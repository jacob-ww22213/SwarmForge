from __future__ import annotations

from dataclasses import dataclass


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
