from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
HISTORY_DIR = ROOT_DIR / "outputs" / "web_history"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def ensure_history_dir() -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return HISTORY_DIR


def make_run_id() -> str:
    return f"run_{datetime.now().strftime('%Y%m%dT%H%M%S%f')}"


def task_preview(task: str, limit: int = 72) -> str:
    collapsed = " ".join(task.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


def save_history_record(result_payload: dict, *, top_k: int) -> dict:
    ensure_history_dir()
    created_at = datetime.now().isoformat(timespec="seconds")
    run_id = make_run_id()
    record = {
        "run_id": run_id,
        "created_at": created_at,
        "provider_mode": result_payload.get("provider_mode", "unknown"),
        "top_k": top_k,
        "task_preview": task_preview(result_payload.get("task", "")),
        **result_payload,
    }
    (HISTORY_DIR / f"{run_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def list_history_records(limit: int = 50) -> list[dict]:
    ensure_history_dir()
    items: list[dict] = []
    for path in sorted(HISTORY_DIR.glob("run_*.json"), reverse=True)[:limit]:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append(
            {
                "run_id": record.get("run_id", path.stem),
                "created_at": record.get("created_at"),
                "provider_mode": record.get("provider_mode"),
                "top_k": record.get("top_k"),
                "task_preview": record.get("task_preview"),
            }
        )
    return items


def load_history_record(run_id: str) -> dict | None:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        return None
    path = ensure_history_dir() / f"{run_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
