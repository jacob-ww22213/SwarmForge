"""Tests for core/workflow.py — the main orchestration pipeline."""
from __future__ import annotations

import pytest

from core.workflow import run_demo


class TestRunDemo:
    def test_basic_run(self, mock_args):
        result = run_demo(mock_args)
        assert "trace" in result
        assert "console_report" in result
        assert "markdown_report" in result

    def test_trace_has_required_fields(self, mock_args):
        trace = run_demo(mock_args)["trace"]
        for key in ("run_id", "timestamp", "task", "provider", "profile",
                     "routed", "proposals", "critique", "aggregate"):
            assert key in trace, f"missing key: {key}"

    def test_trace_has_cost(self, mock_args):
        trace = run_demo(mock_args)["trace"]
        assert "cost" in trace
        assert trace["cost"]["total_tokens"] > 0

    def test_trace_has_weighted_ranking(self, mock_args):
        trace = run_demo(mock_args)["trace"]
        wr = trace["aggregate"].get("weighted_ranking")
        assert wr is not None
        assert len(wr) > 0

    def test_trace_has_duration(self, mock_args):
        trace = run_demo(mock_args)["trace"]
        assert "duration_ms" in trace
        assert isinstance(trace["duration_ms"], int)

    def test_baseline_when_requested(self, mock_args):
        mock_args.baseline = True
        trace = run_demo(mock_args)["trace"]
        assert "baseline" in trace
        assert trace["baseline"]["confidence"] > 0

    def test_no_baseline_by_default(self, mock_args):
        trace = run_demo(mock_args)["trace"]
        assert "baseline" not in trace

    def test_proposals_count(self, mock_args):
        trace = run_demo(mock_args)["trace"]
        assert len(trace["proposals"]) >= 2  # planner + at least 1

    def test_no_task_raises(self, mock_args):
        mock_args.task = ""
        mock_args.task_file = None
        with pytest.raises(ValueError, match="Provide"):
            run_demo(mock_args)

    def test_task_file(self, mock_args, tmp_path):
        f = tmp_path / "task.txt"
        f.write_text("来自文件的测试任务", encoding="utf-8")
        mock_args.task = None
        mock_args.task_file = str(f)
        trace = run_demo(mock_args)["trace"]
        assert "来自文件的测试任务" in trace["task"]

    def test_budget_reduces_experts(self):
        import argparse
        args = argparse.Namespace(
            task="预算测试", task_file=None, provider="mock",
            base_url=None, api_key=None, model=None,
            top_k=5, baseline=False, update_reputation=False, budget=0.0,
        )
        trace = run_demo(args)["trace"]
        assert len(trace["proposals"]) == 1  # only planner
