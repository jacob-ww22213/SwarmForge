#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Condition, Lock, Thread
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
    route_workers,
    save_json,
    serialize_routing_records,
    slim_peer_result,
    utc_now_iso,
    utc_timestamp_id,
)

logger = logging.getLogger(__name__)


class ControllerState:
    def __init__(self, stale_after_s: int) -> None:
        self.stale_after_s = stale_after_s
        self._lock = Lock()
        self._condition = Condition(self._lock)
        self.workers: dict[str, dict[str, Any]] = {}
        self.worker_queues: dict[str, list[dict[str, Any]]] = {}
        self.task_results: dict[str, dict[str, dict[str, Any]]] = {}

    def upsert_worker(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker_id = payload["worker_id"]
        now = time.time()
        with self._lock:
            previous = dict(self.workers.get(worker_id, {}))
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
            "provider_ready": bool(payload.get("provider_ready", previous.get("provider_ready", True))),
            "provider_error": payload.get("provider_error", previous.get("provider_error")),
            "last_seen": now,
            "last_seen_iso": utc_now_iso(),
            "last_error": payload.get("last_error"),
            "last_pull": previous.get("last_pull"),
            "last_pull_iso": previous.get("last_pull_iso"),
            "callback_reachable": previous.get("callback_reachable"),
            "callback_error": previous.get("callback_error"),
            "callback_checked_at": previous.get("callback_checked_at"),
            "callback_checked_at_iso": previous.get("callback_checked_at_iso"),
            "callback_probe_pending": previous.get("callback_probe_pending", False),
            "callback_checked_url": previous.get("callback_checked_url"),
        }
        with self._lock:
            self.workers[worker_id] = record
            self.worker_queues.setdefault(worker_id, [])
        return record

    def list_workers(self) -> list[dict[str, Any]]:
        now = time.time()
        items: list[dict[str, Any]] = []
        with self._lock:
            for worker in self.workers.values():
                item = dict(worker)
                heartbeat_online = (now - worker["last_seen"]) <= self.stale_after_s
                last_pull = float(worker.get("last_pull") or 0.0)
                pull_online = bool(last_pull) and (now - last_pull) <= max(self.stale_after_s * 2, 30)
                provider_ready = bool(worker.get("provider_ready", True))
                ready = heartbeat_online and pull_online and provider_ready
                callback_reachable = worker.get("callback_reachable")
                item["heartbeat_online"] = heartbeat_online
                item["pull_online"] = pull_online
                item["provider_ready"] = provider_ready
                item["ready"] = ready
                item["online"] = ready
                if ready:
                    item["status_label"] = "ready"
                elif heartbeat_online:
                    item["status_label"] = "degraded"
                else:
                    item["status_label"] = "offline"
                if callback_reachable is False:
                    item["connectivity_label"] = "callback-failed"
                elif callback_reachable is True:
                    item["connectivity_label"] = "callback-ok"
                else:
                    item["connectivity_label"] = "callback-unknown"
                items.append(item)
        items.sort(key=lambda item: item["worker_id"])
        return items

    def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        with self._lock:
            worker = self.workers.get(worker_id)
            return dict(worker) if worker else None

    def online_workers(self) -> list[dict[str, Any]]:
        return [item for item in self.list_workers() if item["ready"]]

    def _mark_worker_pull_locked(self, worker_id: str) -> dict[str, Any] | None:
        worker = self.workers.get(worker_id)
        if worker is None:
            return None
        worker["last_pull"] = time.time()
        worker["last_pull_iso"] = utc_now_iso()
        return dict(worker)

    def mark_worker_pull(self, worker_id: str) -> dict[str, Any] | None:
        with self._condition:
            return self._mark_worker_pull_locked(worker_id)

    def should_probe_callback(self, worker_id: str) -> bool:
        with self._lock:
            worker = self.workers.get(worker_id)
            if worker is None or not worker.get("public_url"):
                return False
            if worker.get("callback_probe_pending"):
                return False
            last_checked = float(worker.get("callback_checked_at") or 0.0)
            if worker.get("callback_checked_url") != worker.get("public_url"):
                worker["callback_probe_pending"] = True
                return True
            if (time.time() - last_checked) >= 20:
                worker["callback_probe_pending"] = True
                return True
            return False

    def set_callback_probe_result(self, worker_id: str, *, reachable: bool, error: str | None = None) -> None:
        with self._lock:
            worker = self.workers.get(worker_id)
            if worker is None:
                return
            worker["callback_reachable"] = reachable
            worker["callback_error"] = error
            worker["callback_checked_at"] = time.time()
            worker["callback_checked_at_iso"] = utc_now_iso()
            worker["callback_probe_pending"] = False
            worker["callback_checked_url"] = worker.get("public_url")

    def enqueue_assignments(self, assignments: list[dict[str, Any]]) -> None:
        with self._condition:
            for assignment in assignments:
                worker_id = assignment["worker_id"]
                self.worker_queues.setdefault(worker_id, []).append(assignment)
                task_id = assignment["task_id"]
                self.task_results.setdefault(task_id, {})
            self._condition.notify_all()

    def next_assignment(self, worker_id: str, wait_timeout_s: float) -> dict[str, Any] | None:
        deadline = time.monotonic() + max(wait_timeout_s, 0.0)
        with self._condition:
            self._mark_worker_pull_locked(worker_id)
            while True:
                queue = self.worker_queues.setdefault(worker_id, [])
                if queue:
                    assignment = queue.pop(0)
                    self._mark_worker_pull_locked(worker_id)
                    return assignment
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._mark_worker_pull_locked(worker_id)
                    return None
                self._condition.wait(timeout=remaining)

    def submit_task_result(self, task_id: str, assignment_id: str, result: dict[str, Any]) -> None:
        with self._condition:
            bucket = self.task_results.setdefault(task_id, {})
            bucket[assignment_id] = result
            self._condition.notify_all()

    def await_task_results(
        self,
        task_id: str,
        assignment_ids: list[str],
        *,
        timeout_s: float,
    ) -> dict[str, dict[str, Any]]:
        deadline = time.monotonic() + timeout_s
        with self._condition:
            bucket = self.task_results.setdefault(task_id, {})
            while True:
                if all(assignment_id in bucket for assignment_id in assignment_ids):
                    return {assignment_id: bucket[assignment_id] for assignment_id in assignment_ids}
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {assignment_id: bucket[assignment_id] for assignment_id in assignment_ids if assignment_id in bucket}
                self._condition.wait(timeout=remaining)

    def clear_task_tracking(self, task_id: str) -> None:
        with self._condition:
            self.task_results.pop(task_id, None)


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
                "requester_role": record.get("requester_role", "project"),
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


