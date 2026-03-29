#!/bin/zsh
set -euo pipefail

ROOT="/Users/jacob/Documents/cursor/0.5b 模型的畅想"
RUN_DIR="$ROOT/.swarmforge-run"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

MODE="${1:-mock}"
CONTROLLER_HOST="${CONTROLLER_HOST:-127.0.0.1}"
CONTROLLER_PORT="${CONTROLLER_PORT:-8010}"
WORKER_A_PORT="${WORKER_A_PORT:-8021}"
WORKER_B_PORT="${WORKER_B_PORT:-8022}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
MODEL_A="${MODEL_A:-qwen2.5:7b}"
MODEL_B="${MODEL_B:-qwen2.5:7b}"

cd "$ROOT"

start_if_missing() {
  local pid_file="$1"
  shift
  local log_file="$1"
  shift
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "already running: pid=$pid command=$*"
      return 0
    fi
  fi
  nohup "$@" >"$log_file" 2>&1 </dev/null &!
  local pid=$!
  echo "$pid" > "$pid_file"
  echo "started: pid=$pid command=$*"
}

start_if_missing \
  "$RUN_DIR/controller.pid" \
  "$LOG_DIR/controller.log" \
  python3 -m swarmos_demo.controller --host "$CONTROLLER_HOST" --port "$CONTROLLER_PORT"

if [[ "$MODE" == "mock" ]]; then
  start_if_missing \
    "$RUN_DIR/worker-a.pid" \
    "$LOG_DIR/worker-a.log" \
    python3 -m swarmos_demo.worker \
      --host 127.0.0.1 \
      --port "$WORKER_A_PORT" \
      --public-url "http://127.0.0.1:${WORKER_A_PORT}" \
      --controller-url "http://${CONTROLLER_HOST}:${CONTROLLER_PORT}" \
      --provider mock \
      --worker-id worker-a \
      --name Worker-A \
      --role-key coding_worker \
      --role-name "Coding Worker"

  start_if_missing \
    "$RUN_DIR/worker-b.pid" \
    "$LOG_DIR/worker-b.log" \
    python3 -m swarmos_demo.worker \
      --host 127.0.0.1 \
      --port "$WORKER_B_PORT" \
      --public-url "http://127.0.0.1:${WORKER_B_PORT}" \
      --controller-url "http://${CONTROLLER_HOST}:${CONTROLLER_PORT}" \
      --provider mock \
      --worker-id worker-b \
      --name Worker-B \
      --role-key research_worker \
      --role-name "Research Worker"
elif [[ "$MODE" == "ollama" ]]; then
  start_if_missing \
    "$RUN_DIR/worker-a.pid" \
    "$LOG_DIR/worker-a.log" \
    python3 -m swarmos_demo.worker \
      --host 127.0.0.1 \
      --port "$WORKER_A_PORT" \
      --public-url "http://127.0.0.1:${WORKER_A_PORT}" \
      --controller-url "http://${CONTROLLER_HOST}:${CONTROLLER_PORT}" \
      --provider ollama \
      --base-url "$OLLAMA_BASE_URL" \
      --model "$MODEL_A" \
      --worker-id worker-a \
      --name Worker-A \
      --role-key coding_worker \
      --role-name "Coding Worker"

  start_if_missing \
    "$RUN_DIR/worker-b.pid" \
    "$LOG_DIR/worker-b.log" \
    python3 -m swarmos_demo.worker \
      --host 127.0.0.1 \
      --port "$WORKER_B_PORT" \
      --public-url "http://127.0.0.1:${WORKER_B_PORT}" \
      --controller-url "http://${CONTROLLER_HOST}:${CONTROLLER_PORT}" \
      --provider ollama \
      --base-url "$OLLAMA_BASE_URL" \
      --model "$MODEL_B" \
      --worker-id worker-b \
      --name Worker-B \
      --role-key research_worker \
      --role-name "Research Worker"
else
  echo "unsupported mode: $MODE" >&2
  echo "usage: $0 [mock|ollama]" >&2
  exit 1
fi

echo
echo "local demo start requested"
echo "controller: http://${CONTROLLER_HOST}:${CONTROLLER_PORT}"
echo "mode: $MODE"
echo "logs: $LOG_DIR"
echo "next step: ./scripts/health-check.sh"
