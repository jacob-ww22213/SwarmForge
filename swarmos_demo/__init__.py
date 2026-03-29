from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


def _read_version() -> str:
    version_file = REPO_ROOT / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "0.0.0"


__version__ = _read_version()

# Allow legacy absolute imports like `from core...` to work both when running
# scripts inside swarmos_demo/ and when using `python3 -m swarmos_demo.*`
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))
