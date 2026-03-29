# SwarmForge English Guide

SwarmForge now includes two complementary tracks:

1. a single-machine routed multi-expert demo
2. a stage-3 distributed small-model network demo

The distributed mode is the closer match to the target product: a controller tracks online worker nodes, each worker runs a local model, the browser sends a task to the controller, and the controller dispatches that task to all online small-model nodes before aggregating results, latency, and user satisfaction.

The distributed front-end now serves two roles:
- project-side operator
- user-side node owner

Both roles can submit tasks and inspect results from the same page, while the user-side view also explains model download, worker startup, and how to keep a node online.

## What This Project Demonstrates

- multi-expert AI workflow orchestration
- route -> propose -> critique -> aggregate pipeline
- offline `mock` provider for easy local demos
- `openai-compatible` and `ollama` provider support
- baseline comparison
- cost estimation, conflict detection, TF-IDF routing, reputation, learned scores
- web UI demo and multi-round collaboration
- controller + worker multi-machine orchestration
- worker heartbeats and online node tracking
- Ollama model pull and model switch actions from the dashboard
- distributed task history, latency metrics, and user ratings

## Repository Layout

- `swarmos_demo/cli.py`
  CLI entry point
- `swarmos_demo/serve.py`
  canonical web demo entry point
- `swarmos_demo/web.py`
  compatibility wrapper that forwards to `serve.py`
- `swarmos_demo/controller.py`
  distributed controller for worker registration, task dispatch, aggregation, and metrics
- `swarmos_demo/worker.py`
  worker node service for local model execution, heartbeats, model pull, and model switch
- `swarmos_demo/distributed_common.py`
  shared distributed helpers, aggregation logic, and Ollama utilities
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

## Codex Skill Launcher

This repository now includes a local Codex skill:

- `.codex/skills/swarmforge-demo-runner/SKILL.md`

It can be used to:
- start the controller
- start mock workers
- start Ollama workers
- verify local demo status
- stop the local demo

Bundled scripts:
- `.codex/skills/swarmforge-demo-runner/scripts/start_controller.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/start_mock_worker.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/start_ollama_worker.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/check_local_demo.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/stop_local_demo.sh`

If another Codex user has the repo locally, they can invoke it with a request like:

```text
Use swarmforge-demo-runner to download and launch a local model worker
```

This skill is meant to explain and automate four things:
- how to start the controller
- how to start an Ollama-backed worker
- how to keep the worker online
- how to verify that the node is actually available to the controller

There are two separate runtime layers:
- `Ollama` hosts the local model
- the SwarmForge `worker` keeps that machine registered as an online node

So a node is only truly usable when:
- Ollama is still running
- the worker process is still running and sending heartbeats

Recommended operator flow:

1. start the controller
2. run `ollama serve` on the worker machine
3. start the SwarmForge worker
4. pull the model from the dashboard, or run `ollama pull MODEL`
5. verify the node appears as `ONLINE`
6. keep both Ollama and the worker process alive

Minimal real-model example:

```bash
ollama serve
```

```bash
ollama pull qwen2.5:7b
```

```bash
python3 -m swarmos_demo.worker \
  --controller-url http://127.0.0.1:8010 \
  --public-url http://127.0.0.1:8021 \
  --host 127.0.0.1 \
  --port 8021 \
  --provider ollama \
  --base-url http://127.0.0.1:11434/v1 \
  --model qwen2.5:7b \
  --worker-id worker-a \
  --name Worker-A \
  --role-key coding_worker \
  --role-name "Coding Worker"
```

For a more stable local demo, keep the controller and worker in separate terminal tabs or run them under `tmux`, `screen`, or another long-running process manager.

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

### 2. Run the Single-Machine Web Demo

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

### 3. Run Stage 3 Distributed Mode

Start the controller:

```bash
python3 -m swarmos_demo.controller --host 0.0.0.0 --port 8010
```

Start one worker on each node. Example with Ollama:

```bash
python3 -m swarmos_demo.worker \
  --controller-url http://CONTROLLER_IP:8010 \
  --public-url http://WORKER_IP:8020 \
  --host 0.0.0.0 \
  --port 8020 \
  --provider ollama \
  --base-url http://127.0.0.1:11434/v1 \
  --model qwen2.5:7b \
  --worker-id worker-a \
  --name Worker-A \
  --role-key coding_worker \
  --role-name "Coding Worker"
```

For local smoke tests, you can start a mock worker instead:

```bash
python3 -m swarmos_demo.worker \
  --controller-url http://127.0.0.1:8010 \
  --public-url http://127.0.0.1:8021 \
  --host 127.0.0.1 \
  --port 8021 \
  --provider mock \
  --worker-id worker-a \
  --name Worker-A \
  --role-key coding_worker \
  --role-name "Coding Worker"
```

Then open:

```text
http://CONTROLLER_IP:8010
```

The distributed dashboard supports:
- online/offline worker visibility
- Ollama model download per worker
- model switching per worker
- both project-side and user-side task submission
- MoE top-k routing for proposal workers and MoA second-round review workers
- per-worker results, latency, and aggregated output
- 1 to 5 user satisfaction ratings

### 3.2 Full front-end logic

1. Project-side view
- publish platform tasks
- inspect global worker state
- review routing, collaboration output, aggregate output, latency, and rating

2. User-side view
- understand how to download a local small model
- understand how to start a worker node
- understand how to keep the node online
- submit user tasks and inspect results

3. User node onboarding section
- explains the difference between `Ollama` and the SwarmForge `worker`
- includes recommended model buttons
- includes the skill prompt
- includes example commands for keeping a node online

### 3.1 Actual operator run order

If you want other users to understand the current project flow clearly, use this exact order:

1. start `swarmos_demo.controller` on the controller machine
2. run `ollama serve` on each worker machine
3. start `swarmos_demo.worker` on each worker machine
4. let workers register and send heartbeats
5. open the controller page and confirm the node is `ONLINE`
6. pull or switch the model
7. submit a task from the browser
8. let the controller run MoE routing and two-round MoA collaboration
9. inspect worker outputs, aggregate output, latency, and rating

The most important distinction is:
- downloading a model is not the same as having an online node
- having an online node is not the same as having a ready local model

The system works only when all of these are true:
- Ollama is running
- the target model exists locally
- the worker process is running
- the controller can reach the worker `public_url`

### 4. Run with Real Models

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

### Distributed Runtime Flow

1. the controller starts and exposes a dashboard plus task APIs
2. each worker starts, loads its local provider, and sends heartbeats to the controller
3. the controller maintains online worker state and metadata
4. the user enters a task in the browser
5. the controller first routes the task to a top-k proposal worker set
6. the proposal workers run their local models and return first-round proposals
7. the controller then routes round-1 outputs to a top-k review worker set for refinement
8. the controller aggregates both rounds into a final summary, recommendations, and risks
9. the controller stores the task record under `swarmos_demo/outputs/distributed/tasks/`
10. the user can rate the output for later evaluation

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
