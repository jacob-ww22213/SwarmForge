from __future__ import annotations

from typing import Any

from core.types import ExpertProfile, ExpertProposal


def _render_baseline_section(
    baseline: dict[str, Any],
    proposals: list[ExpertProposal],
) -> list[str]:
    lines: list[str] = []
    lines.append("## Baseline (Single-Model)")
    lines.append("")
    lines.append(f"- Summary: {baseline['summary']}")
    lines.append(f"- Confidence: {baseline['confidence']:.2f}")
    lines.append("")
    lines.append("Recommendations:")
    for item in baseline["recommendations"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Risks:")
    for item in baseline["risks"]:
        lines.append(f"- {item}")
    lines.append("")

    multi_recs = sum(len(p.recommendations) for p in proposals)
    multi_risks = sum(len(p.risks) for p in proposals)
    avg_conf = sum(p.confidence for p in proposals) / len(proposals) if proposals else 0

    lines.append("## Baseline vs Multi-Expert Comparison")
    lines.append("")
    lines.append("| Metric | Baseline | Multi-Expert |")
    lines.append("|--------|----------|--------------|")
    lines.append(
        f"| Recommendations | {len(baseline['recommendations'])} | {multi_recs} |"
    )
    lines.append(
        f"| Risks identified | {len(baseline['risks'])} | {multi_risks} |"
    )
    lines.append(
        f"| Confidence | {baseline['confidence']:.2f} | {avg_conf:.2f} (avg) |"
    )
    lines.append(f"| Perspectives | 1 (generalist) | {len(proposals)} (specialists) |")
    lines.append("")
    return lines


def render_markdown_report(
    task: str,
    provider_mode: str,
    routed: list[tuple[ExpertProfile, float]],
    proposals: list[ExpertProposal],
    critique: dict[str, Any],
    aggregate: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# SwarmOS Demo Report")
    lines.append("")
    lines.append(f"- Provider: `{provider_mode}`")
    lines.append(f"- Task: {task}")
    lines.append("")
    lines.append("## Routed Experts")
    for expert, score in routed:
        lines.append(f"- `{expert.key}` / {expert.name}: score={score:.3f}")
    lines.append("")
    lines.append("## Expert Proposals")
    for proposal in proposals:
        lines.append(f"### {proposal.expert_name}")
        lines.append(f"- Role: {proposal.role}")
        lines.append(f"- Confidence: {proposal.confidence:.2f}")
        lines.append(f"- Summary: {proposal.summary}")
        lines.append("")
        lines.append("Recommendations:")
        for item in proposal.recommendations:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("Risks:")
        for item in proposal.risks:
            lines.append(f"- {item}")
        lines.append("")
    lines.append("## Critic Focus")
    for item in critique.get("focus", []):
        lines.append(f"- {item}")
    lines.append("")
    if critique.get("duplicates"):
        lines.append("## Critic Duplicate Signals")
        for item in critique["duplicates"]:
            lines.append(f"- {item}")
        lines.append("")
    if critique.get("next_checks"):
        lines.append("## Critic Next Checks")
        for item in critique["next_checks"]:
            lines.append(f"- {item}")
        lines.append("")

    if baseline is not None:
        lines.extend(_render_baseline_section(baseline, proposals))

    lines.append("## Final Output")
    lines.append(aggregate["final_summary"])
    lines.append("")
    lines.append("Consensus:")
    for item in aggregate["consensus"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Next steps:")
    for item in aggregate["next_steps"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Key risks:")
    for item in aggregate["key_risks"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
