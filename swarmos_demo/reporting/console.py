from __future__ import annotations

from typing import Any

from core.types import ExpertProfile, ExpertProposal


def bullet_block(title: str, items: list[str]) -> str:
    lines = [title]
    for item in items:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _render_baseline_comparison(
    baseline: dict[str, Any],
    proposals: list[ExpertProposal],
) -> list[str]:
    lines: list[str] = []
    lines.append("")
    lines.append("-" * 72)
    lines.append("Baseline (single-model, no routing)")
    lines.append("-" * 72)
    lines.append(f"Summary: {baseline['summary']}")
    lines.append(f"Confidence: {baseline['confidence']:.2f}")
    lines.append("")
    lines.append("Recommendations:")
    for item in baseline["recommendations"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Risks:")
    for item in baseline["risks"]:
        lines.append(f"- {item}")

    multi_recs = sum(len(p.recommendations) for p in proposals)
    multi_risks = sum(len(p.risks) for p in proposals)
    lines.append("")
    lines.append("Quick comparison:")
    lines.append(
        f"  Baseline:      {len(baseline['recommendations'])} recs, "
        f"{len(baseline['risks'])} risks, conf={baseline['confidence']:.2f}"
    )
    lines.append(
        f"  Multi-expert:  {multi_recs} recs, "
        f"{multi_risks} risks (from {len(proposals)} experts)"
    )
    return lines


def render_console_report(
    task: str,
    routed: list[tuple[ExpertProfile, float]],
    proposals: list[ExpertProposal],
    critique: dict[str, Any],
    aggregate: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("SwarmOS Demo")
    lines.append("=" * 72)
    lines.append(f"Task: {task}")
    lines.append("")
    lines.append("Routed experts:")
    for expert, score in routed:
        lines.append(f"- {expert.name} ({expert.key}) score={score:.3f}")
    lines.append("")
    lines.append("Expert proposals:")
    for proposal in proposals:
        lines.append(f"* {proposal.expert_name} [{proposal.confidence:.2f}]")
        lines.append(f"  Summary: {proposal.summary}")
        for item in proposal.recommendations:
            lines.append(f"  - {item}")
        if proposal.risks:
            lines.append("  Risks:")
            for item in proposal.risks:
                lines.append(f"  - {item}")
        lines.append("")
    lines.append("Critic focus:")
    for item in critique.get("focus", []):
        lines.append(f"- {item}")
    if critique.get("duplicates"):
        lines.append("")
        lines.append("Critic duplicates:")
        for item in critique["duplicates"]:
            lines.append(f"- {item}")
    if critique.get("next_checks"):
        lines.append("")
        lines.append("Critic next checks:")
        for item in critique["next_checks"]:
            lines.append(f"- {item}")
    lines.append("")
    lines.append("Final summary:")
    lines.append(aggregate["final_summary"])
    lines.append("")
    lines.append(bullet_block("Consensus", aggregate["consensus"]))
    lines.append("")
    lines.append(bullet_block("Next steps", aggregate["next_steps"]))
    lines.append("")
    lines.append(bullet_block("Key risks", aggregate["key_risks"]))

    if baseline is not None:
        lines.extend(_render_baseline_comparison(baseline, proposals))

    return "\n".join(lines)
