from __future__ import annotations

from typing import Any


def workflow_result_to_dict(result: dict[str, Any]) -> dict[str, Any]:
    trace = dict(result["trace"])
    return {
        "run_id": trace.get("run_id"),
        "timestamp": trace.get("timestamp"),
        "task": result["task"],
        "provider_mode": result["provider"].mode,
        "console_report": result["console_report"],
        "markdown_report": result["markdown_report"],
        "trace": trace,
        "baseline": trace.get("baseline"),
    }
