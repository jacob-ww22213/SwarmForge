# SwarmForge 中文说明

SwarmForge 现在包含两条能力线：

1. 单机协作 Demo
2. 阶段 3：多机小模型网络 Demo

单机模式用于展示 route -> propose -> critique -> aggregate 的协作链路。  
多机模式用于展示你真正想要的形态：controller 管理在线节点，worker 在各自机器上运行本地模型，用户在页面输入任务后，系统把任务分发给所有在线小模型，再汇总结果、耗时和满意度。

## 项目能做什么

- 演示多专家协作式 AI 工作流
- 展示 route -> propose -> critique -> aggregate 的完整链路
- 支持离线 `mock` provider
- 支持 `openai-compatible` 和 `ollama` provider
- 支持 baseline 对比
- 支持成本统计、冲突检测、TF-IDF 路由、reputation、learned scores
- 支持 Web 页面演示和多轮协作
- 支持 controller + worker 多机分发
- 支持节点心跳、在线状态、任务广播
- 支持 Ollama 模型下载与模型切换
- 支持分布式运行记录、耗时统计和用户评分

## 仓库结构

- `swarmos_demo/cli.py`
  CLI 入口
- `swarmos_demo/serve.py`
  Web Demo 的唯一正式入口
- `swarmos_demo/web.py`
  兼容入口，内部转发到 `serve.py`
- `swarmos_demo/controller.py`
  多机版 controller，负责节点注册、任务分发、结果聚合、指标记录
- `swarmos_demo/worker.py`
  多机版 worker，负责模型运行、心跳、推理、模型下载和切换
- `swarmos_demo/distributed_common.py`
  多机版共用工具、聚合逻辑和模型辅助函数
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

### 2. 运行单机 Web Demo

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

### 3. 运行阶段 3：多机版

先启动 controller：

```bash
python3 -m swarmos_demo.controller --host 0.0.0.0 --port 8010
```

然后在每台 worker 机器上启动一个节点。下面是 Ollama 版本：

```bash
python3 -m swarmos_demo.worker \
  --controller-url http://控制器IP:8010 \
  --public-url http://当前机器IP:8020 \
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

如果你只是先本地联调，也可以先用 mock worker：

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

最后打开 controller 页面：

```text
http://控制器IP:8010
```

页面现在支持：
- 查看在线/离线 worker
- 给 worker 下载 Ollama 模型
- 给 worker 切换当前模型
- 输入任务并广播给所有在线节点
- 查看每个节点的结果、耗时和聚合结果
- 给本次结果打满意度分数

### 4. 使用真实模型

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

### 多机版运行流程

1. controller 启动后暴露统一控制台和 API
2. 每个 worker 节点启动后向 controller 周期性发送 heartbeat
3. controller 维护在线节点列表和节点元信息
4. 用户在页面输入任务并点击分发
5. controller 把任务广播到所有在线 worker 的 `/api/infer`
6. worker 使用本地 provider 和本地模型运行推理
7. 每个 worker 返回 proposal、耗时、模型信息和完成时间
8. controller 聚合所有 proposal，生成 final summary、top recommendations、top risks
9. controller 持久化任务记录到 `swarmos_demo/outputs/distributed/tasks/`
10. 用户可以对结果做 1 到 5 分满意度打分

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
