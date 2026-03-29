"""Tests for core/router.py."""
from __future__ import annotations

from core.router import route_experts, score_expert
from core.task_parser import analyze_task
from experts.registry import EXPERTS


class TestScoreExpert:
    def test_planner_always_high(self):
        profile = analyze_task("随便一个任务")
        planner = next(e for e in EXPERTS if e.key == "planner")
        score = score_expert(planner, "随便一个任务", profile)
        assert score >= 0.4

    def test_keyword_boost(self):
        profile = analyze_task("设计一个架构")
        arch = next(e for e in EXPERTS if e.key == "systems_architect")
        score = score_expert(arch, "设计一个系统架构", profile)
        assert score > 0.3

    def test_score_clamped(self):
        for expert in EXPERTS:
            profile = analyze_task("test")
            s = score_expert(expert, "test", profile)
            assert 0.0 <= s <= 1.0


class TestRouteExperts:
    def test_planner_always_included(self):
        profile = analyze_task("任意任务")
        selected, _ = route_experts("任意任务", profile, top_k=3)
        keys = {e.key for e, _ in selected}
        assert "planner" in keys

    def test_top_k_respected(self):
        profile = analyze_task("任意任务")
        selected, _ = route_experts("任意任务", profile, top_k=2)
        assert len(selected) <= 2 + 1  # +1 for planner

    def test_top_k_zero(self):
        profile = analyze_task("任意任务")
        selected, _ = route_experts("任意任务", profile, top_k=0)
        assert len(selected) == 1
        assert selected[0][0].key == "planner"

    def test_score_map_complete(self):
        profile = analyze_task("任意任务")
        _, score_map = route_experts("任意任务", profile, top_k=3)
        assert len(score_map) == len(EXPERTS)

    def test_budget_limits_experts(self):
        profile = analyze_task("任意任务")
        full, _ = route_experts("任意任务", profile, top_k=5)
        budget, _ = route_experts("任意任务", profile, top_k=5, budget=0.0001)
        assert len(budget) <= len(full)

    def test_budget_none_no_effect(self):
        profile = analyze_task("任意任务")
        a, _ = route_experts("任意任务", profile, top_k=3, budget=None)
        b, _ = route_experts("任意任务", profile, top_k=3)
        assert len(a) == len(b)
