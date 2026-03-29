# SwarmOS Demo Report

- Provider: `mock`
- Task: 请为“群智引擎 SwarmOS”设计一个最小可行 demo。 要求： 1. 两周内可以做出来 2. 默认离线可跑 3. 能展示路由、专家协作、批判、聚合四个环节 4. 给出主要风险和下一步实验指标

## Routed Experts
- `planner` / Planner: score=0.630
- `research_scientist` / Research Scientist: score=0.710
- `coding_engineer` / Coding Engineer: score=0.590
- `product_strategist` / Product Strategist: score=0.450

## Expert Proposals
### Planner
- Role: Turns the task into a concrete execution plan.
- Confidence: 0.86
- Summary: 这个任务适合先做一个最小闭环：输入任务，路由到少量专家，生成多份提案，加入批判环节，再聚合输出。

Recommendations:
- 把流程固定为 路由 -> 提案 -> 批判 -> 聚合 -> 保存 trace。
- 限制首版专家数在 3 到 5 个，避免一开始就做复杂调度。
- 给 demo 设定明确成功标准，例如输出质量、可解释性和运行时长。
- 把 demo 范围收敛为 1 个核心场景和 2 到 3 个固定样例任务。

Risks:
- 如果 demo 目标太大，容易变成空泛展示而不是可运行原型。

### Research Scientist
- Role: Focuses on baselines, experiments, evaluation, and ablations.
- Confidence: 0.91
- Summary: 如果想判断 demo 有没有价值，必须同时保存基线、路由结果、协作收益和失败模式。 这个任务里，评测设计会直接决定 demo 的说服力。

Recommendations:
- 记录每次路由分数和被选中的专家，作为后续评测数据。
- 准备一个单模型直出基线，和协作流程做对比。
- 把失败案例也保存下来，方便观察协作在哪些任务上没有带来净收益。
- 给每个样例任务保存一份单模型直出结果，后续和协作结果并排对比。

Risks:
- 没有强基线会导致 demo 看起来聪明但无法证明收益。
- 只展示成功案例会掩盖失败边界。
- 没有失败样例时，很容易高估协作机制的真实收益。

### Coding Engineer
- Role: Focuses on implementation detail, interfaces, and MVP scope.
- Confidence: 0.84
- Summary: 最小工程实现应尽量少依赖，优先做一个单命令可运行的 CLI，并把 trace 和结果保存下来。

Recommendations:
- 用 Python 标准库实现 CLI，减少环境安装成本。
- 把专家配置和路由逻辑写成可扩展结构，而不是写死在主流程里。
- 为输出增加 markdown 报告，方便直接发给投资人或合伙人看。

Risks:
- 引入过多依赖会拖慢第一次跑通。
- 如果 CLI 输出不清晰，用户看不出协作带来的价值。

### Product Strategist
- Role: Focuses on user value, workflow fit, and commercial framing.
- Confidence: 0.78
- Summary: demo 不需要证明终极智能，只需要让人一眼看懂系统为什么比单模型流程更可控、更可解释。 当前目标应是让用户在 30 秒内看懂系统流程。

Recommendations:
- 首个 demo 选一个大家一看就懂的任务，例如 MVP 规划或代码审查。
- 输出中要显式展示每个专家贡献了什么，而不是只给最终答案。
- 强调这是系统组织能力 demo，不是假装已经拥有 10 万个真实专家。
- 准备一段 30 秒讲解话术，解释每个专家分别贡献了什么。

Risks:
- 如果任务场景不够具体，外部观众会觉得它只是概念片。
- 如果输出太技术化，外部观众会看不出为什么这比普通工作流更强。

## Critic Focus
- 必须加一个单模型直出基线，否则看不出协作收益。

## Critic Duplicate Signals
- 多个专家都在收敛到最小闭环，这说明首版应克制范围。

## Critic Next Checks
- 选 3 个代表性任务跑离线 demo，观察不同任务下的路由差异。
- 把最终结果和单模型直出结果并排保存，方便人工比较。
- 统计每次调用的专家数、总耗时和输出长度，形成最早一版成本画像。
- 让一个不了解代码的人直接阅读 markdown 输出，检查是否能快速看懂。

## Baseline (Single-Model)

- Summary: 这个任务需要做一个 demo，建议先确定核心场景，用最小范围实现一个可运行版本，然后给相关人展示收集反馈。
- Confidence: 0.60

Recommendations:
- 把目标拆分为可执行的步骤，优先完成核心部分。
- 先做最重要的部分，再逐步扩展到次要功能。

Risks:
- 范围失控可能导致项目延期。
- 缺少阶段性验收容易偏离目标。

## Baseline vs Multi-Expert Comparison

| Metric | Baseline | Multi-Expert |
|--------|----------|--------------|
| Recommendations | 2 | 15 |
| Risks identified | 2 | 8 |
| Confidence | 0.60 | 0.85 (avg) |
| Perspectives | 1 (generalist) | 4 (specialists) |

## Final Output
这个 demo 应该把目标收敛为一个能跑通的系统样机：用少量专家展示路由、协作、批判和聚合四个核心机制，并通过 trace 与基线对比证明它不仅仅是一个更花哨的工作流。 这次被路由到的专家是 Planner, Research Scientist, Coding Engineer, Product Strategist，足以体现角色分工。

Consensus:
- 先做离线可跑的最小闭环，而不是追求真实海量专家。
- 必须保留 trace，记录路由分数、专家输出、批判意见和最终结果。
- 首版 demo 要有明确基线，至少和单模型直出或单代理流程比较一次。
- 评测设计是 demo 说服力的一部分，不是可有可无的附加项。
- 结果展示要让用户一眼看出每个专家分别做了什么。

Next steps:
- 第 1 天到第 3 天：完成 CLI、专家注册表、路由和 mock provider。
- 第 4 天到第 6 天：加入批判器、聚合器和 markdown/JSON 输出。
- 第 7 天到第 10 天：挑选 3 个任务样例，做基线对比和人工点评。
- 第 11 天到第 14 天：如果条件允许，接入一个真实模型 provider 做第二轮验证。

Key risks:
- 如果路由太明显像关键词硬匹配，demo 会显得过于玩具化。
- 如果没有基线和失败案例，外部观众很难判断协作是否有价值。
- 如果展示任务过于抽象，用户会记不住系统真正解决了什么。
