"""Token counting and cost estimation.

For mock provider: estimates tokens via character count heuristic.
For real providers: uses the usage dict returned by the API.

Cost model (configurable):
  prompt_token:     $0.003 / 1K
  completion_token: $0.006 / 1K
"""
from __future__ import annotations

from typing import Any

_COST_PER_1K_PROMPT = 0.003
_COST_PER_1K_COMPLETION = 0.006
_CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str) -> int:
    """Rough token estimate from character count."""
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def cost_from_usage(usage: dict[str, int]) -> float:
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    return (prompt * _COST_PER_1K_PROMPT + completion * _COST_PER_1K_COMPLETION) / 1000


def build_cost_summary(
    proposals: list[dict[str, Any]],
    usage_map: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Build a CostSummary dict for the trace.

    If usage_map is provided (from real provider), uses actual token counts.
    Otherwise estimates from proposal text lengths.
    """
    per_expert: dict[str, Any] = {}
    total_prompt = 0
    total_completion = 0

    for p in proposals:
        key = p.get("expert_key", "unknown")

        if usage_map and key in usage_map:
            u = usage_map[key]
            pt = u.get("prompt_tokens", 0)
            ct = u.get("completion_tokens", 0)
        else:
            text_len = len(p.get("summary", ""))
            text_len += sum(len(r) for r in p.get("recommendations", []))
            text_len += sum(len(r) for r in p.get("risks", []))
            ct = estimate_tokens(" " * text_len) if text_len else 50
            pt = ct * 2

        total_prompt += pt
        total_completion += ct
        expert_cost = (pt * _COST_PER_1K_PROMPT + ct * _COST_PER_1K_COMPLETION) / 1000
        per_expert[key] = {
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "estimated_cost_usd": round(expert_cost, 6),
        }

    total_cost = (total_prompt * _COST_PER_1K_PROMPT + total_completion * _COST_PER_1K_COMPLETION) / 1000
    return {
        "total_tokens": total_prompt + total_completion,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "estimated_cost_usd": round(total_cost, 6),
        "per_expert": per_expert,
    }
