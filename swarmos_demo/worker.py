#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import threading
import time
from dataclasses import asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from distributed_common import (  # noqa: E402
    build_worker_expert_profile,
    guess_public_url,
    json_request,
    list_ollama_models,
    make_provider,
    pull_ollama_model,
    utc_now_iso,
)

logger = logging.getLogger(__name__)


class WorkerRuntime:
    def __init__(self, args: argparse.Namespace) -> None:
        self._lock = threading.Lock()
        self.worker_id = args.worker_id
        self.name = args.name or args.worker_id
        self.role_key = args.role_key
        self.role_name = args.role_name
        self.provider = args.provider
        self.model = args.model
        self.base_url = args.base_url
        self.api_key = args.api_key
        self.controller_url = args.controller_url.rstrip("/")
        self.host = args.host
        self.port = args.port
        self.public_url = args.public_url or guess_public_url(args.host, args.port)
        self.heartbeat_interval = args.heartbeat_interval
        self.temperature = args.temperature
        self.max_tokens = args.max_tokens
        self.stop_event = threading.Event()

    def build_provider(self):
        with self._lock:
            return make_provider(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
            )

    def status_payload(self) -> dict[str, Any]:
        with self._lock:
            models_available: list[str] = []
            if self.provider == "ollama" and self.base_url:
                try:
                    models_available = list_ollama_models(self.base_url)
                except Exception:
                    models_available = []
            return {
                "worker_id": self.worker_id,
                "name": self.name,
                "role_key": self.role_key,
                "role_name": self.role_name,
                "provider": self.provider,
                "model": self.model,
                "base_url": self.base_url,
                "public_url": self.public_url,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "status": "online",
                "models_available": models_available,
            }

    def heartbeat_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                json_request(
                    f"{self.controller_url}/api/workers/heartbeat",
                    method="POST",
                    payload=self.status_payload(),
                    timeout=10.0,
                )
            except Exception as exc:
                logger.warning("Heartbeat failed: %s", exc)
            self.stop_event.wait(self.heartbeat_interval)

    def infer(self, task_id: str, task: str) -> dict[str, Any]:
        started = time.monotonic()
        worker_meta = self.status_payload()
        expert = build_worker_expert_profile(worker_meta)
        provider = self.build_provider()
        context = {"profile": {"domains": [], "actions": [], "mentions_demo": True, "risk_level": "medium"}, "scores": {expert.key: 0.75}}
        proposal = provider.propose(expert, task, context)
        latency_ms = int((time.monotonic() - started) * 1000)
        return {
            "task_id": task_id,
            "status": "ok",
            "worker_id": self.worker_id,
            "worker_name": self.name,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": latency_ms,
            "proposal": asdict(proposal),
            "finished_at": utc_now_iso(),
        }

    def pull_model(self, model: str) -> dict[str, Any]:
        if self.provider != "ollama" or not self.base_url:
            raise ValueError("Model pull is only supported for ollama workers.")
        result = pull_ollama_model(self.base_url, model)
        with self._lock:
            self.model = model
        return {
            "ok": True,
            "model": model,
            "provider": self.provider,
            "details": result,
        }

    def activate_model(self, model: str) -> dict[str, Any]:
        with self._lock:
            self.model = model
        return {
            "ok": True,
            "model": model,
            "provider": self.provider,
        }


RUNTIME: WorkerRuntime | None = None


class WorkerHandler(BaseHTTPRequestHandler):
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
        if parsed.path == "/api/status":
            return self._json_response(RUNTIME.status_payload())  # type: ignore[union-attr]
        return self._json_response({"error": "not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            return self._json_response({"error": "invalid JSON"}, 400)

        if parsed.path == "/api/infer":
            task = str(body.get("task", "")).strip()
            task_id = str(body.get("task_id", ""))
            if not task:
                return self._json_response({"error": "task is required"}, 400)
            try:
                result = RUNTIME.infer(task_id, task)  # type: ignore[union-attr]
            except Exception as exc:
                return self._json_response({"status": "error", "error": str(exc)}, 500)
            return self._json_response(result)

        if parsed.path == "/api/model/pull":
            model = str(body.get("model", "")).strip()
            if not model:
                return self._json_response({"error": "model is required"}, 400)
            try:
                result = RUNTIME.pull_model(model)  # type: ignore[union-attr]
            except Exception as exc:
                return self._json_response({"error": str(exc)}, 500)
            return self._json_response(result)

        if parsed.path == "/api/model/activate":
            model = str(body.get("model", "")).strip()
            if not model:
                return self._json_response({"error": "model is required"}, 400)
            result = RUNTIME.activate_model(model)  # type: ignore[union-attr]
            return self._json_response(result)

        return self._json_response({"error": "not found"}, 404)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[worker] {args[0]} {args[1]} {args[2]}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="SwarmOS distributed worker.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--controller-url", required=True, help="Controller base URL, e.g. http://10.0.0.2:8010")
    parser.add_argument("--public-url", help="Public worker URL reachable by the controller.")
    parser.add_argument("--worker-id", default=socket.gethostname())
    parser.add_argument("--name", help="Display name for this worker.")
    parser.add_argument("--role-key", default="generalist_worker")
    parser.add_argument("--role-name", default="Generalist Worker")
    parser.add_argument("--provider", choices=("mock", "openai-compatible", "ollama"), default="ollama")
    parser.add_argument("--base-url", help="Provider base URL. For ollama default is http://127.0.0.1:11434/v1")
    parser.add_argument("--api-key", help="API key for openai-compatible provider.")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--heartbeat-interval", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args()

    if args.provider == "ollama" and not args.base_url:
        args.base_url = "http://127.0.0.1:11434/v1"

    global RUNTIME
    RUNTIME = WorkerRuntime(args)

    heartbeat_thread = threading.Thread(target=RUNTIME.heartbeat_loop, daemon=True)
    heartbeat_thread.start()

    server = HTTPServer((args.host, args.port), WorkerHandler)
    print(f"SwarmOS worker running at {RUNTIME.public_url}")
    print(f"Controller: {args.controller_url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        RUNTIME.stop_event.set()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
