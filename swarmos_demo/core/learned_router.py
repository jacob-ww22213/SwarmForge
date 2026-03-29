"""Learning-based routing: analyze saved traces to compute per-expert
effectiveness scores, then blend into the rule-based router.

Strategy:
  For each expert that appears in historical traces, compute an
  effectiveness signal from their proposals:
    signal = w_conf * confidence + w_rec * norm(recommendations) + w_risk * (1 - norm(risks))

  These per-expert scores are aggregated across traces (EMA) and stored in
  outputs/.learned_scores.json.  The router calls `learned_bonus(store, expert_key)`
  to get a small additive bonus (clamped to [-0.10, +0.10]).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "outputs" / ".learned_scores.json"
_LEARNING_RATE = 0.20
_BONUS_WEIGHT = 0.10
_MAX_BONUS = 0.10

_W_CONF = 0.50
_W_REC = 0.30
_W_RISK = 0.20


def _proposal_signal(proposal: dict[str, Any]) -> float:
    confidence = proposal.get("confidence", 0.5)
    n_rec = min(len(proposal.get("recommendations", [])), 5) / 5.0
    n_risk = min(len(proposal.get("risks", [])), 3) / 3.0
    risk_quality = 1.0 - max(0.0, n_risk - 0.33)
    return _W_CONF * confidence + _W_REC * n_rec + _W_RISK * risk_quality


def load_learned_scores(path: Path = _DEFAULT_PATH) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("expected dict")
        return {str(k): float(v) for k, v in raw.items()}
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        logger.warning("Corrupted learned scores at %s — resetting.", path)
        return {}


def save_learned_scores(store: dict[str, float], path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_learned_scores(
    traces_dir: Path | None = None,
    out_path: Path = _DEFAULT_PATH,
) -> dict[str, float]:
    """Rebuild learned scores from all traces in a directory."""
    if traces_dir is None:
        traces_dir = out_path.parent

    store = load_learned_scores(out_path)
    traces = sorted(traces_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)

    for trace_path in traces:
        if trace_path.name.startswith("."):
            continue
        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for proposal in trace.get("proposals", []):
            key = proposal.get("expert_key")
            if not key:
                continue
            signal = _proposal_signal(proposal)
            old = store.get(key, 0.50)
            store[key] = round(old + _LEARNING_RATE * (signal - old), 4)

    save_learned_scores(store, out_path)
    return store


def learned_bonus(store: dict[str, float], expert_key: str) -> float:
    """Return a small additive routing bonus based on learned scores."""
    if not store or expert_key not in store:
        return 0.0
    delta = store[expert_key] - 0.50
    bonus = delta * _BONUS_WEIGHT
    return max(-_MAX_BONUS, min(_MAX_BONUS, bonus))
