# SwarmOS Demo

A runnable MVP for two related directions:
- a routed multi-expert collaboration demo
- a stage-3 distributed controller + worker small-model network

What it demonstrates:
- Task parsing and domain detection
- Sparse expert routing with TF-IDF semantic matching, reputation scoring, learned scores, and budget constraints
- Per-expert prompt templates, temperature, and token limits
- Parallel expert proposals with fault tolerance
- Automatic conflict detection between experts
- Confidence × reputation weighted aggregation
- Critic review
- Aggregation into a final answer
- Token counting and cost estimation
- Single-model baseline comparison
- Trace saving for later inspection and evaluation
- HTTP retry with exponential backoff for real providers
- controller + worker multi-machine orchestration
- worker heartbeats and online status tracking
- MoE sparse routing to a top-k proposal worker set
- MoA second-round review and refinement on a separate top-k reviewer set
- per-worker model pull / model switch support for Ollama
- distributed task trace, latency, completion rate, and user rating capture

## Quick start

### A. Single-machine collaboration demo

From the `swarmos_demo/` directory, run the offline demo (default mock provider, no network needed):

```bash
python3 cli.py --task "为一个由大量0.5B小模型组成的系统设计一个低成本demo，并给出下一步实验计划"
```

From the repo root, you can also use the package entrypoint:

```bash
python3 -m swarmos_demo.cli \
  --task-file swarmos_demo/examples/task_01.txt \
  --save-markdown swarmos_demo/outputs/task_01.md \
  --save-json swarmos_demo/outputs/task_01.json
```

Run the web demo from the repo root with the canonical entry:

```bash
python3 swarmos_demo/serve.py
```

You can also run it from inside the `swarmos_demo/` directory:

```bash
python3 serve.py
```

Compatibility aliases still work:

```bash
python3 -m swarmos_demo.web
python3 swarmos_demo/web.py
```

Then open:

```text
http://127.0.0.1:8000
```

The web demo includes:
- a single-model baseline comparison block
- saved traces under `swarmos_demo/outputs/`
- replay and multi-round collaboration in the browser UI

Important:
- `serve.py` is the only real web server implementation
- `web.py` is now just a compatibility wrapper to avoid breaking old commands

### B. Stage-3 distributed multi-machine demo

Start the controller from the repo root:

```bash
python3 -m swarmos_demo.controller --host 0.0.0.0 --port 8010
```

On each worker machine, start a worker that points back to the controller:

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

For local smoke tests without a real model server, use `--provider mock`:

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

Open the distributed dashboard:

```text
http://CONTROLLER_IP:8010
```

The distributed UI lets you:
- view online and offline worker nodes
- trigger Ollama model downloads on a worker
- switch the active model on a worker
- switch between project-side and user-side task entry
- route the task to a proposal top-k and a review top-k
- inspect per-worker proposals and aggregate output
- rate the final result from 1 to 5

The distributed page is now a dual-role console:
- project-side operator:
  inspect the full network and publish platform tasks
- user-side node owner:
  learn how to bring a node online, download a model, keep heartbeats alive, and run user tasks

Run with a task file:

```bash
python3 cli.py \
  --task-file examples/task_01.txt \
  --save-markdown outputs/task_01.md \
  --save-json outputs/task_01.json
```

Run with baseline comparison:

```bash
python3 cli.py \
  --task-file examples/task_01.txt \
  --baseline \
  --save-json outputs/task_01.json
```

Run with reputation updates (scores evolve across runs):

```bash
python3 cli.py \
  --task-file examples/task_01.txt \
  --baseline \
  --update-reputation \
  --save-json outputs/task_01.json
```

Rebuild learned routing scores from all saved traces (V4):

```bash
python3 cli.py \
  --task-file examples/task_01.txt \
  --learn \
  --save-json outputs/task_01.json
```

Evaluate across multiple traces:

```bash
python3 evaluate.py outputs/task_01.json outputs/task_02.json outputs/task_03.json
```

