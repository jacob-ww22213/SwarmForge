#!/usr/bin/env python3
"""SwarmOS Web Demo — zero-dependency HTTP server.

Usage:
    python3 serve.py              # http://localhost:8000
    python3 serve.py --port 9000  # http://localhost:9000
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from functools import partial
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

sys.path.insert(0, str(PROJECT_ROOT))

from core.task_parser import analyze_task
from core.router import route_experts, reload_reputation
from core.types import normalize_task
from core.reputation import update_reputation
from providers.mock import MockProvider
from providers.base import BaseProvider
from reporting.console import render_console_report
from reporting.markdown import render_markdown_report
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
import uuid
from datetime import datetime, timezone


def _run_single(task: str, top_k: int = 3, with_baseline: bool = False) -> dict[str, Any]:
    """Run the full pipeline and return the trace dict."""
    task = normalize_task(task)
    profile = analyze_task(task)
    routed, scores = route_experts(task=task, profile=profile, top_k=top_k)
    context: dict[str, Any] = {"profile": profile, "scores": scores}
    provider: BaseProvider = MockProvider()

    with ThreadPoolExecutor(max_workers=len(routed)) as pool:
        futures = [pool.submit(provider.propose, expert, task, context) for expert, _ in routed]
        proposals = [f.result() for f in futures]

    order = {e.key: i for i, (e, _) in enumerate(routed)}
    proposals.sort(key=lambda p: order[p.expert_key])

    critique = provider.critique(task=task, routed=routed, proposals=proposals, context=context)
    aggregate = provider.aggregate(task=task, routed=routed, proposals=proposals, critique=critique, context=context)

    baseline = None
    if with_baseline:
        baseline = provider.baseline(task=task, context=context)

    trace: dict[str, Any] = {
        "run_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": task,
        "provider": provider.mode,
        "profile": profile,
        "routed": [{"key": e.key, "name": e.name, "score": s} for e, s in routed],
        "proposals": [asdict(p) for p in proposals],
        "critique": critique,
        "aggregate": aggregate,
    }
    if baseline is not None:
        trace["baseline"] = baseline

    return trace


def _run_multi_round(
    task: str, history: list[dict[str, Any]], feedback: str, top_k: int = 3
) -> dict[str, Any]:
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
        except (json.JSONDecodeError, OSError):
            continue
    return traces


def _get_trace(filename: str) -> dict[str, Any] | None:
    path = OUTPUTS_DIR / filename
    if not path.exists() or not path.suffix == ".json":
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
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
    args = parser.parse_args()

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
