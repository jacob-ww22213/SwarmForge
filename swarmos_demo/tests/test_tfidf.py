"""Tests for core/tfidf_router.py."""
from __future__ import annotations

from core.tfidf_router import TFIDFIndex, _tokenize, tfidf_bonus
from experts.registry import EXPERTS


class TestTokenize:
    def test_english(self):
        tokens = _tokenize("design a system architecture")
        assert "design" in tokens
        assert "system" in tokens

    def test_chinese_bigrams(self):
        tokens = _tokenize("系统架构")
        assert "系统" in tokens
        assert "统架" in tokens
        assert "架构" in tokens

    def test_mixed(self):
        tokens = _tokenize("设计一个API系统")
        assert "api" in tokens
        assert any("\u4e00" <= t[0] <= "\u9fff" for t in tokens)

    def test_empty(self):
        assert _tokenize("") == []

    def test_short_english_filtered(self):
        tokens = _tokenize("a b cd ef")
        assert "a" not in tokens  # < 2 chars
        assert "cd" in tokens


class TestTFIDFIndex:
    def test_build(self):
        idx = TFIDFIndex(EXPERTS)
        scores = idx.score("设计一个分布式系统架构")
        assert "systems_architect" in scores
        assert scores["systems_architect"] > 0

    def test_medical_task(self):
        idx = TFIDFIndex(EXPERTS)
        scores = idx.score("设计一个医疗诊断系统，帮助患者诊断疾病")
        assert scores["medical_safety"] > scores["math_optimizer"]

    def test_legal_task(self):
        idx = TFIDFIndex(EXPERTS)
        scores = idx.score("评估合规法律风险和监管")
        assert scores["legal_risk"] > scores["coding_engineer"]

    def test_empty_task(self):
        idx = TFIDFIndex(EXPERTS)
        scores = idx.score("")
        assert all(v == 0.0 for v in scores.values())

    def test_scores_bounded(self):
        idx = TFIDFIndex(EXPERTS)
        scores = idx.score("代码开发实现一个demo")
        for s in scores.values():
            assert 0.0 <= s <= 1.0


class TestTfidfBonus:
    def test_returns_float(self):
        b = tfidf_bonus(EXPERTS, "测试任务", "planner")
        assert isinstance(b, float)

    def test_relevant_expert_higher(self):
        arch = tfidf_bonus(EXPERTS, "设计分布式系统架构", "systems_architect")
        med = tfidf_bonus(EXPERTS, "设计分布式系统架构", "medical_safety")
        assert arch > med

    def test_bounded(self):
        for e in EXPERTS:
            b = tfidf_bonus(EXPERTS, "任意长任务文本" * 10, e.key)
            assert 0.0 <= b <= 0.15
