"""Compatibility wrapper for the canonical web server in serve.py.

Primary entry:
    python3 serve.py

Compatible aliases:
    python3 web.py
    python3 -m swarmos_demo.web
"""
from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from serve import main


if __name__ == "__main__":
    raise SystemExit(main())
