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

Run the offline demo (default mock provider, no network needed):

```bash
python3 cli.py --task "为一个由大量0.5B小模型组成的系统设计一个低成本demo，并给出下一步实验计划"
```

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
├── serve.py                  # Web demo server (V3, zero deps)
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
  "baseline": { "summary": "...", "recommendations": [...], ... }
}
```

## Web Demo (V3)

Start the web server (zero dependencies, pure stdlib):

```bash
python3 serve.py              # http://127.0.0.1:8000
python3 serve.py --port 9000  # custom port
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

## Suggested experiments

```bash
python3 cli.py --task "请为这个群智引擎项目设计一个 2 周内可做完的 MVP" --baseline
python3 cli.py --task "请设计一个多专家协作的代码审查系统，并指出成本控制方法" --baseline
python3 cli.py --task "请评估把法律、医疗、代码专家接入同一系统的主要风险" --baseline
```
