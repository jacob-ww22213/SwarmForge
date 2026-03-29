"""Detect contradictions / divergences between expert proposals.

Heuristics:
  1. Sentiment conflict: one expert flags a risk that another explicitly recommends.
  2. Confidence spread: unusually wide confidence range signals disagreement.
  3. Recommendation overlap: if the same recommendation appears in many experts,
     and another expert's risk contradicts it, that's a conflict.
"""
from __future__ import annotations

from typing import Any

from core.config import (
    CONFLICT_CONFIDENCE_SPREAD as _CONFIDENCE_SPREAD_THRESHOLD,
    CONFLICT_MIN_PROPOSALS as _MIN_PROPOSALS_FOR_ANALYSIS,
)


def _normalize(text: str) -> set[str]:
    """Extract lowercased keywords (>2 chars) for rough matching."""
    return {w for w in text.lower().split() if len(w) > 2}


def detect_conflicts(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a list of detected conflicts between proposals."""
    if len(proposals) < _MIN_PROPOSALS_FOR_ANALYSIS:
        return []

    conflicts: list[dict[str, Any]] = []

    rec_keywords: dict[str, set[str]] = {}
    risk_keywords: dict[str, set[str]] = {}
    for p in proposals:
        key = p.get("expert_key", "?")
        recs = " ".join(p.get("recommendations", []))
        risks = " ".join(p.get("risks", []))
        rec_keywords[key] = _normalize(recs)
        risk_keywords[key] = _normalize(risks)

    keys = list(rec_keywords.keys())
    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1:]:
            overlap_rec_risk = rec_keywords[k1] & risk_keywords[k2]
            overlap_risk_rec = risk_keywords[k1] & rec_keywords[k2]
            shared = overlap_rec_risk | overlap_risk_rec
            significant = {w for w in shared if len(w) > 3}
            if len(significant) >= 2:
                name1 = _find_name(proposals, k1)
                name2 = _find_name(proposals, k2)
                conflicts.append({
                    "type": "recommendation_vs_risk",
                    "experts": [name1, name2],
                    "keywords": sorted(significant)[:5],
                    "description": (
                        f"{name1} 建议的方向被 {name2} 标记为风险"
                        f" (关键词: {', '.join(sorted(significant)[:3])})"
                    ),
                })

    confidences = [p.get("confidence", 0.5) for p in proposals]
    if confidences:
        spread = max(confidences) - min(confidences)
        if spread >= _CONFIDENCE_SPREAD_THRESHOLD:
            high_expert = _find_name(proposals, _key_at_conf(proposals, max(confidences)))
            low_expert = _find_name(proposals, _key_at_conf(proposals, min(confidences)))
            conflicts.append({
                "type": "confidence_divergence",
                "experts": [high_expert, low_expert],
                "spread": round(spread, 3),
                "description": (
                    f"置信度分歧: {high_expert} ({max(confidences):.0%}) vs "
                    f"{low_expert} ({min(confidences):.0%})"
                ),
            })

    return conflicts


def _find_name(proposals: list[dict[str, Any]], key: str) -> str:
    for p in proposals:
        if p.get("expert_key") == key:
            return p.get("expert_name", key)
    return key


def _key_at_conf(proposals: list[dict[str, Any]], conf: float) -> str:
    for p in proposals:
        if p.get("confidence") == conf:
            return p.get("expert_key", "?")
    return "?"
