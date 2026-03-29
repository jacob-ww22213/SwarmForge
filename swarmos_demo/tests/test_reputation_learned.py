"""Tests for core/reputation.py and core/learned_router.py."""
from __future__ import annotations

import json
from pathlib import Path

from core.learned_router import (
    learned_bonus,
    load_learned_scores,
    update_learned_scores,
)
from core.reputation import (
    get_reputation,
    load_reputation,
    reputation_bonus,
    update_reputation,
)


class TestReputation:
    def test_load_missing_file(self, tmp_path):
        assert load_reputation(tmp_path / "nope.json") == {}

    def test_load_corrupted_file(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("NOT JSON")
        assert load_reputation(f) == {}

    def test_get_reputation_default(self):
        assert get_reputation({}, "unknown") == 0.50

    def test_get_reputation_known(self):
        assert get_reputation({"planner": 0.8}, "planner") == 0.8

    def test_reputation_bonus_unknown(self):
        assert reputation_bonus({}, "unknown") == 0.50 * 0.10

    def test_update_and_load(self, tmp_path):
        path = tmp_path / "rep.json"
        proposals = [
            {"expert_key": "planner", "confidence": 0.9, "recommendations": ["a", "b"], "risks": ["r"]},
        ]
        result = update_reputation(proposals, path)
        assert "planner" in result
        loaded = load_reputation(path)
        assert "planner" in loaded


class TestLearnedRouter:
    def test_load_missing(self, tmp_path):
        assert load_learned_scores(tmp_path / "nope.json") == {}

    def test_load_corrupted(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("[1,2,3]")
        assert load_learned_scores(f) == {}

    def test_load_non_dict(self, tmp_path):
        f = tmp_path / "s.json"
        f.write_text('"hello"')
        assert load_learned_scores(f) == {}

    def test_bonus_unknown(self):
        assert learned_bonus({}, "x") == 0.0

    def test_bonus_known(self):
        b = learned_bonus({"planner": 0.7}, "planner")
        assert b > 0  # 0.7 > 0.5 default → positive bonus

    def test_update_from_traces(self, tmp_path):
        trace = {
            "proposals": [
                {"expert_key": "planner", "confidence": 0.9, "recommendations": ["a"], "risks": ["r"]},
            ],
        }
        trace_file = tmp_path / "t1.json"
        trace_file.write_text(json.dumps(trace), encoding="utf-8")
        out = tmp_path / ".learned.json"
        result = update_learned_scores(traces_dir=tmp_path, out_path=out)
        assert "planner" in result
