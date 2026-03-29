# SwarmForge

SwarmForge is a runnable demo for a routed multi-expert AI system and a stage-3 distributed small-model network.

The repository now includes two complementary modes:
- an offline orchestration demo for routing, critique, aggregation, and baseline comparison
- a controller + worker distributed MVP where multiple machines register online, receive tasks, run local models, and report results back

The distributed console is now a single unified page:
- the server-side controller only routes tasks, tracks online nodes, and renders the task history
- model owners download small models on their own devices, start a local worker, keep heartbeats alive, and then participate in task execution

Language:
- [中文说明](./README.zh-CN.md)
- [English Guide](./README.en.md)

Release metadata:
- version: [`VERSION`](./VERSION)
- changelog: [`CHANGELOG.md`](./CHANGELOG.md)

## Quick Start

Run tests:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/python -m pytest
```

Run the CLI demo:

```bash
python3 -m swarmos_demo.cli \
  --task-file swarmos_demo/examples/task_01.txt \
  --baseline \
  --save-markdown swarmos_demo/outputs/task_01.md \
  --save-json swarmos_demo/outputs/task_01.json
```

Run the single-machine web demo:

```bash
python3 swarmos_demo/serve.py
```

Then open `http://127.0.0.1:8000`.

Run the distributed controller:

```bash
python3 -m swarmos_demo.controller --host 0.0.0.0 --port 8010
```

Run a worker on each node:

```bash
python3 -m swarmos_demo.worker \
  --controller-url http://CONTROLLER_IP:8010 \
  --public-url http://WORKER_IP:8020 \
  --host 0.0.0.0 \
  --port 8020 \
  --provider ollama \
  --base-url http://127.0.0.1:11434/v1 \
  --model qwen2.5:7b \
  --worker-id my-node-1 \
  --name "My Node" \
  --role-key coding_worker \
  --role-name "Coding Worker"
```

Then open the distributed dashboard at `http://CONTROLLER_IP:8010`.

## Versioning

This project now uses a lightweight pre-1.0 SemVer-style versioning scheme:
- `MAJOR`: breaking architecture or workflow changes
- `MINOR`: new user-facing features or major demo upgrades
- `PATCH`: bug fixes, doc fixes, and small UX improvements

Current version:
- `0.6.2`

See [`CHANGELOG.md`](./CHANGELOG.md) for release history.

## Release Scripts

The repository now includes repeatable local release scripts:

- [`scripts/start-local-demo.sh`](./scripts/start-local-demo.sh)
- [`scripts/health-check.sh`](./scripts/health-check.sh)
- [`scripts/stop-local-demo.sh`](./scripts/stop-local-demo.sh)

Typical flow:

```bash
./scripts/start-local-demo.sh mock
./scripts/health-check.sh
./scripts/stop-local-demo.sh
```

For a single-server deployment where the dashboard should be reachable from outside the machine:

```bash
CONTROLLER_BIND_HOST=0.0.0.0 CONTROLLER_PUBLIC_HOST=127.0.0.1 ./scripts/start-local-demo.sh mock
```

For persistent Linux deployment with `systemd` and local Ollama workers, see:

- [`deploy/systemd/README.md`](./deploy/systemd/README.md)
- [`scripts/install-systemd-demo.sh`](./scripts/install-systemd-demo.sh)

## Distributed Run Flow

The distributed path is:

1. start the controller
2. start Ollama on each worker machine
3. start a worker process on each worker machine
4. verify the worker appears online in the controller dashboard
5. let node owners download models from the recommended-model cards or run `ollama pull MODEL` locally
6. submit a task from the browser
7. let the controller run MoE routing and two-round MoA collaboration
8. inspect per-worker output, aggregate output, latency, and ratings

Current front-end responsibilities:
- show recommended small models with official download links
- explain how to start `ollama serve` and the SwarmForge worker on a user-owned machine
- display online node state without exposing internal demo worker ids
- submit tasks and inspect MoE routing, two-round MoA results, latency, and ratings

Important:
- the model is served by Ollama
- the node appears online only while the worker process is still running
- for real local-model demos, keep both Ollama and the worker process alive

The controller server itself does not need to host business models for the main product flow. It can run as a pure router + dashboard while external user-owned nodes attach themselves over time.

This repository also includes a local Codex skill for that flow:

- `.codex/skills/swarmforge-demo-runner/SKILL.md`

## Main Entry Points

- `swarmos_demo/cli.py`: CLI entry
- `swarmos_demo/serve.py`: canonical web server
- `swarmos_demo/web.py`: compatibility wrapper for `serve.py`
- `swarmos_demo/controller.py`: distributed controller for multi-machine orchestration
- `swarmos_demo/worker.py`: worker node service for local model execution
- `swarmos_demo/distributed_common.py`: shared distributed helpers and aggregation
- `swarmos_demo/core/workflow.py`: orchestration pipeline
- `swarmos_demo/core/router.py`: expert routing
- `swarmos_demo/providers/`: mock / OpenAI-compatible / Ollama backends
- `swarmos_demo/experts/`: expert registry, proposal, critique, aggregation
- `swarmos_demo/tests/`: automated test suite

## Docs

- [中文说明](./README.zh-CN.md)
- [English Guide](./README.en.md)
- [Technical README](./swarmos_demo/README.md)