## CLI flags

| Flag | Description |
|------|-------------|
| `--task TEXT` | Inline task text |
| `--task-file PATH` | Path to a UTF-8 text file with the task |
| `--provider` | `mock` (default), `openai-compatible`, or `ollama` |
| `--base-url` | Base URL for real providers |
| `--api-key` | API key for openai-compatible provider |
| `--model` | Model name for real providers |
| `--top-k N` | Number of non-planner experts to route (default 3) |
| `--baseline` | Also run a single-model baseline for comparison |
| `--update-reputation` | Update expert reputation scores after this run |
| `--learn` | Rebuild learned routing scores from all saved traces |
| `--budget USD` | Max estimated cost; low-value experts skipped when tight |
| `--save-markdown PATH` | Write markdown report |
| `--save-json PATH` | Write JSON trace |

## Provider modes

### 1. Offline mock (default)

No network or model server required.

### 2. OpenAI-compatible endpoint

```bash
export SWARMOS_API_KEY="your-key"
export SWARMOS_BASE_URL="https://your-endpoint.example/v1"
export SWARMOS_MODEL="your-model-name"

python3 cli.py --provider openai-compatible --task "设计一个多专家协作代码评审 demo"
```

### 3. Ollama

```bash
python3 cli.py --provider ollama --model qwen2.5:7b --task "用本地模型跑一个协作规划 demo"
```

## Testing

Create a local test environment:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
```

Run the tests:

```bash
./.venv/bin/python -m pytest
```

120+ tests covering types, task parser, router, TF-IDF, reputation, learned routing,
cost, conflict, weighting, workflow, serve, CLI, and the distributed stage-3 helpers.

## Project structure

```text
swarmos_demo/
├── cli.py                    # CLI entry point
├── serve.py                  # Canonical web demo server (zero deps)
├── web.py                    # Compatibility wrapper for serve.py
├── controller.py             # Distributed controller service
├── worker.py                 # Distributed worker node service
├── distributed_common.py     # Shared distributed helpers and aggregation
├── swarmos_demo.py           # Backward-compatible thin wrapper
├── evaluate.py               # Trace evaluation script
├── demo_types.py             # Re-export for backward compat
│
├── core/                     # A-line: engine & orchestration
│   ├── config.py             # Centralized constants & thresholds (V6)
│   ├── types.py              # Shared types (TypedDict + dataclass)
│   ├── task_parser.py        # Task analysis (language / domain / action / risk)
│   ├── router.py             # Expert scoring & selection with reputation + learned + TF-IDF
│   ├── tfidf_router.py       # TF-IDF cosine similarity routing, pure stdlib (V6)
│   ├── learned_router.py     # Trace-based learned routing scores (V4)
│   ├── workflow.py           # Main orchestration with fault tolerance (V4)
│   ├── storage.py            # Trace / markdown persistence
│   ├── reputation.py         # Expert reputation store
│   ├── cost.py               # Token counting & cost estimation (V5)
│   ├── conflict.py           # Inter-expert conflict detection (V5)
│   └── weighting.py          # Confidence × reputation weighting (V5)
│
├── providers/                # A-line: inference backends
│   ├── base.py               # BaseProvider abstraction
│   ├── mock.py               # Offline mock (delegates to experts/)
│   ├── openai_compatible.py  # OpenAI-compatible HTTP provider (retry + backoff V4)
│   └── ollama.py             # Ollama local provider
│
├── experts/                  # B-line: expert content & strategies
│   ├── registry.py           # 8 expert profiles
│   ├── strategies.py         # Context-aware proposal generation
│   ├── critic.py             # Critique logic
│   └── aggregator.py         # Aggregation logic
│
├── reporting/                # B-line: output formatting
│   ├── console.py            # Terminal report
│   └── markdown.py           # Markdown report with comparison table
│
├── tests/                    # pytest test suite
│   ├── conftest.py           # Shared fixtures
│   ├── test_types.py
│   ├── test_task_parser.py
│   ├── test_router.py
│   ├── test_tfidf.py
│   ├── test_workflow.py
│   ├── test_providers.py
│   ├── test_cost_conflict_weight.py
│   └── test_distributed_stage3.py
│   ├── test_reputation_learned.py
│   ├── test_serve.py
│   ├── test_experts_registry.py
│   └── test_cli.py
│
├── examples/                 # Sample task files
│   ├── task_01.txt
│   ├── task_02.txt
│   └── task_03.txt
│
├── web/                      # V3 web frontend
│   └── index.html            # Single-page app (vanilla JS)
│
├── outputs/                  # Generated results (gitignored)
└── docs/                     # Design documents
```

## JSON trace format

Each run produces a trace with:

```json
{
  "run_id": "74b083a99fce",
  "timestamp": "2026-03-29T05:14:04Z",
  "task": "...",
  "provider": "mock",
  "profile": { "language": "zh", "domains": [...], ... },
  "routed": [{ "key": "planner", "name": "Planner", "score": 0.63 }, ...],
  "proposals": [...],
  "critique": { "focus": [...], "duplicates": [...], "next_checks": [...] },
  "aggregate": { "final_summary": "...", "consensus": [...], ... },
  "baseline": { "summary": "...", "recommendations": [...], ... },
  "cost": { "total_tokens": 696, "estimated_cost_usd": 0.002676, "per_expert": {...} },
  "conflicts": [{ "type": "...", "experts": [...], "description": "..." }],
  "duration_ms": 42,
  "errors": []
}
```

## Web Demo

Start the canonical web server (zero dependencies, pure stdlib). Supports all providers.

```bash
python3 serve.py                                       # mock (default)
python3 serve.py --port 9000                           # custom port
python3 serve.py --provider openai-compatible \
  --base-url https://api.example.com/v1 \
  --api-key sk-... --model gpt-4o                      # real LLM
