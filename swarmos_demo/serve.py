#!/usr/bin/env python3
"""SwarmOS Web Demo — zero-dependency HTTP server.

Usage:
    python3 serve.py                                       # mock, http://localhost:8000
    python3 serve.py --provider openai-compatible \\
        --base-url https://api.example.com/v1 \\
        --api-key sk-... --model gpt-4o                    # real LLM
    python3 serve.py --provider ollama --model qwen2.5:7b  # local Ollama
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
import uuid

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

sys.path.insert(0, str(PROJECT_ROOT))

from core.conflict import detect_conflicts
from core.cost import build_cost_summary
from core.task_parser import analyze_task
from core.weighting import weighted_ranking
from core.router import route_experts, reload_reputation
from core.types import ExpertProfile, ExpertProposal, WorkflowTrace, normalize_task
from core.reputation import update_reputation
from providers import build_provider
from providers.base import BaseProvider
from providers.mock import MockProvider

from core.config import WORKFLOW_PROPOSE_TIMEOUT_S as _PROPOSE_TIMEOUT_S

logger = logging.getLogger(__name__)

_active_provider: BaseProvider | None = None


def _get_provider() -> BaseProvider:
    global _active_provider
    if _active_provider is None:
        _active_provider = MockProvider()
    return _active_provider


def _safe_propose(
    provider: BaseProvider,
    expert: ExpertProfile,
    task: str,
    context: dict[str, Any],
) -> ExpertProposal | None:
    try:
        return provider.propose(expert, task, context)
    except Exception as exc:
        logger.warning("Expert %s failed: %s", expert.name, exc)
        return None


def _run_single(task: str, top_k: int = 3, with_baseline: bool = False) -> WorkflowTrace:
    """Run the full pipeline and return the trace dict."""
    t0 = time.monotonic()
    task = normalize_task(task)
    profile = analyze_task(task)
    routed, scores = route_experts(task=task, profile=profile, top_k=top_k)
    context: dict[str, Any] = {"profile": profile, "scores": scores}
    provider = _get_provider()

    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=len(routed)) as pool:
        future_to_expert = {
            pool.submit(_safe_propose, provider, expert, task, context): expert
            for expert, _ in routed
        }
        results: dict[str, ExpertProposal] = {}
        try:
            for future in as_completed(future_to_expert, timeout=_PROPOSE_TIMEOUT_S):
                expert = future_to_expert[future]
                proposal = future.result()
                if proposal is not None:
                    results[expert.key] = proposal
                else:
                    errors.append(f"{expert.name}: proposal failed")
        except TimeoutError:
            errors.append("Proposal phase timed out")

    order = {e.key: i for i, (e, _) in enumerate(routed)}
    proposals = sorted(results.values(), key=lambda p: order.get(p.expert_key, 999))

    critique = provider.critique(task=task, routed=routed, proposals=proposals, context=context)
    aggregate = provider.aggregate(task=task, routed=routed, proposals=proposals, critique=critique, context=context)

    baseline = None
    if with_baseline:
        try:
            baseline = provider.baseline(task=task, context=context)
        except Exception as exc:
            errors.append(f"Baseline failed: {exc}")

    duration_ms = int((time.monotonic() - t0) * 1000)
    trace: WorkflowTrace = {
        "run_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": task,
        "provider": provider.mode,
        "profile": profile,
        "routed": [{"key": e.key, "name": e.name, "score": s} for e, s in routed],
        "proposals": [asdict(p) for p in proposals],
        "critique": critique,
        "aggregate": aggregate,
        "duration_ms": duration_ms,
    }
    if baseline is not None:
        trace["baseline"] = baseline
    if errors:
        trace["errors"] = errors

    usage_map: dict[str, dict[str, int]] = {}
    for p in proposals:
        u = getattr(p, "_usage", None)
        if u:
            usage_map[p.expert_key] = u
    trace["cost"] = build_cost_summary(trace["proposals"], usage_map or None)

    conflicts = detect_conflicts(trace["proposals"])
    if conflicts:
        trace["conflicts"] = conflicts

    trace["aggregate"]["weighted_ranking"] = weighted_ranking(trace["proposals"])

    return trace


def _run_multi_round(
    task: str, history: list[dict[str, Any]], feedback: str, top_k: int = 3
) -> WorkflowTrace:
    """Run one round of multi-round collaboration with accumulated context."""
    round_num = len(history) + 1
    enriched_task = task
    if feedback and history:
        enriched_task = (
            f"{task}\n\n"
            f"[第 {round_num} 轮追问] {feedback}\n\n"
            f"[上一轮共识] {history[-1].get('aggregate', {}).get('final_summary', '')}"
        )

    trace = _run_single(enriched_task, top_k=top_k, with_baseline=False)
    trace["round"] = round_num
    if feedback:
        trace["user_feedback"] = feedback
    return trace


def _list_traces() -> list[dict[str, Any]]:
    """List saved JSON traces from outputs/."""
    traces = []
    for p in sorted(OUTPUTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        # Skip AppleDouble metadata files that may appear after copying archives
        # from macOS onto Linux hosts.
        if p.name.startswith("._"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            traces.append({
                "file": p.name,
                "run_id": data.get("run_id", "N/A"),
                "timestamp": data.get("timestamp", ""),
                "task": data.get("task", "")[:100],
                "provider": data.get("provider", ""),
                "expert_count": len(data.get("proposals", [])),
                "has_baseline": "baseline" in data,
            })
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
    return traces


def _get_trace(filename: str) -> dict[str, Any] | None:
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename or ".." in filename:
        return None
    path = (OUTPUTS_DIR / safe_name).resolve()
    if not path.is_relative_to(OUTPUTS_DIR.resolve()):
        return None
    if not path.exists() or path.suffix != ".json" or path.name.startswith("._"):
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None


class APIHandler(SimpleHTTPRequestHandler):
    """Serves static files from web/ and handles /api/* endpoints."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _json_response(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "" or path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()

        if path == "/api/status":
            p = _get_provider()
            return self._json_response({"provider": p.mode})

        if path == "/api/traces":
            return self._json_response(_list_traces())

        if path.startswith("/api/traces/"):
            filename = path[len("/api/traces/"):]
            trace = _get_trace(filename)
            if trace is None:
                return self._json_response({"error": "not found"}, 404)
            return self._json_response(trace)

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/run":
            try:
                body = json.loads(self._read_body())
            except json.JSONDecodeError:
                return self._json_response({"error": "invalid JSON"}, 400)

            task = body.get("task", "").strip()
            if not task:
                return self._json_response({"error": "task is required"}, 400)

            top_k = body.get("top_k", 3)
            with_baseline = body.get("baseline", False)
            trace = _run_single(task, top_k=top_k, with_baseline=with_baseline)

            if body.get("save", False):
                out = OUTPUTS_DIR / f"{trace['run_id']}.json"
                out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
                trace["_saved_to"] = out.name

            if body.get("update_reputation", False):
                update_reputation(trace["proposals"])
                reload_reputation()

            return self._json_response(trace)

        if path == "/api/multi-round":
            try:
                body = json.loads(self._read_body())
            except json.JSONDecodeError:
                return self._json_response({"error": "invalid JSON"}, 400)

            task = body.get("task", "").strip()
            if not task:
                return self._json_response({"error": "task is required"}, 400)

            history = body.get("history", [])
            feedback = body.get("feedback", "").strip()
            top_k = body.get("top_k", 3)
            trace = _run_multi_round(task, history, feedback, top_k=top_k)
            return self._json_response(trace)

        self._json_response({"error": "not found"}, 404)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[serve] {args[0]} {args[1]} {args[2]}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SwarmOS Web Demo server.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--provider",
        choices=("mock", "openai-compatible", "ollama"),
        default="mock",
    )
    parser.add_argument("--base-url", help="Base URL for real providers.")
    parser.add_argument("--api-key", help="API key for openai-compatible provider.")
    parser.add_argument("--model", help="Model name for real providers.")
    args = parser.parse_args()

    global _active_provider
    _active_provider = build_provider(args)
    print(f"Provider: {_active_provider.mode}")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer((args.host, args.port), APIHandler)
    print(f"SwarmOS Web Demo running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
