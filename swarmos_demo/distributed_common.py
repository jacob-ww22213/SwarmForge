from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.task_parser import analyze_task
from core.types import ExpertProfile
from experts.registry import EXPERTS
from providers import build_provider
from providers.base import BaseProvider


EXPERT_BY_KEY = {expert.key: expert for expert in EXPERTS}
TOKEN_RE = re.compile(r"[a-z0-9_:+.-]+|[\u4e00-\u9fff]+", re.IGNORECASE)

DOMAIN_TEMPLATE_BOOSTS: dict[str, dict[str, float]] = {
    "code": {
        "coding_engineer": 0.42,
        "systems_architect": 0.18,
        "research_scientist": 0.08,
    },
    "math": {
        "math_optimizer": 0.44,
        "research_scientist": 0.18,
    },
    "legal": {
        "legal_risk": 0.48,
        "research_scientist": 0.10,
    },
    "medical": {
        "medical_safety": 0.48,
        "research_scientist": 0.10,
    },
    "research": {
        "research_scientist": 0.38,
        "planner": 0.08,
        "systems_architect": 0.08,
    },
    "business": {
        "product_strategist": 0.36,
        "planner": 0.10,
        "math_optimizer": 0.06,
    },
    "systems": {
        "systems_architect": 0.42,
        "coding_engineer": 0.18,
        "planner": 0.10,
    },
}

ACTION_TEMPLATE_BOOSTS: dict[str, dict[str, float]] = {
    "design": {
        "planner": 0.20,
        "systems_architect": 0.14,
        "product_strategist": 0.06,
    },
    "build": {
        "coding_engineer": 0.22,
        "systems_architect": 0.12,
    },
    "evaluate": {
        "research_scientist": 0.24,
        "math_optimizer": 0.10,
    },
    "sell": {
        "product_strategist": 0.20,
        "planner": 0.06,
    },
    "risk": {
        "legal_risk": 0.24,
        "medical_safety": 0.18,
        "research_scientist": 0.08,
    },
}

PHASE_TEMPLATE_BOOSTS: dict[str, dict[str, float]] = {
    "proposal": {
        "planner": 0.10,
        "systems_architect": 0.08,
        "coding_engineer": 0.08,
        "research_scientist": 0.08,
        "product_strategist": 0.05,
        "math_optimizer": 0.05,
    },
    "review": {
        "research_scientist": 0.26,
        "systems_architect": 0.22,
        "planner": 0.18,
        "legal_risk": 0.18,
        "medical_safety": 0.18,
        "math_optimizer": 0.12,
    },
}


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


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _worker_catalog_text(worker: dict[str, Any], template: ExpertProfile) -> str:
    parts = [
        str(worker.get("worker_id", "")),
        str(worker.get("name", "")),
        str(worker.get("role_key", "")),
        str(worker.get("role_name", "")),
        str(worker.get("model", "")),
        " ".join(str(item) for item in worker.get("keywords", [])),
        " ".join(template.keywords),
        template.role,
    ]
    return " ".join(parts)


def _phase_task_text(task: str, phase: str, prior_results: list[dict[str, Any]] | None) -> str:
    if phase != "review" or not prior_results:
        return task
    lines = [task]
    for item in prior_results[:6]:
        proposal = item.get("proposal", {})
        lines.append(str(proposal.get("summary", "")))
        lines.extend(str(text) for text in proposal.get("recommendations", [])[:3])
        lines.extend(str(text) for text in proposal.get("risks", [])[:2])
    return "\n".join(lines)


