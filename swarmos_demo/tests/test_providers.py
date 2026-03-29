"""Tests for providers — mock, base, factory."""
from __future__ import annotations

import argparse

import pytest

from core.types import ExpertProfile
from providers import build_provider
from providers.base import BaseProvider, ProviderError
from providers.mock import MockProvider


class TestMockProvider:
    def test_mode(self):
        assert MockProvider().mode == "mock"

    def test_propose(self):
        p = MockProvider()
        expert = ExpertProfile(key="planner", name="Planner", role="Plans", keywords=("plan",))
        context = {
            "profile": {"language": "zh", "domains": [], "actions": [], "risk_level": "low", "mentions_demo": False},
            "scores": {"planner": 0.7},
        }
        proposal = p.propose(expert, "测试任务", context)
        assert proposal.expert_key == "planner"
        assert proposal.summary
        assert len(proposal.recommendations) >= 1
        assert 0 <= proposal.confidence <= 1

    def test_critique(self):
        p = MockProvider()
        expert = ExpertProfile(key="planner", name="Planner", role="Plans", keywords=("plan",))
        context = {
            "profile": {"language": "zh", "domains": [], "actions": [], "risk_level": "low", "mentions_demo": False},
            "scores": {"planner": 0.7},
        }
        proposal = p.propose(expert, "测试", context)
        critique = p.critique(task="测试", routed=[(expert, 0.7)], proposals=[proposal], context=context)
        assert "focus" in critique
        assert "duplicates" in critique
        assert "next_checks" in critique

    def test_aggregate(self):
        p = MockProvider()
        expert = ExpertProfile(key="planner", name="Planner", role="Plans", keywords=("plan",))
        context = {
            "profile": {"language": "zh", "domains": [], "actions": [], "risk_level": "low", "mentions_demo": False},
            "scores": {"planner": 0.7},
        }
        proposal = p.propose(expert, "测试", context)
        critique = p.critique(task="测试", routed=[(expert, 0.7)], proposals=[proposal], context=context)
        agg = p.aggregate(task="测试", routed=[(expert, 0.7)], proposals=[proposal], critique=critique, context=context)
        assert agg["final_summary"]
        assert len(agg["consensus"]) >= 1

    def test_baseline(self):
        p = MockProvider()
        context = {
            "profile": {"language": "zh", "domains": [], "actions": [], "risk_level": "low", "mentions_demo": True},
        }
        b = p.baseline(task="测试", context=context)
        assert b["summary"]
        assert 0 <= b["confidence"] <= 1


class TestBuildProvider:
    def test_mock(self):
        args = argparse.Namespace(provider="mock", base_url=None, api_key=None, model=None)
        p = build_provider(args)
        assert isinstance(p, MockProvider)

    def test_invalid_provider(self):
        args = argparse.Namespace(provider="invalid", base_url=None, api_key=None, model=None)
        with pytest.raises(ProviderError):
            build_provider(args)

    def test_openai_missing_config(self):
        args = argparse.Namespace(provider="openai-compatible", base_url=None, api_key=None, model=None)
        with pytest.raises(ProviderError):
            build_provider(args)


class TestBaseProvider:
    def test_propose_not_implemented(self):
        with pytest.raises(NotImplementedError):
            BaseProvider().propose(None, "", {})

    def test_critique_not_implemented(self):
        with pytest.raises(NotImplementedError):
            BaseProvider().critique("", [], [], {})

    def test_baseline_not_implemented(self):
        with pytest.raises(NotImplementedError):
            BaseProvider().baseline("", {})
