#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
UNIT_SRC="$ROOT/deploy/systemd"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
ENV_DIR="${ENV_DIR:-/etc/swarmforge}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "please run as root" >&2
  exit 1
fi

install -d "$SYSTEMD_DIR" "$ENV_DIR"

for unit in \
  swarmforge-firewall.service \
  swarmforge-controller.service \
  swarmforge-worker@.service \
  swarmforge-demo.target
do
  install -m 0644 "$UNIT_SRC/$unit" "$SYSTEMD_DIR/$unit"
done

for env_file in controller.env worker-a.env worker-b.env; do
  if [[ ! -f "$ENV_DIR/$env_file" ]]; then
    install -m 0644 "$UNIT_SRC/$env_file" "$ENV_DIR/$env_file"
  fi
done

systemctl daemon-reload

cat <<'EOF'
systemd unit files installed.

Next steps:
  systemctl enable --now ollama
  ollama pull qwen2.5:0.5b
  systemctl enable --now swarmforge-demo.target
  systemctl status swarmforge-demo.target --no-pager
EOF
