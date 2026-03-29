# SwarmForge 中文说明

SwarmForge 是一个“多专家路由协作系统”的可运行 Demo。

它的核心目标不是证明“一个更大的单体模型”，而是展示一条清晰的系统链路：

1. 输入任务
2. 解析任务画像
3. 路由到少量合适专家
4. 并行生成专家提案
5. 执行批判与去重
6. 聚合为最终结论
7. 与单模型 baseline 做对比
8. 保存 trace 供回放、评估与后续学习

## 项目能做什么

- 演示多专家协作式 AI 工作流
- 展示 route -> propose -> critique -> aggregate 的完整链路
- 支持离线 `mock` provider
- 支持 `openai-compatible` 和 `ollama` provider
- 支持 baseline 对比
- 支持成本统计、冲突检测、TF-IDF 路由、reputation、learned scores
- 支持 Web 页面演示和多轮协作

## 仓库结构

- `swarmos_demo/cli.py`
  CLI 入口
- `swarmos_demo/serve.py`
  Web Demo 的唯一正式入口
- `swarmos_demo/web.py`
  兼容入口，内部转发到 `serve.py`
- `swarmos_demo/core/`
  核心编排、路由、解析、成本、冲突、加权、学习逻辑
- `swarmos_demo/providers/`
  推理后端
- `swarmos_demo/experts/`
  专家注册表、提案策略、批判器、聚合器
- `swarmos_demo/reporting/`
  Console 和 Markdown 输出
- `swarmos_demo/web/`
  Web 前端页面
- `swarmos_demo/tests/`
  自动化测试

## 环境准备

在仓库根目录执行：

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
```

运行测试：

```bash
./.venv/bin/python -m pytest
```

## 如何运行 Demo

### 1. 运行 CLI Demo

```bash
python3 -m swarmos_demo.cli \
  --task-file swarmos_demo/examples/task_01.txt \
  --baseline \
  --save-markdown swarmos_demo/outputs/task_01.md \
  --save-json swarmos_demo/outputs/task_01.json
```

你也可以直接传任务：

```bash
python3 -m swarmos_demo.cli \
  --task "请设计一个多专家协作的代码审查 demo" \
  --baseline
```

### 2. 运行 Web Demo

推荐入口：

```bash
python3 swarmos_demo/serve.py
```

然后打开：

```text
http://127.0.0.1:8000
```

兼容入口仍可用：

```bash
python3 -m swarmos_demo.web
python3 swarmos_demo/web.py
```

### 3. 使用真实模型

OpenAI-compatible:

```bash
python3 -m swarmos_demo.cli \
  --provider openai-compatible \
  --base-url https://your-endpoint.example/v1 \
  --api-key your-key \
  --model your-model \
  --task "设计一个多专家协作系统"
```

Ollama:

```bash
python3 -m swarmos_demo.cli \
  --provider ollama \
  --model qwen2.5:7b \
  --task "用本地模型跑一个协作规划 demo"
```

## Demo 的运行流程

### 节点 1：输入

入口文件：
- `swarmos_demo/cli.py`
- `swarmos_demo/serve.py`

输入内容包括：
- task
- provider
- top-k
- baseline
- budget

### 节点 2：任务解析

`swarmos_demo/core/task_parser.py`

这里会生成 `TaskProfile`，包括：
- language
- domains
- actions
- risk_level
- mentions_demo

### 节点 3：专家路由

`swarmos_demo/core/router.py`

路由分数由这些因素构成：
- 基础分
- 专家 bias
- 关键词匹配
- 领域匹配 boost
- reputation bonus
- learned bonus
- TF-IDF bonus
- budget 约束

### 节点 4：专家提案

`swarmos_demo/core/workflow.py` 调用 provider 的 `propose`

默认离线模式使用：
- `swarmos_demo/providers/mock.py`

专家内容定义在：
- `swarmos_demo/experts/registry.py`
- `swarmos_demo/experts/strategies.py`

### 节点 5：批判

`swarmos_demo/experts/critic.py`

输出：
- focus
- duplicates
- next_checks

### 节点 6：聚合

`swarmos_demo/experts/aggregator.py`

输出：
- final_summary
- consensus
- next_steps
- key_risks

### 节点 7：Baseline 对比

provider 的 `baseline()` 会生成单模型直出结果，用于和多专家协作结果对比。

### 节点 8：输出与持久化

输出文件：
- Console report
- Markdown report
- JSON trace

相关文件：
- `swarmos_demo/reporting/console.py`
- `swarmos_demo/reporting/markdown.py`
- `swarmos_demo/core/storage.py`

## 常用命令

运行测试：

```bash
./.venv/bin/python -m pytest
```

运行样例 1：

```bash
python3 -m swarmos_demo.cli --task-file swarmos_demo/examples/task_01.txt --baseline
```

运行样例 2：

```bash
python3 -m swarmos_demo.cli --task-file swarmos_demo/examples/task_02.txt --baseline
```

运行 Web：

```bash
python3 swarmos_demo/serve.py
```

## 进一步阅读

- [English Guide](./README.en.md)
- [详细技术说明](./swarmos_demo/README.md)
