#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
RUN_DIR="$ROOT/.swarmforge-run"

stop_pid_file() {
  local pid_file="$1"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    echo "stopped pid=$pid"
  fi
  rm -f "$pid_file"
}

stop_pid_file "$RUN_DIR/worker-a.pid"
stop_pid_file "$RUN_DIR/worker-b.pid"
stop_pid_file "$RUN_DIR/controller.pid"

echo "local demo stop requested"
