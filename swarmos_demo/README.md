# SwarmOS Demo

A runnable MVP for the "many small experts + routing + collaboration" idea.

What it demonstrates:
- Task parsing and domain detection
- Sparse expert routing with reputation scoring
- Parallel expert proposals
- Critic review
- Aggregation into a final answer
- Single-model baseline comparison
- Trace saving for later inspection and evaluation

## Quick start

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

Run the web demo from the repo root:

```bash
python3 -m swarmos_demo.web --host 127.0.0.1 --port 8000
```

Or from the `swarmos_demo/` directory:

```bash
python3 web.py --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The web demo includes:
- a single-model baseline comparison block
- persisted run history under `swarmos_demo/outputs/web_history/`
- clickable trace playback from the browser UI

Important:
- `python3 -m swarmos_demo.web` must be run from the repo root
- if you are already inside `swarmos_demo/`, use `python3 web.py`

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

## Project structure

```text
swarmos_demo/
├── cli.py                    # CLI entry point
├── swarmos_demo.py           # Backward-compatible thin wrapper
├── evaluate.py               # Trace evaluation script
├── demo_types.py             # Re-export for backward compat
│
├── core/                     # A-line: engine & orchestration
│   ├── types.py              # Shared types (TypedDict + dataclass)
│   ├── task_parser.py        # Task analysis (language / domain / action / risk)
│   ├── router.py             # Expert scoring & selection with reputation
│   ├── workflow.py           # Main orchestration pipeline
│   ├── storage.py            # Trace / markdown persistence
│   └── reputation.py         # Expert reputation store
│
├── providers/                # A-line: inference backends
│   ├── base.py               # BaseProvider abstraction
│   ├── mock.py               # Offline mock (delegates to experts/)
│   ├── openai_compatible.py  # OpenAI-compatible HTTP provider
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
├── examples/                 # Sample task files
│   ├── task_01.txt
│   ├── task_02.txt
│   └── task_03.txt
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
  "baseline": { "summary": "...", "recommendations": [...], ... }
}
```

## Suggested experiments

```bash
python3 cli.py --task "请为这个群智引擎项目设计一个 2 周内可做完的 MVP" --baseline
python3 cli.py --task "请设计一个多专家协作的代码审查系统，并指出成本控制方法" --baseline
python3 cli.py --task "请评估把法律、医疗、代码专家接入同一系统的主要风险" --baseline
```

## Current structure

- `swarmos_demo/swarmos_demo.py`: backward-compatible wrapper entrypoint
- `swarmos_demo/cli.py`: CLI entrypoint
- `swarmos_demo/web.py`: local zero-dependency web demo server
- `swarmos_demo/web_history.py`: local run-history persistence and replay metadata
- `swarmos_demo/core/`: task parsing, routing, workflow orchestration, serialization, storage
- `swarmos_demo/providers/`: mock, openai-compatible, ollama
- `swarmos_demo/experts/`: registry, proposal strategies, critic, aggregator
- `swarmos_demo/reporting/`: console and markdown renderers
- `swarmos_demo/web_static/`: single-page UI assets
- `swarmos_demo/examples/`: sample task files
- `swarmos_demo/docs/`: technical docs, task split, integration contract
