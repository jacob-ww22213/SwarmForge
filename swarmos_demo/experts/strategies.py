from __future__ import annotations

from typing import Any

from core.types import ExpertProfile, ExpertProposal, clamp


BASE_SUMMARIES = {
    "planner": "这个任务适合先做一个最小闭环：输入任务，路由到少量专家，生成多份提案，加入批判环节，再聚合输出。",
    "systems_architect": "MVP 应该优先验证系统组织能力，而不是追求大量真实模型。重点是路由、协作协议、日志和可观测性。",
    "coding_engineer": "最小工程实现应尽量少依赖，优先做一个单命令可运行的 CLI，并把 trace 和结果保存下来。",
    "research_scientist": "如果想判断 demo 有没有价值，必须同时保存基线、路由结果、协作收益和失败模式。",
    "product_strategist": "demo 不需要证明终极智能，只需要让人一眼看懂系统为什么比单模型流程更可控、更可解释。",
    "math_optimizer": "先用简单打分规则控制专家数量和协作轮数，否则通信成本会在 demo 阶段就吞掉全部收益。",
    "legal_risk": "如果任务涉及合规或企业数据，demo 也要留下审计链和责任边界，避免把系统包装成无条件正确。",
    "medical_safety": "涉及医疗场景时，demo 只能作为辅助分析和风险提示，不应生成未经验证的诊疗建议。",
}

BASE_RECOMMENDATIONS = {
    "planner": [
        "把流程固定为 路由 -> 提案 -> 批判 -> 聚合 -> 保存 trace。",
        "限制首版专家数在 3 到 5 个，避免一开始就做复杂调度。",
        "给 demo 设定明确成功标准，例如输出质量、可解释性和运行时长。",
    ],
    "systems_architect": [
        "默认离线 mock 模式，确保任何机器上都能演示流程。",
        "预留 provider 抽象，后续可替换为 openai-compatible 或 Ollama。",
        "输出 JSON trace，方便回放和后续做路由评测。",
    ],
    "coding_engineer": [
        "用 Python 标准库实现 CLI，减少环境安装成本。",
        "把专家配置和路由逻辑写成可扩展结构，而不是写死在主流程里。",
        "为输出增加 markdown 报告，方便直接发给投资人或合伙人看。",
    ],
    "research_scientist": [
        "记录每次路由分数和被选中的专家，作为后续评测数据。",
        "准备一个单模型直出基线，和协作流程做对比。",
        "把失败案例也保存下来，方便观察协作在哪些任务上没有带来净收益。",
    ],
    "product_strategist": [
        "首个 demo 选一个大家一看就懂的任务，例如 MVP 规划或代码审查。",
        "输出中要显式展示每个专家贡献了什么，而不是只给最终答案。",
        "强调这是系统组织能力 demo，不是假装已经拥有 10 万个真实专家。",
    ],
    "math_optimizer": [
        "首版只激活 top-k 专家，建议 k=3。",
        "把最终评价聚焦在质量提升 / 额外成本，而不是单一准确率。",
        "为后续版本准备一个简单信誉分机制，逐步替换手工规则路由。",
    ],
    "legal_risk": [
        "对外口径中区分 概念验证、内部使用、生产可用 三个阶段。",
        "保存输入、路由、输出和风险提示，方便审计。",
        "避免在无验证情况下把结论描述为确定事实。",
    ],
    "medical_safety": [
        "若进入医疗场景，只做辅助、检索、总结或提醒。",
        "在输出中加入明确安全边界和人工复核建议。",
        "把高风险建议默认升级为需人工确认。",
    ],
}

BASE_RISKS = {
    "planner": [
        "如果 demo 目标太大，容易变成空泛展示而不是可运行原型。",
    ],
    "systems_architect": [
        "路由逻辑过弱时，系统看起来像硬编码流程。",
        "日志和 trace 缺失会让后续迭代失去依据。",
    ],
    "coding_engineer": [
        "引入过多依赖会拖慢第一次跑通。",
        "如果 CLI 输出不清晰，用户看不出协作带来的价值。",
    ],
    "research_scientist": [
        "没有强基线会导致 demo 看起来聪明但无法证明收益。",
        "只展示成功案例会掩盖失败边界。",
    ],
    "product_strategist": [
        "如果任务场景不够具体，外部观众会觉得它只是概念片。",
    ],
    "math_optimizer": [
        "专家数增加太快会让成本和延迟恶化。",
    ],
    "legal_risk": [
        "涉及企业场景时，合规表述不严谨会影响可信度。",
    ],
    "medical_safety": [
        "高风险行业如果没有安全边界，demo 可能被误用。",
    ],
}


def append_unique(items: list[str], new_items: list[str]) -> list[str]:
    seen = set(items)
    for item in new_items:
        if item not in seen:
            items.append(item)
            seen.add(item)
    return items


