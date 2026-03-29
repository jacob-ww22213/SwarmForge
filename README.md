# SwarmForge

SwarmForge is a runnable demo for a routed multi-expert AI system.

It shows how a task can be:
- parsed into a structured profile
- routed to a small set of experts
- answered by parallel expert proposals
- reviewed by a critic
- aggregated into a final result
- compared against a single-model baseline

Language:
- [中文说明](./README.zh-CN.md)
- [English Guide](./README.en.md)

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

Run the web demo:

```bash
python3 swarmos_demo/serve.py
```

Then open `http://127.0.0.1:8000`.

## Main Entry Points

- `swarmos_demo/cli.py`: CLI entry
- `swarmos_demo/serve.py`: canonical web server
- `swarmos_demo/web.py`: compatibility wrapper for `serve.py`
- `swarmos_demo/core/workflow.py`: orchestration pipeline
- `swarmos_demo/core/router.py`: expert routing
- `swarmos_demo/providers/`: mock / OpenAI-compatible / Ollama backends
- `swarmos_demo/experts/`: expert registry, proposal, critique, aggregation
- `swarmos_demo/tests/`: automated test suite

## Docs

- [中文说明](./README.zh-CN.md)
- [English Guide](./README.en.md)
- [Technical README](./swarmos_demo/README.md)
