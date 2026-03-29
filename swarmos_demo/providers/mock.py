from __future__ import annotations

from typing import Any

from core.types import (
    AggregateResult,
    BaselineResult,
    CritiqueReport,
    ExpertProfile,
    ExpertProposal,
)
from experts.aggregator import build_mock_aggregate
from experts.critic import build_mock_critique
from experts.strategies import build_mock_proposal
from providers.base import BaseProvider


class MockProvider(BaseProvider):
    mode = "mock"

    def propose(self, expert: ExpertProfile, task: str, context: dict[str, Any]) -> ExpertProposal:
        return build_mock_proposal(expert=expert, task=task, context=context)

    def critique(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        context: dict[str, Any],
    ) -> CritiqueReport:
        return build_mock_critique(task=task, routed=routed, proposals=proposals, context=context)

    def aggregate(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        critique: CritiqueReport,
        context: dict[str, Any],
    ) -> AggregateResult:
        return build_mock_aggregate(
            task=task,
            routed=routed,
            proposals=proposals,
            critique=critique,
            context=context,
        )

    def baseline(self, task: str, context: dict[str, Any]) -> BaselineResult:
        profile = context["profile"]

        if profile["mentions_demo"]:
            summary = (
                "这个任务需要做一个 demo，建议先确定核心场景，"
                "用最小范围实现一个可运行版本，然后给相关人展示收集反馈。"
            )
        elif profile["risk_level"] == "high":
            summary = (
                "这个任务涉及高风险领域，建议先做范围界定和风险排查，"
                "在确认安全边界后再分步推进。"
            )
        else:
            summary = (
                "这个任务可以通过一个标准方案来完成：先确定目标和范围，"
                "再分步实施，最后做验收和回顾。"
            )

        recommendations = [
            "把目标拆分为可执行的步骤，优先完成核心部分。",
            "先做最重要的部分，再逐步扩展到次要功能。",
        ]
        risks = [
            "范围失控可能导致项目延期。",
            "缺少阶段性验收容易偏离目标。",
        ]

        return {
            "summary": summary,
            "recommendations": recommendations,
            "risks": risks,
            "confidence": 0.60,
        }
