#!/usr/bin/env bash
set -euo pipefail

pkill -f "python3 -m swarmos_demo.controller --host 127.0.0.1 --port 8010" || true
pkill -f "python3 -m swarmos_demo.worker --host 127.0.0.1 --port 8021" || true
pkill -f "python3 -m swarmos_demo.worker --host 127.0.0.1 --port 8022" || true
