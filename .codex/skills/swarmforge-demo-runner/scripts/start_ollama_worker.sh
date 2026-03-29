#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 6 ]; then
  echo "usage: $0 <worker_id> <name> <role_key> <role_name> <model> <port>" >&2
  exit 1
fi

ROOT="$(cd -- "$(dirname -- "$0")/../../../.." && pwd)"
WORKER_ID="$1"
NAME="$2"
ROLE_KEY="$3"
ROLE_NAME="$4"
MODEL="$5"
PORT="$6"
CONTROLLER_URL="${CONTROLLER_URL:-http://127.0.0.1:8010}"
WORKER_BIND_HOST="${WORKER_BIND_HOST:-0.0.0.0}"
PUBLIC_HOST="${PUBLIC_HOST:-127.0.0.1}"
PUBLIC_URL="${PUBLIC_URL:-http://${PUBLIC_HOST}:${PORT}}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"

cd "$ROOT"

exec python3 -m swarmos_demo.worker \
  --controller-url "${CONTROLLER_URL}" \
  --public-url "${PUBLIC_URL}" \
  --host "${WORKER_BIND_HOST}" \
  --port "${PORT}" \
  --provider ollama \
  --base-url "${OLLAMA_BASE_URL}" \
  --model "${MODEL}" \
  --worker-id "${WORKER_ID}" \
  --name "${NAME}" \
  --role-key "${ROLE_KEY}" \
  --role-name "${ROLE_NAME}"
