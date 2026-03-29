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

exec python3 -m swarmos_demo.worker \
  --controller-url http://127.0.0.1:8010 \
  --public-url "http://127.0.0.1:${PORT}" \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --provider mock \
  --worker-id "${WORKER_ID}" \
  --name "${NAME}" \
  --role-key "${ROLE_KEY}" \
  --role-name "${ROLE_NAME}"
