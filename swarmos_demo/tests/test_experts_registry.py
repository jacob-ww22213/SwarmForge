"""Tests for experts/registry.py."""
from __future__ import annotations

from experts.registry import EXPERTS


class TestExpertsRegistry:
    def test_planner_exists(self):
        keys = {e.key for e in EXPERTS}
        assert "planner" in keys

    def test_at_least_5_experts(self):
        assert len(EXPERTS) >= 5

    def test_unique_keys(self):
        keys = [e.key for e in EXPERTS]
        assert len(keys) == len(set(keys))

    def test_all_have_keywords(self):
        for e in EXPERTS:
            assert len(e.keywords) > 0, f"{e.key} has no keywords"

    def test_all_have_system_prompt(self):
        for e in EXPERTS:
            assert e.system_prompt, f"{e.key} has no system_prompt"

    def test_temperature_range(self):
        for e in EXPERTS:
            assert 0.0 <= e.temperature <= 2.0, f"{e.key} temperature {e.temperature} out of range"

    def test_max_tokens_positive(self):
        for e in EXPERTS:
            assert e.max_tokens > 0, f"{e.key} max_tokens must be positive"
