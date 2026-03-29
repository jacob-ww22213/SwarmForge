from __future__ import annotations

from core.types import TaskProfile, contains_cjk


def analyze_task(task: str) -> TaskProfile:
    lowered = task.lower()
    profile: TaskProfile = {
        "language": "zh" if contains_cjk(task) else "en",
        "domains": [],
        "actions": [],
        "risk_level": "medium",
        "mentions_demo": any(word in task for word in ("demo", "演示", "原型", "mvp")),
    }

    domain_rules = {
        "code": ("code", "代码", "bug", "debug", "review", "审查", "测试", "工程"),
        "math": ("math", "数学", "优化", "证明", "概率", "loss", "metric"),
        "legal": ("legal", "法律", "合同", "合规", "监管", "法务"),
        "medical": ("medical", "医疗", "医学", "诊断", "药物", "病人", "患者"),
        "research": ("research", "研究", "实验", "benchmark", "评测", "论文"),
        "business": ("商业", "投资", "融资", "市场", "客户", "定价", "roi"),
        "systems": ("架构", "系统", "infra", "部署", "分布式", "router", "routing"),
    }
    action_rules = {
        "design": ("设计", "design", "架构", "方案"),
        "build": ("实现", "build", "开发", "编码", "搭建"),
        "evaluate": ("评估", "evaluate", "实验", "测试", "验证", "指标"),
        "sell": ("路演", "pitch", "融资", "投资人", "商业化"),
        "risk": ("风险", "合规", "安全", "审计", "隐私"),
    }

    for domain, keywords in domain_rules.items():
        if any(keyword in lowered or keyword in task for keyword in keywords):
            profile["domains"].append(domain)

    for action, keywords in action_rules.items():
        if any(keyword in lowered or keyword in task for keyword in keywords):
            profile["actions"].append(action)

    if "medical" in profile["domains"] or "legal" in profile["domains"]:
        profile["risk_level"] = "high"
    elif "business" in profile["domains"] and "systems" not in profile["domains"]:
        profile["risk_level"] = "medium"
    else:
        profile["risk_level"] = "low" if profile["mentions_demo"] else "medium"

    if not profile["domains"]:
        profile["domains"] = ["systems", "research"]
    if not profile["actions"]:
        profile["actions"] = ["design"]
    return profile
