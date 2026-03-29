"""Backward-compatible entry point.

Usage unchanged:
    python3 swarmos_demo.py --task "..." --save-json outputs/result.json
"""
from __future__ import annotations

from cli import main

if __name__ == "__main__":
    raise SystemExit(main())
