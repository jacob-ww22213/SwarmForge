from __future__ import annotations

from typing import Any

from core.types import ExpertProfile, ExpertProposal


def build_mock_aggregate(
    task: str,
    routed: list[tuple[ExpertProfile, float]],
    proposals: list[ExpertProposal],
    critique: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    del routed

    profile = context["profile"]
    selected_names = [proposal.expert_name for proposal in proposals]
    expert_keys = {proposal.expert_key for proposal in proposals}
    consensus = [
        "先做离线可跑的最小闭环，而不是追求真实海量专家。",
        "必须保留 trace，记录路由分数、专家输出、批判意见和最终结果。",
        "首版 demo 要有明确基线，至少和单模型直出或单代理流程比较一次。",
    ]
    if "research_scientist" in expert_keys:
        consensus.append("评测设计是 demo 说服力的一部分，不是可有可无的附加项。")
    if profile["mentions_demo"]:
        consensus.append("结果展示要让用户一眼看出每个专家分别做了什么。")
    if "systems_architect" in expert_keys:
        consensus.append("接口和输出结构应先稳定，再继续增加 provider 或更多专家。")

    next_steps = [
        "第 1 天到第 3 天：完成 CLI、专家注册表、路由和 mock provider。",
        "第 4 天到第 6 天：加入批判器、聚合器和 markdown/JSON 输出。",
        "第 7 天到第 10 天：挑选 3 个任务样例，做基线对比和人工点评。",
        "第 11 天到第 14 天：如果条件允许，接入一个真实模型 provider 做第二轮验证。",
    ]
    if "code" in profile["domains"]:
        next_steps.append("补一个代码审查样例，让输出更接近真实工程任务。")
    if "business" in profile["domains"]:
        next_steps.append("补一版面向投资人或合伙人的简洁展示报告。")

    key_risks = [
        "如果路由太明显像关键词硬匹配，demo 会显得过于玩具化。",
        "如果没有基线和失败案例，外部观众很难判断协作是否有价值。",
        "如果展示任务过于抽象，用户会记不住系统真正解决了什么。",
    ]
    if profile["risk_level"] == "high":
        key_risks.append("高风险场景必须增加人工复核和边界声明。")
    if "code" in profile["domains"]:
        key_risks.append("如果输出不够结构化，后续很难接入真实工程流程或 CI。")

    final_summary = (
        "这个 demo 应该把目标收敛为一个能跑通的系统样机："
        "用少量专家展示路由、协作、批判和聚合四个核心机制，"
        "并通过 trace 与基线对比证明它不仅仅是一个更花哨的工作流。"
    )
    if "code" in profile["domains"]:
        final_summary += " 当前任务带有工程属性，因此展示结果时最好同时给出结构化建议和下一步实现动作。"
    if profile["mentions_demo"]:
        final_summary += f" 这次被路由到的专家是 {', '.join(selected_names)}，足以体现角色分工。"
    if "路演" in task or "投资" in task:
        final_summary += " 如果用于对外展示，要补一层更商业化的语言包装。"

    return {
        "selected_experts": selected_names,
        "consensus": consensus,
        "critique_focus": critique["focus"],
        "next_steps": next_steps,
        "key_risks": key_risks,
        "final_summary": final_summary,
    }
