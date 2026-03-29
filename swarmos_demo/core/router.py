from __future__ import annotations

import threading

from core.config import (
    COST_PER_1K_COMPLETION as _COST_PER_1K_COMPLETION,
    COST_PER_1K_PROMPT as _COST_PER_1K_PROMPT,
    ROUTER_BASE_SCORE,
    ROUTER_DOMAIN_BOOST,
    ROUTER_KEYWORD_BOOST,
    ROUTER_PLANNER_BOOST,
)
from core.learned_router import learned_bonus, load_learned_scores
from core.reputation import load_reputation, reputation_bonus
from core.tfidf_router import tfidf_bonus
from core.types import ExpertProfile, TaskProfile, clamp
from experts.registry import EXPERTS

_lock = threading.Lock()
_reputation_store: dict[str, float] | None = None
_learned_store: dict[str, float] | None = None


def _get_reputation_store() -> dict[str, float]:
    global _reputation_store
    with _lock:
        if _reputation_store is None:
            _reputation_store = load_reputation()
        return _reputation_store


def _get_learned_store() -> dict[str, float]:
    global _learned_store
    with _lock:
        if _learned_store is None:
            _learned_store = load_learned_scores()
        return _learned_store


def reload_reputation() -> None:
    """Force-reload reputation store from disk (call after update)."""
    global _reputation_store
    with _lock:
        _reputation_store = None


def reload_learned() -> None:
    """Force-reload learned scores from disk."""
    global _learned_store
    with _lock:
        _learned_store = None


def score_expert(expert: ExpertProfile, task: str, profile: TaskProfile) -> float:
    score = (
        ROUTER_BASE_SCORE
        + expert.bias
        + reputation_bonus(_get_reputation_store(), expert.key)
        + learned_bonus(_get_learned_store(), expert.key)
        + tfidf_bonus(EXPERTS, task, expert.key)
    )
    lowered = task.lower()
    for keyword in expert.keywords:
        if keyword.lower() in lowered or keyword in task:
            score += ROUTER_KEYWORD_BOOST

    domain_boost = ROUTER_DOMAIN_BOOST.get(expert.key)
    if domain_boost is not None:
        key = expert.key
        if key == "systems_architect" and "systems" in profile["domains"]:
            score += domain_boost
        elif key == "coding_engineer" and ("code" in profile["domains"] or profile["mentions_demo"]):
            score += domain_boost
        elif key == "research_scientist" and "research" in profile["domains"]:
            score += domain_boost
        elif key == "product_strategist" and ("business" in profile["domains"] or profile["mentions_demo"]):
            score += domain_boost
        elif key == "math_optimizer" and ("math" in profile["domains"] or "evaluate" in profile["actions"]):
            score += domain_boost
        elif key == "legal_risk" and "legal" in profile["domains"]:
            score += domain_boost
        elif key == "medical_safety" and "medical" in profile["domains"]:
            score += domain_boost

    if expert.key == "planner":
        score += ROUTER_PLANNER_BOOST

    return round(clamp(score, 0.0, 1.0), 3)


def _estimate_expert_cost(expert: ExpertProfile) -> float:
    """Rough per-call cost estimate based on max_tokens config."""
    prompt_tokens = expert.max_tokens * 2
    return (prompt_tokens * _COST_PER_1K_PROMPT + expert.max_tokens * _COST_PER_1K_COMPLETION) / 1000


def route_experts(
    task: str,
    profile: TaskProfile,
    top_k: int,
    *,
    budget: float | None = None,
) -> tuple[list[tuple[ExpertProfile, float]], dict[str, float]]:
    score_map: dict[str, float] = {}
    for expert in EXPERTS:
        score_map[expert.key] = score_expert(expert, task, profile)

    always_include = {"planner"}
    optional = []
    for expert in EXPERTS:
        if expert.key in always_include:
            continue
        optional.append((expert, score_map[expert.key]))
    optional.sort(key=lambda item: item[1], reverse=True)

    selected = [(expert, score_map[expert.key]) for expert in EXPERTS if expert.key in always_include]
    remaining_budget = budget

    if remaining_budget is not None:
        for expert, _ in selected:
            remaining_budget -= _estimate_expert_cost(expert)

    for expert, sc in optional[:top_k]:
        if remaining_budget is not None:
            cost = _estimate_expert_cost(expert)
            if cost > remaining_budget:
                continue
            remaining_budget -= cost
        selected.append((expert, sc))

    return selected, score_map
