"""Expert reputation store.

Tracks per-expert historical quality signals and feeds them back into routing.
Data lives in a JSON file; each run can optionally update it.

This module is purely A-line. B-line code is not affected.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "outputs" / ".reputation.json"

_DEFAULT_REPUTATION = 0.50
_LEARNING_RATE = 0.15
_REPUTATION_WEIGHT = 0.10


def load_reputation(path: Path = _DEFAULT_PATH) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: float(v) for k, v in data.items()}
    except (json.JSONDecodeError, ValueError):
        return {}


def get_reputation(store: dict[str, float], expert_key: str) -> float:
    return store.get(expert_key, _DEFAULT_REPUTATION)


def reputation_bonus(store: dict[str, float], expert_key: str) -> float:
    """Score adjustment for the router: reputation * weight."""
    return get_reputation(store, expert_key) * _REPUTATION_WEIGHT


def update_reputation(
    proposals: list[dict[str, Any]],
    path: Path = _DEFAULT_PATH,
) -> dict[str, float]:
    """Update reputation after a run based on proposal quality signals.

    Quality signal per expert:
      signal = 0.4 * confidence
             + 0.3 * min(len(recommendations) / 4, 1.0)
             + 0.3 * min(len(risks) / 2, 1.0)

    Reputation is an exponential moving average:
      new = old * (1 - lr) + signal * lr
    """
    store = load_reputation(path)

    for proposal in proposals:
        key = proposal.get("expert_key", "")
        if not key:
            continue
        confidence = proposal.get("confidence", 0.5)
        rec_count = len(proposal.get("recommendations", []))
        risk_count = len(proposal.get("risks", []))

        signal = (
            0.4 * confidence
            + 0.3 * min(rec_count / 4.0, 1.0)
            + 0.3 * min(risk_count / 2.0, 1.0)
        )

        old = store.get(key, _DEFAULT_REPUTATION)
        store[key] = round(old * (1 - _LEARNING_RATE) + signal * _LEARNING_RATE, 4)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(store, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return store
