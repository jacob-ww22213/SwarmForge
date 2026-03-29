# SwarmForge 中文说明

SwarmForge 现在包含两条能力线：

1. 单机协作 Demo
2. 阶段 3：多机小模型网络 Demo

单机模式用于展示 route -> propose -> critique -> aggregate 的协作链路。  
多机模式用于展示你真正想要的形态：controller 管理在线节点，worker 在各自机器上运行本地模型，用户在页面输入任务后，系统把任务分发给所有在线小模型，再汇总结果、耗时和满意度。

当前分布式前端已经是双角色控制台：
- 项目方角色：发平台任务、检查系统状态、查看路由和聚合结果
- 用户角色：下载小模型、启动本地节点、保持在线、从用户角度发任务

## 项目能做什么

- 演示多专家协作式 AI 工作流
- 展示 route -> propose -> critique -> aggregate 的完整链路
- 支持离线 `mock` provider
- 支持 `openai-compatible` 和 `ollama` provider
- 支持 baseline 对比
- 支持成本统计、冲突检测、TF-IDF 路由、reputation、learned scores
- 支持 Web 页面演示和多轮协作
- 支持 controller + worker 多机分发
- 支持节点心跳、在线状态、MoE 路由与两轮协作
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

## 版本管理

项目现在已经补上正式版本文件和变更日志：

- [VERSION](./VERSION)
- [CHANGELOG.md](./CHANGELOG.md)

版本规则采用轻量化的 pre-1.0 SemVer：
- `MAJOR`：架构或工作流有破坏性变化
- `MINOR`：新增用户可感知功能或重大 demo 升级
- `PATCH`：修复、文档更新、小型体验改进

当前版本：
- `0.5.0`

## 一键启动与健康检查

项目根目录新增了 3 个脚本：

- [start-local-demo.sh](./scripts/start-local-demo.sh)
- [health-check.sh](./scripts/health-check.sh)
- [stop-local-demo.sh](./scripts/stop-local-demo.sh)

推荐发布前自检流程：

```bash
./scripts/start-local-demo.sh mock
./scripts/health-check.sh
./scripts/stop-local-demo.sh
```

说明：
- `start-local-demo.sh mock` 会一键拉起 controller 和两个 mock worker
- `start-local-demo.sh ollama` 会尝试按 Ollama 模式拉起本地节点
- `health-check.sh` 会运行 pytest、检查 controller / workers，并分别提交项目方任务和用户任务
- `stop-local-demo.sh` 会关闭一键脚本拉起的本地进程

## Codex Skill 启动

仓库里已经自带一个本地 skill：

- `.codex/skills/swarmforge-demo-runner/SKILL.md`

用途：
- 启动 controller
- 启动 mock worker
- 启动 Ollama worker
- 检查 demo 状态
- 停止本地 demo

对应脚本在：
- `.codex/skills/swarmforge-demo-runner/scripts/start_controller.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/start_mock_worker.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/start_ollama_worker.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/check_local_demo.sh`
- `.codex/skills/swarmforge-demo-runner/scripts/stop_local_demo.sh`

如果别人下载仓库后也使用 Codex，可以直接说：

```text
使用 swarmforge-demo-runner 下载并启动本地小模型节点
```

或者直接执行脚本：

```bash
./.codex/skills/swarmforge-demo-runner/scripts/start_controller.sh
```

这个 skill 现在重点解决的是 4 件事：
- 告诉用户怎样启动 controller
- 告诉用户怎样启动 Ollama worker
- 告诉用户怎样让 worker 保持在线
- 告诉用户怎样验证节点已经在线并可接任务

需要明确区分两层：
- `Ollama` 负责真正托管小模型
- `worker` 负责把这台机器注册成在线节点

也就是说，只有同时满足下面两点，页面里这个节点才算真正可用：
- Ollama 还在运行
- worker 进程还在运行并持续发 heartbeat

如果你想让用户快速理解“下载模型并保持在线”，推荐按这个顺序操作：

1. 启动 controller
2. 在节点机器上启动 `ollama serve`
3. 启动 SwarmForge worker
4. 用页面里的“下载模型”按钮，或直接执行 `ollama pull 模型名`
5. 在页面确认节点状态是 `ONLINE`
6. 不要关闭 Ollama 或 worker 终端，否则节点会掉线

一个最小真实模型例子：

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

如果想保持在线状态更稳定，建议：
- 用单独终端标签页运行 controller 和 worker
- 或使用 `tmux` / `screen`
- 或者用 `nohup` / 进程管理器做长时间本地演示

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
- 项目方和用户两个角色都能发任务并查看结果
- 输入任务，先做 MoE 路由选择第一轮 worker，再做第二轮 MoA 精炼
- 查看每个节点的结果、耗时和聚合结果
- 给本次结果打满意度分数

### 3.2 当前前端页面的完整逻辑

1. 项目方视角
- 用于平台运营、任务发布和系统验收
- 可以查看所有在线节点
- 可以发任务并检查路由、两轮协作和最终聚合结果

2. 用户视角
- 用于节点提供者或普通用户
- 可以看到怎么下载小模型
- 可以看到如何启动本地 worker
- 可以看到怎样保持在线状态
- 也可以发任务并检查结果

3. 用户节点接入区
- 解释 `Ollama` 和 `worker` 的职责区别
- 提供推荐模型按钮
- 提供 skill 文案
- 提供保持在线的命令示例

### 3.1 当前项目的真实运行顺序

如果你要给别人演示“下载小模型并上线节点”，推荐直接照这个流程：

1. controller 机器启动 `swarmos_demo.controller`
2. worker 机器启动 `ollama serve`
3. worker 机器启动 `swarmos_demo.worker`
4. worker 自动向 controller 发 heartbeat
5. 浏览器打开 controller 页面，确认节点显示为 `ONLINE`
6. 在页面里下载或切换模型
7. 用户在页面输入任务
8. controller 执行 MoE 路由和两轮 MoA 协作
9. 页面展示每个 worker 的输出、聚合结果、耗时和评分

这一步里最容易被误解的是：
- 下载模型不等于节点在线
- 节点在线也不等于模型已经下载完成

真正可工作的条件是：
- Ollama 在运行
- 目标模型已经可用
- worker 进程在运行
- controller 能访问到 worker 的 `public_url`

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
5. controller 先做 MoE 路由，选出第一轮 proposal workers
6. 第一轮 worker 使用本地 provider 和本地模型运行推理
7. controller 把第一轮结果发给第二轮 review workers 做 MoA 精炼
8. 每个 worker 返回 proposal、耗时、模型信息和完成时间
9. controller 聚合两轮结果，生成 final summary、top recommendations、top risks
10. controller 持久化任务记录到 `swarmos_demo/outputs/distributed/tasks/`
11. 用户可以对结果做 1 到 5 分满意度打分

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
