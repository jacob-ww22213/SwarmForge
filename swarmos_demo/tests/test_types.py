"""Tests for core/types.py — shared data structures and utilities."""
from __future__ import annotations

from core.types import (
    AggregateResult,
    BaselineResult,
    CostSummary,
    CritiqueReport,
    ExpertProfile,
    ExpertProposal,
    RoutedExpert,
    TaskProfile,
    TaskRequest,
    WorkflowTrace,
    clamp,
    contains_cjk,
    ensure_parent,
    normalize_task,
)


class TestUtilities:
    def test_contains_cjk_chinese(self):
        assert contains_cjk("设计一个系统") is True

    def test_contains_cjk_english(self):
        assert contains_cjk("design a system") is False

    def test_contains_cjk_mixed(self):
        assert contains_cjk("hello 你好") is True

    def test_contains_cjk_empty(self):
        assert contains_cjk("") is False

    def test_normalize_task(self):
        assert normalize_task("  hello   world  ") == "hello world"

    def test_normalize_task_newlines(self):
        assert normalize_task("line1\n  line2\n") == "line1 line2"

    def test_clamp_within(self):
        assert clamp(0.5, 0.0, 1.0) == 0.5

    def test_clamp_below(self):
        assert clamp(-1.0, 0.0, 1.0) == 0.0

    def test_clamp_above(self):
        assert clamp(2.0, 0.0, 1.0) == 1.0

    def test_ensure_parent_none(self):
        ensure_parent(None)

    def test_ensure_parent_empty(self):
        ensure_parent("")


class TestDataclasses:
    def test_expert_profile_defaults(self):
        ep = ExpertProfile(key="test", name="Test", role="test role", keywords=("a",))
        assert ep.bias == 0.0
        assert ep.temperature == 0.2
        assert ep.max_tokens == 512
        assert ep.system_prompt == ""

    def test_expert_proposal(self):
        p = ExpertProposal(
            expert_key="k", expert_name="N", role="R",
            score=0.5, summary="S", recommendations=["r"], risks=["x"], confidence=0.8,
        )
        assert p.expert_key == "k"
        assert p.confidence == 0.8

    def test_routed_expert(self):
        re = RoutedExpert(key="k", name="N", score=0.7)
        assert re.score == 0.7


class TestTypedDicts:
    def test_task_profile_is_dict(self):
        tp: TaskProfile = {
            "language": "zh", "domains": ["code"], "actions": ["design"],
            "risk_level": "low", "mentions_demo": True,
        }
        assert tp["language"] == "zh"

    def test_critique_report_is_dict(self):
        cr: CritiqueReport = {"focus": ["a"], "duplicates": [], "next_checks": ["b"]}
        assert isinstance(cr, dict)

    def test_aggregate_result_optional_weighted(self):
        ar: AggregateResult = {
            "selected_experts": [], "consensus": [], "critique_focus": [],
            "next_steps": [], "key_risks": [], "final_summary": "s",
        }
        assert "weighted_ranking" not in ar
        ar["weighted_ranking"] = [{"expert_key": "p", "weight": 0.5}]
        assert len(ar["weighted_ranking"]) == 1
