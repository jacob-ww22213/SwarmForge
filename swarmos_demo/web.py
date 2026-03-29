from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.serialization import workflow_result_to_dict
from core.workflow import run_demo
from providers.base import ProviderError
from web_history import list_history_records, load_history_record, save_history_record


STATIC_DIR = ROOT_DIR / "web_static"
EXAMPLES_DIR = ROOT_DIR / "examples"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SwarmOS web demo.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind. Default: 8000")
    return parser.parse_args()


def load_examples() -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for path in sorted(EXAMPLES_DIR.glob("task_*.txt")):
        examples.append(
            {
                "id": path.stem,
                "name": path.name,
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return examples


def build_run_args(body: dict[str, object]) -> argparse.Namespace:
    return argparse.Namespace(
        task=body.get("task"),
        task_file=None,
        provider=body.get("provider", "mock"),
        base_url=body.get("base_url"),
        api_key=body.get("api_key"),
        model=body.get("model"),
        top_k=int(body.get("top_k", 3)),
        baseline=True,
        update_reputation=False,
        save_markdown=None,
        save_json=None,
    )


class SwarmOSRequestHandler(BaseHTTPRequestHandler):
    server_version = "SwarmOSDemo/0.2"

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "service": "swarmos-demo-web"})
            return
        if parsed.path == "/api/examples":
            self._send_json({"examples": load_examples()})
            return
        if parsed.path == "/api/history":
            self._send_json({"runs": list_history_records()})
            return
        if parsed.path.startswith("/api/history/"):
            run_id = parsed.path.rsplit("/", 1)[-1]
            record = load_history_record(run_id)
            if record is None:
                self._send_json({"error": "History record not found."}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(record)
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            body = self._read_json_body()
            args = build_run_args(body)
            result = run_demo(args)
        except (ValueError, ProviderError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # pragma: no cover
            self._send_json({"error": f"Unexpected server error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        payload = workflow_result_to_dict(result)
        record = save_history_record(payload, top_k=args.top_k)
        self._send_json(record)

    def _read_json_body(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

    def _serve_static(self, raw_path: str) -> None:
        path = raw_path if raw_path != "/" else "/index.html"
        candidate = (STATIC_DIR / path.lstrip("/")).resolve()
        if not str(candidate).startswith(str(STATIC_DIR.resolve())) or not candidate.is_file():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        content_type, _ = mimetypes.guess_type(candidate.name)
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), SwarmOSRequestHandler)
    print(f"SwarmOS web demo running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
