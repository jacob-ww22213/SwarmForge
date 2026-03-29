from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.types import ensure_parent


def save_trace(path: str, trace: dict[str, Any]) -> None:
    ensure_parent(path)
    Path(path).write_text(
        json.dumps(trace, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_markdown(path: str, content: str) -> None:
    ensure_parent(path)
    Path(path).write_text(content, encoding="utf-8")