def _score_worker(
    worker: dict[str, Any],
    *,
    task: str,
    phase: str,
    exclude_worker_ids: set[str] | None,
    prior_results: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    profile = analyze_task(task)
    template_key = resolve_template_expert_key(worker)
    template = EXPERT_BY_KEY[template_key]
    score = 0.15 + template.bias
    reasons: list[str] = [f"template={template_key}"]

    for domain in profile["domains"]:
        domain_boost = DOMAIN_TEMPLATE_BOOSTS.get(domain, {}).get(template_key, 0.0)
        if domain_boost:
            score += domain_boost
            reasons.append(f"domain:{domain}+{domain_boost:.2f}")

    for action in profile["actions"]:
        action_boost = ACTION_TEMPLATE_BOOSTS.get(action, {}).get(template_key, 0.0)
        if action_boost:
            score += action_boost
            reasons.append(f"action:{action}+{action_boost:.2f}")

    phase_boost = PHASE_TEMPLATE_BOOSTS.get(phase, {}).get(template_key, 0.0)
    if phase_boost:
        score += phase_boost
        reasons.append(f"phase:{phase}+{phase_boost:.2f}")

    task_tokens = set(_tokenize(_phase_task_text(task, phase, prior_results)))
    worker_tokens = set(_tokenize(_worker_catalog_text(worker, template)))
    overlap = sorted(task_tokens & worker_tokens)
    if overlap:
        overlap_boost = min(0.24, 0.04 * len(overlap))
        score += overlap_boost
        reasons.append(f"keyword:{','.join(overlap[:4])}+{overlap_boost:.2f}")

    if profile["mentions_demo"] and template_key in {
        "planner",
        "systems_architect",
        "coding_engineer",
        "research_scientist",
        "product_strategist",
    }:
        score += 0.06
        reasons.append("demo+0.06")

    if profile["risk_level"] == "high" and template_key in {"legal_risk", "medical_safety"}:
        score += 0.10
        reasons.append("high-risk+0.10")

    if phase == "review" and exclude_worker_ids and worker.get("worker_id") in exclude_worker_ids:
        score -= 0.08
        reasons.append("repeat-review-penalty-0.08")

    if phase == "review" and prior_results:
        score += min(0.10, len(prior_results) * 0.02)
        reasons.append("review-context")

    return {
        "worker": worker,
        "worker_id": worker.get("worker_id"),
        "name": worker.get("name"),
        "role_name": worker.get("role_name"),
        "template_key": template_key,
        "score": round(score, 3),
        "reasons": reasons,
    }


def route_workers(
    task: str,
    workers: list[dict[str, Any]],
    *,
    phase: str,
    top_k: int,
    exclude_worker_ids: set[str] | None = None,
    prior_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    profile = analyze_task(task)
    scored = [
        _score_worker(
            worker,
            task=task,
            phase=phase,
            exclude_worker_ids=exclude_worker_ids,
            prior_results=prior_results,
        )
        for worker in workers
    ]
    scored.sort(key=lambda item: (-float(item["score"]), str(item["worker_id"])))
    selected_count = min(max(top_k, 1), len(scored)) if scored else 0
    selected = scored[:selected_count]
    return {
        "phase": phase,
        "profile": profile,
        "selected": selected,
        "all_scores": scored,
    }


def serialize_routing_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "worker_id": item["worker_id"],
            "name": item["name"],
            "role_name": item["role_name"],
            "template_key": item["template_key"],
            "score": item["score"],
            "reasons": item["reasons"],
        }
        for item in records
    ]


def slim_peer_result(item: dict[str, Any]) -> dict[str, Any]:
    proposal = item.get("proposal", {})
    return {
        "worker_id": item.get("worker_id") or item.get("worker", {}).get("worker_id"),
        "worker_name": item.get("worker_name") or item.get("worker", {}).get("name"),
        "role_name": item.get("worker", {}).get("role_name") or item.get("role_name"),
        "latency_ms": item.get("latency_ms"),
        "summary": proposal.get("summary", ""),
        "recommendations": proposal.get("recommendations", [])[:4],
        "risks": proposal.get("risks", [])[:3],
        "confidence": proposal.get("confidence", 0.0),
    }


