#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/jacob-ww22213/SwarmForge.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/swarmforge-node}"
REPO_DIR="${REPO_DIR:-$INSTALL_DIR/SwarmForge}"
CONTROLLER_URL="${CONTROLLER_URL:-}"
PUBLIC_HOST="${PUBLIC_HOST:-}"
WORKER_BIND_HOST="${WORKER_BIND_HOST:-0.0.0.0}"
WORKER_PORT="${WORKER_PORT:-8021}"
WORKER_ID="${WORKER_ID:-my-node-1}"
WORKER_NAME="${WORKER_NAME:-My Node}"
ROLE_KEY="${ROLE_KEY:-coding_worker}"
ROLE_NAME="${ROLE_NAME:-Coding Worker}"
MODEL="${MODEL:-qwen2.5:0.5b}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
SETUP_VENV="${SETUP_VENV:-1}"
PULL_MODEL="${PULL_MODEL:-0}"

usage() {
  cat <<'EOF'
usage:
  CONTROLLER_URL=http://31.97.191.47:8010 \
  PUBLIC_HOST=<this-node-ip> \
  bash scripts/bootstrap-node.sh

environment variables:
  CONTROLLER_URL   required for remote controller registration
  PUBLIC_HOST      required for remote controller callback
  INSTALL_DIR      install root, default: $HOME/swarmforge-node
  WORKER_PORT      worker port, default: 8021
  WORKER_ID        worker id, default: my-node-1
  WORKER_NAME      worker display name, default: My Node
  ROLE_KEY         default: coding_worker
  ROLE_NAME        default: Coding Worker
  MODEL            default: qwen2.5:0.5b
  OLLAMA_BASE_URL  default: http://127.0.0.1:11434/v1
  PULL_MODEL       set to 1 to run ollama pull automatically

notes:
  - do not use 127.0.0.1 as CONTROLLER_URL on a different machine
  - PUBLIC_HOST must be reachable by the controller
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

require_cmd git
require_cmd python3
require_cmd curl
require_cmd ollama

if [[ -z "$CONTROLLER_URL" ]]; then
  echo "CONTROLLER_URL is required" >&2
  usage
  exit 1
fi

if [[ -z "$PUBLIC_HOST" ]]; then
  echo "PUBLIC_HOST is required" >&2
  usage
  exit 1
fi

mkdir -p "$INSTALL_DIR"

if [[ -d "$REPO_DIR/.git" ]]; then
  echo "repository exists, updating: $REPO_DIR"
  git -C "$REPO_DIR" pull --ff-only
else
  echo "cloning repository to: $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"

if [[ "$SETUP_VENV" == "1" ]]; then
  if [[ ! -d .venv ]]; then
    echo "creating venv"
    python3 -m venv .venv
  fi
  echo "installing python requirements"
  ./.venv/bin/pip install -r requirements-dev.txt
  PYTHON_BIN="$REPO_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

echo "checking local Ollama service"
curl -fsS "${OLLAMA_BASE_URL%/v1}/api/tags" >/dev/null

if [[ "$PULL_MODEL" == "1" ]]; then
  echo "pulling model: $MODEL"
  ollama pull "$MODEL"
fi

RUN_DIR="$REPO_DIR/.swarmforge-node"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"
PID_FILE="$RUN_DIR/worker.pid"
LOG_FILE="$LOG_DIR/worker.log"
PUBLIC_URL="http://${PUBLIC_HOST}:${WORKER_PORT}"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "stopping previous worker pid=$OLD_PID"
    kill "$OLD_PID" || true
    sleep 1
  fi
fi

echo "starting worker"
nohup "$PYTHON_BIN" -m swarmos_demo.worker \
  --controller-url "$CONTROLLER_URL" \
  --public-url "$PUBLIC_URL" \
  --host "$WORKER_BIND_HOST" \
  --port "$WORKER_PORT" \
  --provider ollama \
  --base-url "$OLLAMA_BASE_URL" \
  --model "$MODEL" \
  --worker-id "$WORKER_ID" \
  --name "$WORKER_NAME" \
  --role-key "$ROLE_KEY" \
  --role-name "$ROLE_NAME" >"$LOG_FILE" 2>&1 </dev/null &

PID="$!"
echo "$PID" > "$PID_FILE"

cat <<EOF

node bootstrap completed
repo: $REPO_DIR
worker pid: $PID
worker log: $LOG_FILE
controller: $CONTROLLER_URL
public url: $PUBLIC_URL
model: $MODEL

next checks:
  tail -f "$LOG_FILE"
  curl -s "$CONTROLLER_URL/api/workers"
EOF
