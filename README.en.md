# SwarmForge English Guide

SwarmForge is a runnable demo of a routed multi-expert AI system.

Instead of acting like one giant monolithic model, the project demonstrates a system pipeline:

1. accept a task
2. build a task profile
3. route the task to a small set of experts
4. generate expert proposals in parallel
5. run critique and duplicate checks
6. aggregate the final result
7. compare against a single-model baseline
8. save traces for replay, evaluation, and future learning

## What This Project Demonstrates

- multi-expert AI workflow orchestration
- route -> propose -> critique -> aggregate pipeline
- offline `mock` provider for easy local demos
- `openai-compatible` and `ollama` provider support
- baseline comparison
- cost estimation, conflict detection, TF-IDF routing, reputation, learned scores
- web UI demo and multi-round collaboration

## Repository Layout

- `swarmos_demo/cli.py`
  CLI entry point
- `swarmos_demo/serve.py`
  canonical web demo entry point
- `swarmos_demo/web.py`
  compatibility wrapper that forwards to `serve.py`
- `swarmos_demo/core/`
  orchestration, routing, parsing, cost, conflict, weighting, learned routing
- `swarmos_demo/providers/`
  inference backends
- `swarmos_demo/experts/`
  expert registry, proposal strategies, critic, aggregator
- `swarmos_demo/reporting/`
  console and markdown output
- `swarmos_demo/web/`
  browser UI
- `swarmos_demo/tests/`
  automated tests

## Setup

From the repository root:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
```

Run tests:

```bash
./.venv/bin/python -m pytest
```

## How To Run the Demo

### 1. Run the CLI Demo

```bash
python3 -m swarmos_demo.cli \
  --task-file swarmos_demo/examples/task_01.txt \
  --baseline \
  --save-markdown swarmos_demo/outputs/task_01.md \
  --save-json swarmos_demo/outputs/task_01.json
```

You can also pass an inline task:

```bash
python3 -m swarmos_demo.cli \
  --task "Design a multi-expert code review demo" \
  --baseline
```

### 2. Run the Web Demo

Canonical command:

```bash
python3 swarmos_demo/serve.py
```

Then open:

```text
http://127.0.0.1:8000
```

Compatibility aliases still work:

```bash
python3 -m swarmos_demo.web
python3 swarmos_demo/web.py
```

### 3. Run with Real Models

OpenAI-compatible:

```bash
python3 -m swarmos_demo.cli \
  --provider openai-compatible \
  --base-url https://your-endpoint.example/v1 \
  --api-key your-key \
  --model your-model \
  --task "Design a routed multi-expert system"
```

Ollama:

```bash
python3 -m swarmos_demo.cli \
  --provider ollama \
  --model qwen2.5:7b \
  --task "Run a local collaborative planning demo"
```

## Runtime Flow

### Node 1: Input

Entry points:
- `swarmos_demo/cli.py`
- `swarmos_demo/serve.py`

Input fields typically include:
- task
- provider
- top-k
- baseline
- budget

### Node 2: Task Parsing

`swarmos_demo/core/task_parser.py`

This generates a `TaskProfile` with:
- language
- domains
- actions
- risk_level
- mentions_demo

### Node 3: Expert Routing

`swarmos_demo/core/router.py`

Routing combines:
- base score
- expert bias
- keyword matching
- domain boosts
- reputation bonus
- learned routing bonus
- TF-IDF bonus
- budget constraints

### Node 4: Expert Proposal Generation

`swarmos_demo/core/workflow.py` calls the provider `propose()` method.

The default offline path uses:
- `swarmos_demo/providers/mock.py`

Expert behavior is defined in:
- `swarmos_demo/experts/registry.py`
- `swarmos_demo/experts/strategies.py`

### Node 5: Critique

`swarmos_demo/experts/critic.py`

Outputs:
- focus
- duplicates
- next_checks

### Node 6: Aggregation

`swarmos_demo/experts/aggregator.py`

Outputs:
- final_summary
- consensus
- next_steps
- key_risks

### Node 7: Baseline Comparison

The provider `baseline()` method generates a direct single-model style result for comparison.

### Node 8: Output and Persistence

The system produces:
- console report
- markdown report
- JSON trace

Relevant files:
- `swarmos_demo/reporting/console.py`
- `swarmos_demo/reporting/markdown.py`
- `swarmos_demo/core/storage.py`

## Common Commands

Run tests:

```bash
./.venv/bin/python -m pytest
```

Run example 1:

```bash
python3 -m swarmos_demo.cli --task-file swarmos_demo/examples/task_01.txt --baseline
```

Run example 2:

```bash
python3 -m swarmos_demo.cli --task-file swarmos_demo/examples/task_02.txt --baseline
```

Run the web demo:

```bash
python3 swarmos_demo/serve.py
```

## Further Reading

- [中文说明](./README.zh-CN.md)
- [Technical README](./swarmos_demo/README.md)
