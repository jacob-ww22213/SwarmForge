"""Tests for core/task_parser.py."""
from __future__ import annotations

from core.task_parser import analyze_task


class TestAnalyzeTask:
    def test_chinese_task(self):
        p = analyze_task("设计一个高并发系统")
        assert p["language"] == "zh"

    def test_english_task(self):
        p = analyze_task("design a high concurrency system")
        assert p["language"] == "en"

    def test_domains_detected(self):
        p = analyze_task("设计一个代码审查系统的架构")
        assert "code" in p["domains"] or "systems" in p["domains"]

    def test_actions_detected(self):
        p = analyze_task("设计并评估一个demo方案")
        assert "design" in p["actions"] or "evaluate" in p["actions"]

    def test_risk_level_medical(self):
        p = analyze_task("设计一个医疗诊断系统")
        assert p["risk_level"] == "high"

    def test_risk_level_legal(self):
        p = analyze_task("评估合规和法律风险")
        assert p["risk_level"] == "high"

    def test_mentions_demo(self):
        p = analyze_task("做一个 demo 来展示")
        assert p["mentions_demo"] is True

    def test_no_demo(self):
        p = analyze_task("设计一个生产系统")
        assert p["mentions_demo"] is False

    def test_returns_all_keys(self):
        p = analyze_task("test")
        assert set(p.keys()) == {"language", "domains", "actions", "risk_level", "mentions_demo"}
