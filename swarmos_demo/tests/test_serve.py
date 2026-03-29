"""Tests for serve.py — path safety and API functions."""
from __future__ import annotations

from pathlib import Path

from serve import _get_trace, _list_traces, _run_multi_round, _run_single


class TestRunSingle:
    def test_basic(self):
        t = _run_single("测试任务", top_k=2)
        assert t["run_id"]
        assert len(t["proposals"]) >= 1
        assert "cost" in t
        assert "duration_ms" in t

    def test_with_baseline(self):
        t = _run_single("测试", with_baseline=True)
        assert "baseline" in t

    def test_weighted_ranking(self):
        t = _run_single("测试")
        assert "weighted_ranking" in t["aggregate"]


class TestMultiRound:
    def test_round_1(self):
        t = _run_multi_round("初始任务", [], "", top_k=2)
        assert t["round"] == 1

    def test_round_2_with_feedback(self):
        r1 = _run_multi_round("任务", [], "")
        r2 = _run_multi_round("任务", [r1], "追加需求")
        assert r2["round"] == 2
        assert "user_feedback" in r2


class TestPathSafety:
    def test_traversal_dotdot(self):
        assert _get_trace("../../etc/passwd") is None

    def test_traversal_encoded(self):
        assert _get_trace("../secret.json") is None

    def test_normal_missing_file(self):
        assert _get_trace("nonexistent_abc123.json") is None

    def test_non_json_extension(self):
        assert _get_trace("file.txt") is None

    def test_empty_filename(self):
        assert _get_trace("") is None


class TestListTraces:
    def test_returns_list(self):
        traces = _list_traces()
        assert isinstance(traces, list)
