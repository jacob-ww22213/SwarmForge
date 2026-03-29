from __future__ import annotations

from pathlib import Path

import swarmos_demo


def test_package_version_matches_version_file():
    repo_root = Path(__file__).resolve().parents[2]
    version_file = repo_root / "VERSION"
    assert version_file.exists()
    assert swarmos_demo.__version__ == version_file.read_text(encoding="utf-8").strip()
