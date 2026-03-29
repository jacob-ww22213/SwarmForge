from __future__ import annotations

from typing import Any

from core.types import (
    AggregateResult,
    BaselineResult,
    CritiqueReport,
    ExpertProfile,
    ExpertProposal,
)


class ProviderError(RuntimeError):
    pass


class BaseProvider:
    mode = "base"

    def propose(self, expert: ExpertProfile, task: str, context: dict[str, Any]) -> ExpertProposal:
        raise NotImplementedError

    def critique(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        context: dict[str, Any],
    ) -> CritiqueReport:
        raise NotImplementedError

    def aggregate(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        critique: CritiqueReport,
        context: dict[str, Any],
    ) -> AggregateResult:
        raise NotImplementedError

    def baseline(self, task: str, context: dict[str, Any]) -> BaselineResult:
        """Single-pass generalist response without routing or collaboration."""
        raise NotImplementedError
