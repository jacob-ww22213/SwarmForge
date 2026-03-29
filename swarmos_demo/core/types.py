from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# TypedDict types — runtime 是普通 dict，B 线用 profile["domains"] 不受影响
# ---------------------------------------------------------------------------

class TaskProfile(TypedDict):
    language: str
    domains: list[str]
    actions: list[str]
    risk_level: str
    mentions_demo: bool


class CritiqueReport(TypedDict):
    focus: list[str]
    duplicates: list[str]
    next_checks: list[str]


class AggregateResult(TypedDict):
    selected_experts: list[str]
    consensus: list[str]
    critique_focus: list[str]
    next_steps: list[str]
    key_risks: list[str]
    final_summary: str


class BaselineResult(TypedDict):
    summary: str
    recommendations: list[str]
    risks: list[str]
    confidence: float


class _WorkflowTraceRequired(TypedDict):
    run_id: str
    timestamp: str
    task: str
    provider: str
    profile: TaskProfile
    routed: list[dict[str, Any]]
    proposals: list[dict[str, Any]]
    critique: CritiqueReport
    aggregate: AggregateResult


class WorkflowTrace(_WorkflowTraceRequired, total=False):
    """Formal trace structure matching 03_模块对接文档 §3.8.

    Required keys are in _WorkflowTraceRequired; optional keys here.
    """
    baseline: BaselineResult
    round: int
    user_feedback: str
    duration_ms: int
    errors: list[str]


# ---------------------------------------------------------------------------
# Dataclass types
# ---------------------------------------------------------------------------

@dataclass
class RoutedExpert:
    """For trace serialization. Runtime routing still uses tuple[ExpertProfile, float]."""
    key: str
    name: str
    score: float


@dataclass
class ExpertProfile:
    key: str
    name: str
    role: str
    keywords: tuple[str, ...]
    bias: float = 0.0


@dataclass
class ExpertProposal:
    expert_key: str
    expert_name: str
    role: str
    score: float
    summary: str
    recommendations: list[str]
    risks: list[str]
    confidence: float


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def normalize_task(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ensure_parent(path_text: str | None) -> None:
    if not path_text:
        return
    Path(path_text).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
