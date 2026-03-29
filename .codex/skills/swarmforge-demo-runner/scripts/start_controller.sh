#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")/../../../.." && pwd)"
cd "$ROOT"

exec python3 -m swarmos_demo.controller --host 127.0.0.1 --port 8010
