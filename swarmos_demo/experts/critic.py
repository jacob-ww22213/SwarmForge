from __future__ import annotations

from typing import Any

from demo_types import ExpertProfile, ExpertProposal


def build_mock_critique(
    task: str,
    routed: list[tuple[ExpertProfile, float]],
    proposals: list[ExpertProposal],
    context: dict[str, Any],
) -> dict[str, Any]:
    del task
    del routed

    profile = context["profile"]
    expert_keys = {proposal.expert_key for proposal in proposals}
    focus: list[str] = []

    if "research_scientist" in expert_keys:
        focus.append("必须加一个单模型直出基线，否则看不出协作收益。")
    if profile["mentions_demo"] and "product_strategist" not in expert_keys:
        focus.append("缺少对 demo 受众和展示路径的定义，容易看起来像内部工具。")
    if "systems" in profile["domains"] and "systems_architect" not in expert_keys:
        focus.append("缺少系统观测与日志层，后续很难定位路由是否有效。")
    if "build" in profile["actions"] and "coding_engineer" not in expert_keys:
        focus.append("当前任务包含实现要求，但没有实现视角专家，落地路径会偏空。")
    if profile["risk_level"] == "high":
        focus.append("高风险场景必须加入明确的人工复核与责任边界。")
    if not focus:
        focus.append("当前方案结构完整，但需要用实际样例验证输出是否足够有说服力。")

    flattened_recommendations = [
        item
        for proposal in proposals
        for item in proposal.recommendations
    ]
    duplicates: list[str] = []
    if sum("trace" in item.lower() for item in flattened_recommendations) >= 2:
        duplicates.append("多个专家都在强调 trace，这说明 trace 是 demo 必须保留的能力。")
    if sum(("基线" in item) or ("baseline" in item.lower()) for item in flattened_recommendations) >= 2:
        duplicates.append("多个专家都要求加入基线对比，说明 demo 不应只展示单次成功输出。")
    if not duplicates:
        duplicates.append("多个专家都在收敛到最小闭环，这说明首版应克制范围。")

    next_checks = [
        "选 3 个代表性任务跑离线 demo，观察不同任务下的路由差异。",
        "把最终结果和单模型直出结果并排保存，方便人工比较。",
        "统计每次调用的专家数、总耗时和输出长度，形成最早一版成本画像。",
    ]
    if profile["mentions_demo"]:
        next_checks.append("让一个不了解代码的人直接阅读 markdown 输出，检查是否能快速看懂。")
    if "code" in profile["domains"]:
        next_checks.append("增加一个代码审查类样例任务，验证输出是否足够结构化。")
    if profile["risk_level"] == "high":
        next_checks.append("高风险样例必须验证输出中是否带有明确的人工复核提醒。")

    return {
        "focus": focus,
        "duplicates": duplicates,
        "next_checks": next_checks,
    }
