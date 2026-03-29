# SwarmOS Demo

This is a runnable MVP for the "many small experts + routing + collaboration" idea.

What it demonstrates:
- Task parsing
- Sparse expert routing
- Parallel expert proposals
- Critic review
- Aggregation into a final answer
- Trace saving for later inspection

What it does not prove:
- It does not prove that many 0.5B models already beat frontier models
- It does not train or run real 0.5B expert checkpoints
- The default mode is an offline mock designed to validate the workflow

## Quick start

Run the offline demo:

```bash
python3 swarmos_demo/swarmos_demo.py \
  --task "为一个由大量0.5B小模型组成的系统设计一个低成本demo，并给出下一步实验计划" \
  --save-markdown swarmos_demo/outputs/demo_result.md \
  --save-json swarmos_demo/outputs/demo_result.json
```

Run with a task file:

```bash
python3 swarmos_demo/swarmos_demo.py \
  --task-file swarmos_demo/examples/task_01.txt \
  --save-markdown swarmos_demo/outputs/task_01.md \
  --save-json swarmos_demo/outputs/task_01.json
```

## Provider modes

### 1. Offline mock

Default mode. No network or model server required.

```bash
python3 swarmos_demo/swarmos_demo.py --task "请帮我设计一个企业法务审查 demo"
```

### 2. OpenAI-compatible endpoint

This path is included so you can later swap in a real backend.

```bash
export SWARMOS_API_KEY="your-key"
export SWARMOS_BASE_URL="https://your-endpoint.example/v1"
export SWARMOS_MODEL="your-model-name"

python3 swarmos_demo/swarmos_demo.py \
  --provider openai-compatible \
  --task "设计一个多专家协作代码评审 demo"
```

Notes:
- The script calls `POST {base_url}/chat/completions`
- It uses only Python standard library HTTP
- In the current workspace this provider is not guaranteed to work without network access

### 3. Ollama

If you later install Ollama locally:

```bash
python3 swarmos_demo/swarmos_demo.py \
  --provider ollama \
  --model qwen2.5:7b \
  --task "用本地模型跑一个协作规划 demo"
```

## Output

The demo prints:
- Routed experts and scores
- Each expert proposal
- Critic notes
- Final aggregated answer

If you pass save flags, it also writes:
- Markdown report
- JSON trace

## Suggested first experiments

Try these tasks:
- `请为这个群智引擎项目设计一个 2 周内可做完的 MVP`
- `请设计一个多专家协作的代码审查系统，并指出成本控制方法`
- `请评估把法律、医疗、代码专家接入同一系统的主要风险`
- `swarmos_demo/examples/task_02.txt`
- `swarmos_demo/examples/task_03.txt`

## Files

- `swarmos_demo/swarmos_demo.py`: main CLI
- `swarmos_demo/demo_types.py`: shared expert-side data structures
- `swarmos_demo/examples/task_01.txt`: starter task
- `swarmos_demo/examples/task_02.txt`: code review demo task
- `swarmos_demo/examples/task_03.txt`: investor-facing demo task
- `swarmos_demo/outputs/`: generated demo results
- `swarmos_demo/experts/`: registry, proposal strategies, critic, aggregator
- `swarmos_demo/reporting/`: console and markdown renderers
- `swarmos_demo/docs/01_项目详细技术文档.md`: architecture and scope
- `swarmos_demo/docs/02_双人开发任务拆解文档.md`: two-person ownership and execution plan
- `swarmos_demo/docs/03_模块对接文档.md`: interface and integration contract
