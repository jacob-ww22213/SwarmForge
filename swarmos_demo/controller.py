#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
OUTPUTS_DIR = ROOT_DIR / "outputs" / "distributed"
TASKS_DIR = OUTPUTS_DIR / "tasks"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from distributed_common import (  # noqa: E402
    aggregate_distributed_results,
    build_distributed_metrics,
    json_request,
    load_json,
    save_json,
    utc_now_iso,
    utc_timestamp_id,
)

logger = logging.getLogger(__name__)


class ControllerState:
    def __init__(self, stale_after_s: int) -> None:
        self.stale_after_s = stale_after_s
        self._lock = Lock()
        self.workers: dict[str, dict[str, Any]] = {}

    def upsert_worker(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = payload["worker_id"]
        now = time.time()
        record = {
            "worker_id": worker_id,
            "name": payload.get("name") or worker_id,
            "role_key": payload.get("role_key") or worker_id,
            "role_name": payload.get("role_name") or "Distributed worker",
            "provider": payload.get("provider", "mock"),
            "model": payload.get("model"),
            "base_url": payload.get("base_url"),
            "public_url": payload.get("public_url"),
            "keywords": payload.get("keywords", []),
            "temperature": payload.get("temperature", 0.2),
            "max_tokens": payload.get("max_tokens", 512),
            "status": payload.get("status", "online"),
            "models_available": payload.get("models_available", []),
            "last_seen": now,
            "last_seen_iso": utc_now_iso(),
            "last_error": payload.get("last_error"),
        }
        with self._lock:
            self.workers[worker_id] = record
        return record

    def list_workers(self) -> list[dict[str, Any]]:
        now = time.time()
        items: list[dict[str, Any]] = []
        with self._lock:
            for worker in self.workers.values():
                item = dict(worker)
                item["online"] = (now - worker["last_seen"]) <= self.stale_after_s
                items.append(item)
        items.sort(key=lambda item: item["worker_id"])
        return items

    def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        with self._lock:
            worker = self.workers.get(worker_id)
            return dict(worker) if worker else None

    def online_workers(self) -> list[dict[str, Any]]:
        return [item for item in self.list_workers() if item["online"] and item.get("public_url")]


STATE = ControllerState(stale_after_s=20)


def _task_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.json"


def _save_task_record(record: dict[str, Any]) -> None:
    save_json(_task_path(record["task_id"]), record)


def _list_task_records(limit: int = 50) -> list[dict[str, Any]]:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for path in sorted(TASKS_DIR.glob("task_*.json"), reverse=True)[:limit]:
        record = load_json(path, {})
        if not record:
            continue
        items.append(
            {
                "task_id": record.get("task_id", path.stem),
                "created_at": record.get("created_at"),
                "task_preview": record.get("task", "")[:100],
                "online_worker_count": record.get("metrics", {}).get("online_worker_count", 0),
                "completed_worker_count": record.get("metrics", {}).get("completed_worker_count", 0),
                "user_rating": record.get("metrics", {}).get("user_rating"),
            }
        )
    return items


def _load_task_record(task_id: str) -> dict[str, Any] | None:
    path = _task_path(task_id)
    record = load_json(path, None)
    return record if isinstance(record, dict) else None


def _rate_task(task_id: str, rating: int, note: str) -> dict[str, Any]:
    record = _load_task_record(task_id)
    if record is None:
        raise ValueError("Task not found.")
    record.setdefault("metrics", {})
    record["metrics"]["user_rating"] = rating
    record["rating_note"] = note
    _save_task_record(record)
    return record


def _dispatch_to_worker(worker: dict[str, Any], task_id: str, task: str) -> dict[str, Any]:
    started = time.monotonic()
    payload = {
        "task_id": task_id,
        "task": task,
    }
    try:
        response = json_request(
            f"{worker['public_url'].rstrip('/')}/api/infer",
            method="POST",
            payload=payload,
            timeout=120.0,
        )
    except Exception as exc:
        return {
            "worker": worker,
            "status": "error",
            "error": str(exc),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    response["worker"] = worker
    response.setdefault("latency_ms", int((time.monotonic() - started) * 1000))
    return response


def _run_distributed_task(task: str) -> dict[str, Any]:
    task_id = utc_timestamp_id("task")
    created_at = utc_now_iso()
    workers = STATE.online_workers()
    if not workers:
        raise ValueError("No online workers available.")

    started = time.monotonic()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futures = [pool.submit(_dispatch_to_worker, worker, task_id, task) for worker in workers]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item["worker"]["worker_id"])
    total_ms = int((time.monotonic() - started) * 1000)
    aggregate = aggregate_distributed_results(task, results)
    metrics = build_distributed_metrics(
        results,
        controller_total_ms=total_ms,
        online_worker_count=len(workers),
    )
    record = {
        "task_id": task_id,
        "created_at": created_at,
        "task": task,
        "dispatch_policy": "all-online",
        "workers": [
            {
                "worker_id": worker["worker_id"],
                "name": worker["name"],
                "role_name": worker["role_name"],
                "provider": worker["provider"],
                "model": worker["model"],
                "public_url": worker["public_url"],
            }
            for worker in workers
        ],
        "worker_results": results,
        "aggregate": aggregate,
        "metrics": metrics,
    }
    _save_task_record(record)
    return record


def _proxy_worker_action(worker_id: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    worker = STATE.get_worker(worker_id)
    if worker is None or not worker.get("public_url"):
        raise ValueError("Worker not found or has no public URL.")
    return json_request(
        f"{worker['public_url'].rstrip('/')}{path}",
        method="POST",
        payload=payload,
        timeout=600.0,
    )


class ControllerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _json_response(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path in {"", "/index.html"}:
            self.path = "/distributed.html"
            return super().do_GET()

        if path == "/api/controller/status":
            workers = STATE.list_workers()
            return self._json_response(
                {
                    "service": "swarmos-controller",
                    "online_workers": len([item for item in workers if item["online"]]),
                    "known_workers": len(workers),
                    "tasks_saved": len(_list_task_records(limit=1000)),
                }
            )

        if path == "/api/workers":
            return self._json_response({"workers": STATE.list_workers()})

        if path == "/api/tasks":
            return self._json_response({"tasks": _list_task_records()})

        if path.startswith("/api/tasks/"):
            task_id = path.split("/")[-1]
            record = _load_task_record(task_id)
            if record is None:
                return self._json_response({"error": "Task not found."}, 404)
            return self._json_response(record)

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            body = self._read_body()
        except json.JSONDecodeError:
            return self._json_response({"error": "invalid JSON"}, 400)

        if path == "/api/workers/heartbeat":
            worker = STATE.upsert_worker(body)
            return self._json_response({"ok": True, "worker": worker})

        if path == "/api/tasks/run":
            task = str(body.get("task", "")).strip()
            if not task:
                return self._json_response({"error": "task is required"}, 400)
            try:
                record = _run_distributed_task(task)
            except ValueError as exc:
                return self._json_response({"error": str(exc)}, 400)
            return self._json_response(record)

        if path.endswith("/rating") and path.startswith("/api/tasks/"):
            task_id = path.split("/")[-2]
            rating = int(body.get("rating", 0))
            note = str(body.get("note", ""))
            if rating < 1 or rating > 5:
                return self._json_response({"error": "rating must be between 1 and 5"}, 400)
            try:
                record = _rate_task(task_id, rating, note)
            except ValueError as exc:
                return self._json_response({"error": str(exc)}, 404)
            return self._json_response(record)

        if path.endswith("/pull-model") and path.startswith("/api/workers/"):
            worker_id = path.split("/")[-2]
            try:
                response = _proxy_worker_action(worker_id, "/api/model/pull", {"model": body.get("model")})
            except ValueError as exc:
                return self._json_response({"error": str(exc)}, 404)
            except Exception as exc:
                return self._json_response({"error": str(exc)}, 502)
            return self._json_response(response)

        if path.endswith("/activate-model") and path.startswith("/api/workers/"):
            worker_id = path.split("/")[-2]
            try:
                response = _proxy_worker_action(worker_id, "/api/model/activate", {"model": body.get("model")})
            except ValueError as exc:
                return self._json_response({"error": str(exc)}, 404)
            except Exception as exc:
                return self._json_response({"error": str(exc)}, 502)
            return self._json_response(response)

        return self._json_response({"error": "not found"}, 404)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[controller] {args[0]} {args[1]} {args[2]}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="SwarmOS distributed controller.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--stale-after", type=int, default=20, help="Heartbeat staleness threshold in seconds.")
    args = parser.parse_args()

    global STATE
    STATE = ControllerState(stale_after_s=args.stale_after)

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer((args.host, args.port), ControllerHandler)
    print(f"SwarmOS controller running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
