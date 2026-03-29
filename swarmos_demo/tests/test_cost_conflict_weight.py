"""Tests for core/cost.py, core/conflict.py, core/weighting.py."""
from __future__ import annotations

from core.conflict import detect_conflicts
from core.cost import build_cost_summary, estimate_tokens
from core.weighting import weighted_ranking


class TestCost:
    def test_estimate_tokens(self):
        assert estimate_tokens("hello world") >= 1

    def test_empty_proposals(self):
        c = build_cost_summary([])
        assert c["total_tokens"] == 0
        assert c["estimated_cost_usd"] == 0

    def test_with_proposals(self):
        proposals = [
            {"expert_key": "a", "summary": "test summary", "recommendations": ["r1", "r2"], "risks": ["x"]},
        ]
        c = build_cost_summary(proposals)
        assert c["total_tokens"] > 0
        assert c["estimated_cost_usd"] > 0
        assert "a" in c["per_expert"]

    def test_with_usage_map(self):
        proposals = [{"expert_key": "a", "summary": "s", "recommendations": [], "risks": []}]
        usage = {"a": {"prompt_tokens": 100, "completion_tokens": 50}}
        c = build_cost_summary(proposals, usage)
        assert c["prompt_tokens"] == 100
        assert c["completion_tokens"] == 50


class TestConflict:
    def test_empty(self):
        assert detect_conflicts([]) == []

    def test_single_proposal(self):
        assert detect_conflicts([{"expert_key": "a", "recommendations": ["x"], "risks": ["y"], "confidence": 0.8}]) == []

    def test_recommendation_vs_risk(self):
        proposals = [
            {"expert_key": "a", "expert_name": "A", "recommendations": ["use heavy caching strategy for better performance"], "risks": ["minor latency"], "confidence": 0.9},
            {"expert_key": "b", "expert_name": "B", "recommendations": ["avoid complexity overhead"], "risks": ["performance problems from caching strategy"], "confidence": 0.6},
        ]
        conflicts = detect_conflicts(proposals)
        types = {c["type"] for c in conflicts}
        assert "confidence_divergence" in types  # 0.9 vs 0.6 = 0.3 spread

    def test_no_divergence_same_confidence(self):
        proposals = [
            {"expert_key": "a", "expert_name": "A", "recommendations": ["abc"], "risks": ["xyz"], "confidence": 0.7},
            {"expert_key": "b", "expert_name": "B", "recommendations": ["def"], "risks": ["uvw"], "confidence": 0.7},
        ]
        conflicts = detect_conflicts(proposals)
        assert not any(c["type"] == "confidence_divergence" for c in conflicts)


class TestWeighting:
    def test_empty(self):
        assert weighted_ranking([]) == []

    def test_sorted_by_weight(self):
        proposals = [
            {"expert_key": "a", "expert_name": "A", "confidence": 0.5},
            {"expert_key": "b", "expert_name": "B", "confidence": 0.9},
        ]
        ranked = weighted_ranking(proposals)
        assert ranked[0]["expert_key"] == "b"

    def test_has_all_fields(self):
        proposals = [{"expert_key": "a", "expert_name": "A", "confidence": 0.8}]
        ranked = weighted_ranking(proposals)
        r = ranked[0]
        assert "confidence" in r
        assert "reputation" in r
        assert "weight" in r
