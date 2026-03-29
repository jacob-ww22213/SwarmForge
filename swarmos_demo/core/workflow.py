from __future__ import annotations

import argparse
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.task_parser import analyze_task
from core.router import route_experts
from core.types import normalize_task
from providers import build_provider
from reporting.console import render_console_report
from reporting.markdown import render_markdown_report


def _build_trace_meta() -> dict[str, str]:
    return {
        "run_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    if args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")
    else:
        task = args.task
    if not task:
        raise ValueError("Provide --task or --task-file.")

    task = normalize_task(task)
    profile = analyze_task(task)
    routed, scores = route_experts(task=task, profile=profile, top_k=args.top_k)
    context = {"profile": profile, "scores": scores}
    provider = build_provider(args)

    with ThreadPoolExecutor(max_workers=len(routed)) as executor:
        futures = [executor.submit(provider.propose, expert, task, context) for expert, _ in routed]
        proposals = [future.result() for future in futures]

    order = {expert.key: index for index, (expert, _) in enumerate(routed)}
    proposals.sort(key=lambda proposal: order[proposal.expert_key])

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
        baseline = provider.baseline(task=task, context=context)

    console_report = render_console_report(task, routed, proposals, critique, aggregate, baseline=baseline)
    markdown_report = render_markdown_report(task, provider.mode, routed, proposals, critique, aggregate, baseline=baseline)

    meta = _build_trace_meta()
    trace: dict[str, Any] = {
        "run_id": meta["run_id"],
        "timestamp": meta["timestamp"],
        "task": task,
        "provider": provider.mode,
        "profile": profile,
        "routed": [{"key": expert.key, "name": expert.name, "score": score} for expert, score in routed],
        "proposals": [asdict(proposal) for proposal in proposals],
        "critique": critique,
        "aggregate": aggregate,
    }
    if baseline is not None:
        trace["baseline"] = baseline

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
