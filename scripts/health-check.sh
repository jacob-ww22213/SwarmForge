#!/bin/zsh
set -euo pipefail

ROOT="/Users/jacob/Documents/cursor/0.5b 模型的畅想"
CONTROLLER_URL="${CONTROLLER_URL:-http://127.0.0.1:8010}"
cd "$ROOT"

wait_for_endpoint() {
  local url="$1"
  local attempts="${2:-20}"
  local sleep_s="${3:-1}"
  local i
  for (( i=1; i<=attempts; i++ )); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_s"
  done
  echo "endpoint not ready: $url" >&2
  return 1
}

echo "[1/5] pytest"
./.venv/bin/python -m pytest -q

echo
echo "[2/5] controller status"
wait_for_endpoint "$CONTROLLER_URL/api/controller/status" 20 1
curl -s "$CONTROLLER_URL/api/controller/status"

echo
echo
echo "[3/5] worker list"
wait_for_endpoint "$CONTROLLER_URL/api/workers" 20 1
curl -s "$CONTROLLER_URL/api/workers"

echo
echo
echo "[4/5] project-side task smoke test"
curl -s -X POST "$CONTROLLER_URL/api/tasks/run" \
  -H 'Content-Type: application/json' \
  -d '{"task":"请从项目方角度检查当前本地演示环境是否可用于发布前检查。","top_k":1,"review_top_k":1,"requester_role":"project"}'

echo
echo
echo "[5/5] user-side task smoke test"
curl -s -X POST "$CONTROLLER_URL/api/tasks/run" \
  -H 'Content-Type: application/json' \
  -d '{"task":"请从用户节点提供者角度检查当前本地模型节点是否已经准备好接任务。","top_k":1,"review_top_k":1,"requester_role":"user"}'

echo
echo
echo "health check completed"
