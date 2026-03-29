from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def mock_args():
    """Minimal argparse.Namespace for mock provider runs."""
    return argparse.Namespace(
        task="测试任务：设计一个高并发短链服务",
        task_file=None,
        provider="mock",
        base_url=None,
        api_key=None,
        model=None,
        top_k=3,
        baseline=False,
        update_reputation=False,
        budget=None,
    )


@pytest.fixture
def mock_args_full(mock_args):
    """Full-featured args with all optional flags."""
    mock_args.baseline = True
    mock_args.budget = 1.0
    return mock_args
