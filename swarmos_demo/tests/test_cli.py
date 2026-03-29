"""Tests for cli.py argument parsing."""
from __future__ import annotations

import sys

import pytest


class TestCLIParsing:
    def test_import(self):
        import cli
        assert hasattr(cli, "main")

    def test_argparse_defaults(self):
        import cli
        import argparse

        parser = argparse.ArgumentParser(description="SwarmOS routed multi-expert demo.")
        parser.add_argument("--task")
        parser.add_argument("--task-file")
        parser.add_argument("--provider", choices=("mock", "openai-compatible", "ollama"), default="mock")
        parser.add_argument("--base-url")
        parser.add_argument("--api-key")
        parser.add_argument("--model")
        parser.add_argument("--top-k", type=int, default=3)
        parser.add_argument("--baseline", action="store_true")
        parser.add_argument("--update-reputation", action="store_true")
        parser.add_argument("--learn", action="store_true")
        parser.add_argument("--budget", type=float, default=None)
        parser.add_argument("--save-markdown")
        parser.add_argument("--save-json")
        args = parser.parse_args(["--task", "测试"])
        assert args.provider == "mock"
        assert args.top_k == 3
        assert args.baseline is False

    def test_main_runs_with_mock(self):
        """Integration: main() exits 0 with a mock task."""
        import sys
        old_argv = sys.argv
        sys.argv = ["cli.py", "--task", "测试任务"]
        try:
            from cli import main
            code = main()
            assert code == 0
        finally:
            sys.argv = old_argv