def build_review_task_prompt(task: str, peer_results: list[dict[str, Any]]) -> str:
    lines = [
        f"Original task: {task}",
        "",
        "You are in round 2 of a multi-agent workflow.",
        "Review the round-1 proposals, keep the strongest consensus items, and resolve the biggest disagreements.",
        "",
        "Round-1 proposals:",
    ]
    for item in peer_results[:8]:
        lines.append(
            f"- {item.get('worker_name') or item.get('worker_id') or 'worker'} "
            f"({item.get('role_name') or 'worker'}): {item.get('summary', '')}"
        )
        for recommendation in item.get("recommendations", [])[:3]:
            lines.append(f"  recommendation: {recommendation}")
        for risk in item.get("risks", [])[:2]:
            lines.append(f"  risk: {risk}")
    lines.extend(
        [
            "",
            "Return a refined answer that highlights:",
            "1. the best consensus recommendations",
            "2. the unresolved risks",
            "3. what should be checked before execution",
        ]
    )
    return "\n".join(lines)


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


def aggregate_distributed_results(
    task: str,
    proposal_results: list[dict[str, Any]],
    review_results: list[dict[str, Any]],
) -> dict[str, Any]:
    round_one = [item for item in proposal_results if item.get("status") == "ok"]
    round_two = [item for item in review_results if item.get("status") == "ok"]
    primary = round_two or round_one
    secondary = round_one if round_two else []

    recommendation_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    confidences: list[float] = []
    active_workers: list[str] = []

    for bucket in (primary, secondary):
        for item in bucket:
            proposal = item.get("proposal", {})
            active_workers.append(item.get("worker", {}).get("name") or item.get("worker_name") or "worker")
            confidences.append(float(proposal.get("confidence", 0.0)))
            for recommendation in proposal.get("recommendations", []):
                recommendation_counter[str(recommendation)] += 1
            for risk in proposal.get("risks", []):
                risk_counter[str(risk)] += 1

    ranked_recommendations = [
        item for item, _ in recommendation_counter.most_common(8)
    ]
    ranked_risks = [
        item for item, _ in risk_counter.most_common(8)
    ]
    consensus_items = [
        item for item, count in recommendation_counter.items() if count >= 2
    ][:5]
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    summary = (
        f"MoE selected {len(proposal_results)} round-1 workers and {len(review_results)} round-2 workers. "
        f"Round 1 completed {len(round_one)} proposals; round 2 completed {len(round_two)} reviews. "
        f"Average confidence across contributing workers is {avg_conf:.2f}."
    )
    if active_workers:
        summary += f" Active workers: {', '.join(dedupe_keep_order(active_workers))}."
    if consensus_items:
        summary += f" Consensus items: {', '.join(consensus_items[:3])}."
    summary += f" Task: {task}"

    return {
        "final_summary": summary,
        "top_recommendations": ranked_recommendations,
        "top_risks": ranked_risks,
        "average_confidence": avg_conf,
        "consensus_items": consensus_items,
        "round_one_successes": len(round_one),
        "round_two_successes": len(round_two),
    }


def build_distributed_metrics(
    results: list[dict[str, Any]],
    *,
    controller_total_ms: int,
    online_worker_count: int,
    proposal_selected_count: int = 0,
    review_selected_count: int = 0,
    proposal_completed_count: int = 0,
    review_completed_count: int = 0,
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
    selected_total = proposal_selected_count + review_selected_count
    selected_completion_rate = round(completed / selected_total, 3) if selected_total else 0.0
    unique_workers = len(
        {
            item.get("worker_id") or item.get("worker", {}).get("worker_id")
            for item in results
            if item.get("status") == "ok"
        }
    )
    return {
        "controller_total_ms": controller_total_ms,
        "online_worker_count": online_worker_count,
        "proposal_selected_count": proposal_selected_count,
        "review_selected_count": review_selected_count,
        "proposal_completed_count": proposal_completed_count,
        "review_completed_count": review_completed_count,
        "completed_worker_count": completed,
        "unique_contributing_workers": unique_workers,
        "completion_rate": completion_rate,
        "selected_completion_rate": selected_completion_rate,
        "mean_worker_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        "max_worker_latency_ms": max(latencies) if latencies else 0,
        "min_worker_latency_ms": min(latencies) if latencies else 0,
        "average_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
        "user_rating": user_rating,
    }
