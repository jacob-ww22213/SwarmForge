from __future__ import annotations

from typing import Any

from demo_types import ExpertProfile, ExpertProposal


def render_markdown_report(
    task: str,
    provider_mode: str,
    routed: list[tuple[ExpertProfile, float]],
    proposals: list[ExpertProposal],
    critique: dict[str, Any],
    aggregate: dict[str, Any],
) -> str:
    lines = []
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
