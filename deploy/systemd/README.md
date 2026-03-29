# SwarmForge systemd deployment

This directory contains Linux systemd assets for running the demo as a persistent service stack.

Files:
- `swarmforge-firewall.service`: ensures TCP port `8010` is accepted by `iptables`
- `swarmforge-controller.service`: starts the public controller on `/opt/swarmforge`
- `swarmforge-worker@.service`: starts a worker instance from `/etc/swarmforge/<instance>.env`
- `swarmforge-demo.target`: starts the whole stack
- `controller.env`, `worker-a.env`, `worker-b.env`: default environment files

Typical install flow on the server:

```bash
cd /opt/swarmforge
./scripts/install-systemd-demo.sh
systemctl enable --now ollama
ollama pull qwen2.5:0.5b
systemctl enable --now swarmforge-demo.target
```
