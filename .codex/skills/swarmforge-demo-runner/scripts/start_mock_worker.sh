#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")/../../../.." && pwd)"
ROLE="${1:-coding}"

case "$ROLE" in
  coding)
    WORKER_ID="worker-a"
    NAME="Worker-A"
    ROLE_KEY="coding_worker"
    ROLE_NAME="Coding Worker"
    PORT="8021"
    ;;
  research)
    WORKER_ID="worker-b"
    NAME="Worker-B"
    ROLE_KEY="research_worker"
    ROLE_NAME="Research Worker"
    PORT="8022"
    ;;
  *)
    echo "usage: $0 [coding|research]" >&2
    exit 1
    ;;
esac

cd "$ROOT"

CONTROLLER_URL="${CONTROLLER_URL:-http://127.0.0.1:8010}"
WORKER_BIND_HOST="${WORKER_BIND_HOST:-0.0.0.0}"
PUBLIC_HOST="${PUBLIC_HOST:-127.0.0.1}"
PUBLIC_URL="${PUBLIC_URL:-http://${PUBLIC_HOST}:${PORT}}"

exec python3 -m swarmos_demo.worker \
  --controller-url "${CONTROLLER_URL}" \
  --public-url "${PUBLIC_URL}" \
  --host "${WORKER_BIND_HOST}" \
  --port "${PORT}" \
  --provider mock \
  --worker-id "${WORKER_ID}" \
  --name "${NAME}" \
  --role-key "${ROLE_KEY}" \
  --role-name "${ROLE_NAME}"
