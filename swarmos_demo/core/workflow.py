from __future__ import annotations

import argparse
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.conflict import detect_conflicts
from core.cost import build_cost_summary
from core.task_parser import analyze_task
from core.weighting import weighted_ranking
from core.router import route_experts
from core.types import (
    ExpertProfile,
    ExpertProposal,
    WorkflowTrace,
    normalize_task,
)
from providers import build_provider
from providers.base import BaseProvider
from reporting.console import render_console_report
from reporting.markdown import render_markdown_report

logger = logging.getLogger(__name__)

_PROPOSE_TIMEOUT_S = 120


def _build_trace_meta() -> dict[str, str]:
    return {
        "run_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _safe_propose(
    provider: BaseProvider,
    expert: ExpertProfile,
    task: str,
    context: dict[str, Any],
) -> ExpertProposal | None:
    """Propose with error isolation — returns None on failure."""
    try:
        return provider.propose(expert, task, context)
    except Exception as exc:
        logger.warning("Expert %s failed: %s", expert.name, exc)
        return None


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    t0 = time.monotonic()

    if args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")
    else:
        task = args.task
    if not task:
        raise ValueError("Provide --task or --task-file.")

    task = normalize_task(task)
    profile = analyze_task(task)
    budget = getattr(args, "budget", None)
    routed, scores = route_experts(task=task, profile=profile, top_k=args.top_k, budget=budget)
    context: dict[str, Any] = {"profile": profile, "scores": scores}
    provider = build_provider(args)

    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=len(routed)) as executor:
        future_to_expert = {
            executor.submit(_safe_propose, provider, expert, task, context): expert
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

    order = {expert.key: index for index, (expert, _) in enumerate(routed)}
    proposals = sorted(results.values(), key=lambda p: order.get(p.expert_key, 999))

    if not proposals:
        raise RuntimeError("All experts failed — no proposals generated.")

    critique = provider.critique(task=task, routed=routed, proposals=proposals, context=context)
    aggregate = provider.aggregate(
        task=task,
        routed=routed,
        proposals=proposals,
        critique=critique,
        context=context,
    )

    baseline = None
    if getattr(args, "baseline", False):
        try:
            baseline = provider.baseline(task=task, context=context)
        except Exception as exc:
            errors.append(f"Baseline failed: {exc}")

    console_report = render_console_report(task, routed, proposals, critique, aggregate, baseline=baseline)
    markdown_report = render_markdown_report(task, provider.mode, routed, proposals, critique, aggregate, baseline=baseline)

    meta = _build_trace_meta()
    duration_ms = int((time.monotonic() - t0) * 1000)

    trace: WorkflowTrace = {
        "run_id": meta["run_id"],
        "timestamp": meta["timestamp"],
        "task": task,
        "provider": provider.mode,
        "profile": profile,
        "routed": [{"key": expert.key, "name": expert.name, "score": score} for expert, score in routed],
        "proposals": [asdict(proposal) for proposal in proposals],
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

    if getattr(args, "update_reputation", False):
        from core.reputation import update_reputation
        from core.router import reload_reputation
        update_reputation(trace["proposals"])
        reload_reputation()

    return {
        "task": task,
        "provider": provider,
        "console_report": console_report,
        "markdown_report": markdown_report,
        "trace": trace,
    }
