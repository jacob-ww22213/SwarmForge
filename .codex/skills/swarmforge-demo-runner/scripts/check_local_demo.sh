#!/bin/zsh
set -euo pipefail

curl -s http://127.0.0.1:8010/api/controller/status
echo
curl -s http://127.0.0.1:8010/api/workers
echo
