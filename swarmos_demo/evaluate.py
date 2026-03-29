#!/usr/bin/env python3
"""Compare baseline vs multi-expert output from one or more JSON traces.

Usage:
    python3 evaluate.py outputs/task_01.json
    python3 evaluate.py outputs/task_01.json outputs/task_02.json outputs/task_03.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_trace(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze_trace(trace: dict[str, Any]) -> dict[str, Any]:
    proposals = trace.get("proposals", [])
    baseline = trace.get("baseline")
    aggregate = trace.get("aggregate", {})

    multi_recs = sum(len(p.get("recommendations", [])) for p in proposals)
    multi_risks = sum(len(p.get("risks", [])) for p in proposals)
    confidences = [p.get("confidence", 0) for p in proposals]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    expert_count = len(proposals)

    unique_risk_texts = set()
    for p in proposals:
        for r in p.get("risks", []):
            unique_risk_texts.add(r)

    consensus_count = len(aggregate.get("consensus", []))
    next_steps_count = len(aggregate.get("next_steps", []))

    result: dict[str, Any] = {
        "task_preview": trace.get("task", "")[:80],
        "provider": trace.get("provider", "unknown"),
        "run_id": trace.get("run_id", "N/A"),
        "expert_count": expert_count,
        "multi": {
            "recommendations": multi_recs,
            "risks": multi_risks,
            "unique_risks": len(unique_risk_texts),
            "avg_confidence": round(avg_conf, 2),
            "consensus_points": consensus_count,
            "next_steps": next_steps_count,
        },
    }

    if baseline:
        bl_recs = len(baseline.get("recommendations", []))
        bl_risks = len(baseline.get("risks", []))
        bl_conf = baseline.get("confidence", 0)
        result["baseline"] = {
            "recommendations": bl_recs,
            "risks": bl_risks,
            "confidence": round(bl_conf, 2),
        }
        result["delta"] = {
            "recommendations": f"+{multi_recs - bl_recs}",
            "risks": f"+{multi_risks - bl_risks}",
            "confidence": f"+{round(avg_conf - bl_conf, 2)}",
            "perspectives": f"1 -> {expert_count}",
        }
    else:
        result["baseline"] = None
        result["delta"] = None

    return result


def print_report(analyses: list[dict[str, Any]]) -> None:
    separator = "=" * 72
    print(separator)
    print("SwarmOS Evaluation Report")
    print(separator)
    print()

    for i, a in enumerate(analyses):
        print(f"--- Trace {i + 1}: {a['run_id']} ({a['provider']}) ---")
        print(f"Task: {a['task_preview']}...")
        print(f"Experts routed: {a['expert_count']}")
        print()

        m = a["multi"]
        print("  Multi-expert:")
        print(f"    Recommendations:  {m['recommendations']}")
        print(f"    Risks:            {m['risks']} (unique: {m['unique_risks']})")
        print(f"    Avg confidence:   {m['avg_confidence']}")
        print(f"    Consensus points: {m['consensus_points']}")
        print(f"    Next steps:       {m['next_steps']}")

        if a["baseline"]:
            b = a["baseline"]
            d = a["delta"]
            print()
            print("  Baseline (single-model):")
            print(f"    Recommendations:  {b['recommendations']}")
            print(f"    Risks:            {b['risks']}")
            print(f"    Confidence:       {b['confidence']}")
            print()
            print("  Delta (multi - baseline):")
            print(f"    Recommendations:  {d['recommendations']}")
            print(f"    Risks:            {d['risks']}")
            print(f"    Confidence:       {d['confidence']}")
            print(f"    Perspectives:     {d['perspectives']}")
        else:
            print()
            print("  (no baseline — rerun with --baseline to enable comparison)")

        print()

    if len(analyses) > 1:
        print(separator)
        print("Summary across all traces:")
        total_multi_recs = sum(a["multi"]["recommendations"] for a in analyses)
        total_experts = sum(a["expert_count"] for a in analyses)
        avg_conf_all = sum(a["multi"]["avg_confidence"] for a in analyses) / len(analyses)
        with_baseline = [a for a in analyses if a["baseline"]]
        print(f"  Total traces:        {len(analyses)}")
        print(f"  Total experts used:  {total_experts}")
        print(f"  Total recs (multi):  {total_multi_recs}")
        print(f"  Avg confidence:      {avg_conf_all:.2f}")
        if with_baseline:
            avg_bl_conf = sum(a["baseline"]["confidence"] for a in with_baseline) / len(with_baseline)
            print(f"  Avg baseline conf:   {avg_bl_conf:.2f}")
            print(f"  Traces with baseline: {len(with_baseline)}/{len(analyses)}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SwarmOS trace files.")
    parser.add_argument("traces", nargs="+", help="One or more JSON trace files.")
    parser.add_argument("--json", dest="output_json", help="Save evaluation as JSON.")
    args = parser.parse_args()

    analyses = []
    for path in args.traces:
        try:
            trace = load_trace(path)
            analyses.append(analyze_trace(trace))
        except (json.JSONDecodeError, FileNotFoundError) as exc:
            print(f"WARN: skipping {path}: {exc}", file=sys.stderr)

    if not analyses:
        print("ERROR: no valid traces to evaluate.", file=sys.stderr)
        return 1

    print_report(analyses)

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(analyses, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved evaluation JSON to {Path(args.output_json).resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
