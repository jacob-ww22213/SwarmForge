#!/bin/zsh
set -euo pipefail

if [ "$#" -lt 6 ]; then
  echo "usage: $0 <worker_id> <name> <role_key> <role_name> <model> <port>" >&2
  exit 1
fi

ROOT="/Users/jacob/Documents/cursor/0.5b 模型的畅想"
WORKER_ID="$1"
NAME="$2"
ROLE_KEY="$3"
ROLE_NAME="$4"
MODEL="$5"
PORT="$6"

cd "$ROOT"

exec python3 -m swarmos_demo.worker \
  --controller-url http://127.0.0.1:8010 \
  --public-url "http://127.0.0.1:${PORT}" \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --provider ollama \
  --base-url http://127.0.0.1:11434/v1 \
  --model "${MODEL}" \
  --worker-id "${WORKER_ID}" \
  --name "${NAME}" \
  --role-key "${ROLE_KEY}" \
  --role-name "${ROLE_NAME}"