def _summary_suffixes(expert: ExpertProfile, profile: dict[str, Any], actions: list[str], top_focus: str) -> list[str]:
    suffixes: list[str] = []
    domains = profile["domains"]

    if expert.key in {"systems_architect", "research_scientist"} and "research" in domains:
        suffixes.append("这个任务里，评测设计会直接决定 demo 的说服力。")
    if expert.key == "product_strategist" and profile["mentions_demo"]:
        suffixes.append("当前目标应是让用户在 30 秒内看懂系统流程。")
    if expert.key == "coding_engineer" and "build" in actions:
        suffixes.append("既然任务明确要求可运行，工程可执行性比术语完整性更重要。")
    if expert.key == "systems_architect" and "systems" in domains:
        suffixes.append(f"当前优先主题是 {top_focus}，所以接口稳定性和日志可见性应优先于功能堆叠。")
    if expert.key == "legal_risk" and profile["risk_level"] == "high":
        suffixes.append("这类任务如果没有责任边界和人工复核，demo 很容易被误解为自动决策系统。")
    if expert.key == "medical_safety" and "medical" in domains:
        suffixes.append("任何涉及诊疗含义的结论都必须保持保守，并明确标注为辅助意见。")
    return suffixes


def _context_recommendations(expert: ExpertProfile, profile: dict[str, Any], actions: list[str], task: str) -> list[str]:
    domains = profile["domains"]
    additions: list[str] = []

    if expert.key == "planner" and profile["mentions_demo"]:
        additions.append("把 demo 范围收敛为 1 个核心场景和 2 到 3 个固定样例任务。")
    if expert.key == "systems_architect" and "systems" in domains:
        additions.append("把 provider 模式、路由分数和执行链路全部写入 trace，方便联调。")
    if expert.key == "coding_engineer" and ("code" in domains or "build" in actions):
        additions.append("增加一个 smoke test 命令，保证每次改动后都能快速验证主流程。")
    if expert.key == "research_scientist" and ("evaluate" in actions or "research" in domains):
        additions.append("给每个样例任务保存一份单模型直出结果，后续和协作结果并排对比。")
    if expert.key == "product_strategist" and profile["mentions_demo"]:
        additions.append("准备一段 30 秒讲解话术，解释每个专家分别贡献了什么。")
    if expert.key == "math_optimizer":
        additions.append("记录 top-k、输出长度和总耗时，形成最早一版成本画像。")
    if expert.key == "legal_risk" and "legal" in domains:
        additions.append("把输出中的结论和风险提示分开显示，避免把建议写成最终判断。")
    if expert.key == "medical_safety" and "medical" in domains:
        additions.append("把涉及医疗的建议统一降级为需人工确认。")
    if "代码审查" in task or "code review" in task.lower():
        additions.append("为代码类任务准备一个固定格式输出，方便后续接 CI 或 PR 流程。")
    return additions


def _context_risks(expert: ExpertProfile, profile: dict[str, Any], actions: list[str]) -> list[str]:
    domains = profile["domains"]
    additions: list[str] = []

    if expert.key == "systems_architect" and "systems" in domains:
        additions.append("如果模块边界不先冻结，双人开发时很容易在主流程层互相打架。")
    if expert.key == "coding_engineer" and "build" in actions:
        additions.append("如果一边重构一边改输出协议，联调阶段会非常痛苦。")
    if expert.key == "research_scientist" and ("research" in domains or "evaluate" in actions):
        additions.append("没有失败样例时，很容易高估协作机制的真实收益。")
    if expert.key == "product_strategist" and profile["mentions_demo"]:
        additions.append("如果输出太技术化，外部观众会看不出为什么这比普通工作流更强。")
    if expert.key == "math_optimizer":
        additions.append("如果只看结果质量，不看专家数和延迟，成本问题会被掩盖。")
    if profile["risk_level"] == "high" and expert.key not in {"legal_risk", "medical_safety"}:
        additions.append("高风险场景没有显式安全边界时，系统可信度会显著下降。")
    return additions


def build_mock_proposal(expert: ExpertProfile, task: str, context: dict[str, Any]) -> ExpertProposal:
    profile = context["profile"]
    score = context["scores"][expert.key]
    actions = profile["actions"]
    top_focus = ", ".join(profile["domains"][:2])

    summary = BASE_SUMMARIES[expert.key]
    suffixes = _summary_suffixes(expert, profile, actions, top_focus)
    if suffixes:
        summary = f"{summary} {' '.join(suffixes)}"

    recommendations = append_unique(
        list(BASE_RECOMMENDATIONS[expert.key]),
        _context_recommendations(expert, profile, actions, task),
    )
    risks = append_unique(
        list(BASE_RISKS[expert.key]),
        _context_risks(expert, profile, actions),
    )
    confidence = clamp(0.55 + score / 2.0, 0.55, 0.92)

    return ExpertProposal(
        expert_key=expert.key,
        expert_name=expert.name,
        role=expert.role,
        score=round(score, 3),
        summary=summary,
        recommendations=recommendations,
        risks=risks,
        confidence=round(confidence, 2),
    )