def _probe_worker_callback(worker_id: str) -> None:
    worker = STATE.get_worker(worker_id)
    if worker is None or not worker.get("public_url"):
        return
    try:
        json_request(
            f"{worker['public_url'].rstrip('/')}/api/status",
            timeout=2.0,
        )
    except Exception as exc:
        STATE.set_callback_probe_result(worker_id, reachable=False, error=str(exc))
        return
    STATE.set_callback_probe_result(worker_id, reachable=True, error=None)


def _build_assignment(
    record: dict[str, Any],
    task_id: str,
    task: str,
    *,
    mode: str,
    round_index: int,
    peer_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "assignment_id": utc_timestamp_id("assign"),
        "task_id": task_id,
        "worker_id": record["worker_id"],
        "worker": record["worker"],
        "task": task,
        "mode": mode,
        "round_index": round_index,
        "routing_score": float(record["score"]),
        "peer_results": peer_results or [],
    }


def _run_worker_group(
    task_id: str,
    task: str,
    selected_records: list[dict[str, Any]],
    *,
    mode: str,
    round_index: int,
    peer_results: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not selected_records:
        return []
    assignments = [
        _build_assignment(
            record,
            task_id,
            task,
            mode=mode,
            round_index=round_index,
            peer_results=peer_results,
        )
        for record in selected_records
    ]
    STATE.enqueue_assignments(assignments)
    assignment_by_id = {assignment["assignment_id"]: assignment for assignment in assignments}
    round_timeout_s = 180.0
    collected = STATE.await_task_results(
        task_id,
        list(assignment_by_id.keys()),
        timeout_s=round_timeout_s,
    )
    results: list[dict[str, Any]] = []
    for assignment in assignments:
        result = collected.get(assignment["assignment_id"])
        if result is None:
            results.append(
                {
                    "task_id": task_id,
                    "assignment_id": assignment["assignment_id"],
                    "worker": assignment["worker"],
                    "worker_id": assignment["worker_id"],
                    "status": "error",
                    "error": f"worker result timeout after {int(round_timeout_s)}s",
                    "mode": mode,
                    "round_index": round_index,
                    "routing_score": round(float(assignment["routing_score"]), 3),
                    "latency_ms": int(round_timeout_s * 1000),
                }
            )
            continue
        result.setdefault("worker", assignment["worker"])
        result.setdefault("worker_id", assignment["worker_id"])
        result.setdefault("mode", mode)
        result.setdefault("round_index", round_index)
        result.setdefault("routing_score", round(float(assignment["routing_score"]), 3))
        results.append(result)
    results.sort(key=lambda item: ((item.get("round_index") or round_index), item["worker"]["worker_id"]))
    return results


def _run_distributed_task(
    task: str,
    top_k: int | None = None,
    review_top_k: int | None = None,
    requester_role: str = "project",
) -> dict[str, Any]:
    task_id = utc_timestamp_id("task")
    created_at = utc_now_iso()
    workers = STATE.online_workers()
    if not workers:
        raise ValueError("No online workers available.")

    proposal_k = min(max(top_k or 3, 1), len(workers))
    review_k = min(max(review_top_k or min(2, len(workers)), 1), len(workers))

    started = time.monotonic()
    proposal_routing = route_workers(task, workers, phase="proposal", top_k=proposal_k)
    proposal_selected = proposal_routing["selected"]
    proposal_results = _run_worker_group(
        task_id,
        task,
        proposal_selected,
        mode="proposal",
        round_index=1,
    )

    proposal_worker_ids = {record["worker_id"] for record in proposal_selected}
    peer_results = [slim_peer_result(item) for item in proposal_results if item.get("status") == "ok"]
    review_routing = route_workers(
        task,
        workers,
        phase="review",
        top_k=review_k,
        exclude_worker_ids=proposal_worker_ids,
        prior_results=proposal_results,
    )
    review_selected = review_routing["selected"]
    if not review_selected:
        review_routing = route_workers(
            task,
            workers,
            phase="review",
            top_k=review_k,
            prior_results=proposal_results,
        )
        review_selected = review_routing["selected"]

    review_results = _run_worker_group(
        task_id,
        task,
        review_selected,
        mode="review",
        round_index=2,
        peer_results=peer_results,
    )

    all_results = proposal_results + review_results
    total_ms = int((time.monotonic() - started) * 1000)
    aggregate = aggregate_distributed_results(task, proposal_results, review_results)
    metrics = build_distributed_metrics(
        all_results,
        controller_total_ms=total_ms,
        online_worker_count=len(workers),
        proposal_selected_count=len(proposal_selected),
        review_selected_count=len(review_selected),
        proposal_completed_count=len([item for item in proposal_results if item.get("status") == "ok"]),
        review_completed_count=len([item for item in review_results if item.get("status") == "ok"]),
    )
    record = {
        "task_id": task_id,
        "created_at": created_at,
        "task": task,
        "requester_role": requester_role,
        "profile": proposal_routing["profile"],
        "dispatch_policy": "moe-top-k + moa-two-round",
        "routing": {
            "proposal": serialize_routing_records(proposal_routing["selected"]),
            "review": serialize_routing_records(review_routing["selected"]),
        },
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
        "rounds": {
            "proposal": proposal_results,
            "review": review_results,
        },
        "worker_results": all_results,
        "aggregate": aggregate,
        "metrics": metrics,
    }
    _save_task_record(record)
    STATE.clear_task_tracking(task_id)
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
                    "online_workers": len([item for item in workers if item["ready"]]),
                    "ready_workers": len([item for item in workers if item["ready"]]),
                    "heartbeat_online_workers": len([item for item in workers if item["heartbeat_online"]]),
                    "callback_reachable_workers": len([item for item in workers if item.get("callback_reachable") is True]),
                    "callback_failed_workers": len([item for item in workers if item.get("callback_reachable") is False]),
                    "known_workers": len(workers),
                    "tasks_saved": len(_list_task_records(limit=1000)),
                    "dispatch_policy": "moe-top-k + moa-two-round + worker-pull",
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
            if STATE.should_probe_callback(worker["worker_id"]):
                Thread(target=_probe_worker_callback, args=(worker["worker_id"],), daemon=True).start()
            return self._json_response({"ok": True, "worker": worker})

        if path.startswith("/api/workers/") and path.endswith("/pull-task"):
            worker_id = path.split("/")[-2]
            wait_timeout_s = float(body.get("wait_timeout_s", 20.0))
            assignment = STATE.next_assignment(worker_id, wait_timeout_s=wait_timeout_s)
            worker = STATE.get_worker(worker_id)
            return self._json_response(
                {
                    "ok": True,
                    "worker_ready": bool(worker and STATE.get_worker(worker_id)),
                    "assignment": assignment,
                }
            )

        if path == "/api/tasks/run":
            task = str(body.get("task", "")).strip()
            requester_role = str(body.get("requester_role", "project")).strip() or "project"
            if not task:
                return self._json_response({"error": "task is required"}, 400)
            top_k_raw = body.get("top_k", 3)
            review_top_k_raw = body.get("review_top_k", 2)
            try:
                top_k = max(int(top_k_raw), 1)
                review_top_k = max(int(review_top_k_raw), 1)
            except (TypeError, ValueError):
                return self._json_response({"error": "top_k and review_top_k must be integers"}, 400)
            try:
                record = _run_distributed_task(
                    task,
                    top_k=top_k,
                    review_top_k=review_top_k,
                    requester_role=requester_role,
                )
            except ValueError as exc:
                return self._json_response({"error": str(exc)}, 400)
            return self._json_response(record)

        if path.startswith("/api/tasks/") and path.endswith("/worker-result"):
            task_id = path.split("/")[-2]
            assignment_id = str(body.get("assignment_id", "")).strip()
            worker_id = str(body.get("worker_id", "")).strip()
            if not assignment_id or not worker_id:
                return self._json_response({"error": "assignment_id and worker_id are required"}, 400)
            STATE.submit_task_result(task_id, assignment_id, body)
            return self._json_response({"ok": True})

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
        message = format % args if args else format
        sys.stderr.write(f"[controller] {message}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="SwarmOS distributed controller.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--stale-after", type=int, default=20, help="Heartbeat staleness threshold in seconds.")
    args = parser.parse_args()

    global STATE
    STATE = ControllerState(stale_after_s=args.stale_after)

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), ControllerHandler)
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
