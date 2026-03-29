from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.types import ExpertProfile
from providers import build_provider
from providers.base import BaseProvider


def resolve_template_expert_key(worker: dict[str, Any]) -> str:
    raw = " ".join(
        str(worker.get(key, "")).lower()
        for key in ("role_key", "role_name", "worker_id", "name")
    )
    if any(token in raw for token in ("research", "science", "eval", "benchmark")):
        return "research_scientist"
    if any(token in raw for token in ("code", "coding", "engineer", "dev")):
        return "coding_engineer"
    if any(token in raw for token in ("system", "infra", "arch")):
        return "systems_architect"
    if any(token in raw for token in ("product", "biz", "investor", "market")):
        return "product_strategist"
    if any(token in raw for token in ("math", "optimiz", "budget")):
        return "math_optimizer"
    if any(token in raw for token in ("legal", "compliance")):
        return "legal_risk"
    if any(token in raw for token in ("medical", "safety", "health")):
        return "medical_safety"
    return "planner"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_timestamp_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"{prefix}_{stamp}"


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def json_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = None
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc
    if not raw.strip():
        return {}
    return json.loads(raw)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def guess_public_url(host: str, port: int) -> str:
    bind_host = host if host not in {"0.0.0.0", ""} else socket.gethostbyname(socket.gethostname())
    return f"http://{bind_host}:{port}"


def ollama_api_root(base_url: str) -> str:
    lowered = base_url.rstrip("/")
    if lowered.endswith("/v1"):
        return lowered[:-3]
    return lowered


def list_ollama_models(base_url: str) -> list[str]:
    root = ollama_api_root(base_url)
    payload = json_request(f"{root}/api/tags", timeout=20.0)
    models = payload.get("models", [])
    return [item.get("name", "") for item in models if item.get("name")]


def pull_ollama_model(base_url: str, model: str) -> dict[str, Any]:
    root = ollama_api_root(base_url)
    return json_request(
        f"{root}/api/pull",
        method="POST",
        payload={"name": model, "stream": False},
        timeout=600.0,
    )


def make_provider(
    *,
    provider: str,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
) -> BaseProvider:
    class Args:
        pass

    args = Args()
    args.provider = provider
    args.base_url = base_url
    args.api_key = api_key
    args.model = model
    return build_provider(args)  # type: ignore[arg-type]


def build_worker_expert_profile(worker: dict[str, Any]) -> ExpertProfile:
    template_key = resolve_template_expert_key(worker)
    name = worker.get("name") or worker.get("worker_id", "Worker")
    role_name = worker.get("role_name") or "Distributed worker model"
    model = worker.get("model") or "unknown-model"
    system_prompt = (
        f"You are worker {name}. "
        f"Your assigned role is: {role_name}. "
        f"You are currently serving model {model}. "
        "Return concise, practical, structured recommendations."
    )
    return ExpertProfile(
        key=template_key,
        name=name,
        role=role_name,
        keywords=tuple(worker.get("keywords", [])) or ("demo", "task", "system"),
        bias=float(worker.get("bias", 0.10)),
        temperature=float(worker.get("temperature", 0.2)),
        max_tokens=int(worker.get("max_tokens", 512)),
        system_prompt=system_prompt,
    )


def aggregate_distributed_results(task: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [item for item in results if item.get("status") == "ok"]
    recommendations: list[str] = []
    risks: list[str] = []
    confidences: list[float] = []
    worker_names: list[str] = []
    for item in successes:
        proposal = item["proposal"]
        worker_names.append(item["worker"]["name"])
        recommendations.extend(proposal.get("recommendations", []))
        risks.extend(proposal.get("risks", []))
        confidences.append(float(proposal.get("confidence", 0.0)))

    recommendations = dedupe_keep_order(recommendations)[:8]
    risks = dedupe_keep_order(risks)[:8]
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    summary = (
        f"Task dispatched to {len(results)} online workers; "
        f"{len(successes)} returned successful proposals. "
        f"Average worker confidence is {avg_conf:.2f}."
    )
    if worker_names:
        summary += f" Active workers: {', '.join(worker_names)}."
    summary += f" Task: {task}"
    return {
        "final_summary": summary,
        "top_recommendations": recommendations,
        "top_risks": risks,
        "average_confidence": avg_conf,
    }


def build_distributed_metrics(
    results: list[dict[str, Any]],
    *,
    controller_total_ms: int,
    online_worker_count: int,
    user_rating: int | None = None,
) -> dict[str, Any]:
    latencies = [int(item.get("latency_ms", 0)) for item in results if item.get("status") == "ok"]
    confidences = [
        float(item["proposal"].get("confidence", 0.0))
        for item in results
        if item.get("status") == "ok"
    ]
    completed = len([item for item in results if item.get("status") == "ok"])
    completion_rate = round(completed / online_worker_count, 3) if online_worker_count else 0.0
    return {
        "controller_total_ms": controller_total_ms,
        "online_worker_count": online_worker_count,
        "completed_worker_count": completed,
        "completion_rate": completion_rate,
        "mean_worker_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        "max_worker_latency_ms": max(latencies) if latencies else 0,
        "min_worker_latency_ms": min(latencies) if latencies else 0,
        "average_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
        "user_rating": user_rating,
    }
