"""Confidence × Reputation weighted aggregation utilities.

Used by workflow to produce a 'weighted_ranking' field in the trace,
letting downstream consumers (B-line aggregator, reporting) leverage it
without changing their code.
"""
from __future__ import annotations

from typing import Any

from core.reputation import load_reputation, get_reputation


def weighted_ranking(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank proposals by confidence × reputation. Returns sorted list of dicts."""
    store = load_reputation()
    ranked: list[dict[str, Any]] = []
    for p in proposals:
        key = p.get("expert_key", "")
        conf = p.get("confidence", 0.5)
        rep = get_reputation(store, key)
        weight = round(conf * rep, 4)
        ranked.append({
            "expert_key": key,
            "expert_name": p.get("expert_name", key),
            "confidence": conf,
            "reputation": round(rep, 4),
            "weight": weight,
        })
    ranked.sort(key=lambda x: x["weight"], reverse=True)
    return ranked
