#!/bin/zsh
set -euo pipefail

ROOT="/Users/jacob/Documents/cursor/0.5b 模型的畅想"
cd "$ROOT"

exec python3 -m swarmos_demo.controller --host 127.0.0.1 --port 8010
