from __future__ import annotations

from typing import Any

from demo_types import ExpertProfile, ExpertProposal


def bullet_block(title: str, items: list[str]) -> str:
    lines = [title]
    for item in items:
        lines.append(f"- {item}")
    return "\n".join(lines)


def render_console_report(
    task: str,
    routed: list[tuple[ExpertProfile, float]],
    proposals: list[ExpertProposal],
    critique: dict[str, Any],
    aggregate: dict[str, Any],
) -> str:
    lines = []
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
    return "\n".join(lines)