python3 serve.py --provider ollama --model qwen2.5:7b  # local Ollama
```

Features:
- **运行任务** — 输入任务 → 实时步骤动画 → 路由/提案/批判/聚合全流程展示，可选基线对比
- **任务回放** — 浏览已保存的 trace，逐步回放每个阶段
- **多轮协作** — 对话式交互，每轮累积上下文，专家持续改进

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/run` | POST | Run a single task `{"task":"...","top_k":3,"baseline":true,"save":true}` |
| `/api/traces` | GET | List saved traces |
| `/api/traces/<file>` | GET | Get full trace by filename |
| `/api/multi-round` | POST | Multi-round `{"task":"...","history":[...],"feedback":"..."}` |
| `/api/status` | GET | Current provider info |

## Suggested experiments

```bash
python3 cli.py --task "请为这个群智引擎项目设计一个 2 周内可做完的 MVP" --baseline
python3 cli.py --task "请设计一个多专家协作的代码审查系统，并指出成本控制方法" --baseline
python3 cli.py --task "请评估把法律、医疗、代码专家接入同一系统的主要风险" --baseline
```

## Current structure

- `swarmos_demo/swarmos_demo.py`: backward-compatible wrapper entrypoint
- `swarmos_demo/cli.py`: CLI entrypoint
- `swarmos_demo/serve.py`: canonical web demo server
- `swarmos_demo/web.py`: compatibility alias that forwards to `serve.py`
- `swarmos_demo/core/`: task parsing, routing, workflow orchestration, storage
- `swarmos_demo/providers/`: mock, openai-compatible, ollama
- `swarmos_demo/experts/`: registry, proposal strategies, critic, aggregator
- `swarmos_demo/reporting/`: console and markdown renderers
- `swarmos_demo/web/`: single-page UI assets
- `swarmos_demo/examples/`: sample task files
- `swarmos_demo/docs/`: technical docs, task split, integration contract
