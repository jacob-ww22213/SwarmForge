from __future__ import annotations

from demo_types import ExpertProfile


EXPERTS = [
    ExpertProfile(
        key="planner",
        name="Planner",
        role="Turns the task into a concrete execution plan.",
        keywords=("plan", "规划", "步骤", "timeline", "milestone", "mvp"),
        bias=0.40,
    ),
    ExpertProfile(
        key="systems_architect",
        name="Systems Architect",
        role="Focuses on routing, orchestration, deployment, and observability.",
        keywords=("架构", "系统", "infra", "部署", "分布式", "router", "routing", "latency"),
        bias=0.25,
    ),
    ExpertProfile(
        key="coding_engineer",
        name="Coding Engineer",
        role="Focuses on implementation detail, interfaces, and MVP scope.",
        keywords=("代码", "code", "开发", "build", "接口", "cli", "api", "demo"),
        bias=0.20,
    ),
    ExpertProfile(
        key="research_scientist",
        name="Research Scientist",
        role="Focuses on baselines, experiments, evaluation, and ablations.",
        keywords=("研究", "实验", "评测", "benchmark", "ablation", "验证", "指标"),
        bias=0.18,
    ),
    ExpertProfile(
        key="product_strategist",
        name="Product Strategist",
        role="Focuses on user value, workflow fit, and commercial framing.",
        keywords=("客户", "市场", "投资", "demo", "场景", "产品", "roi", "商业"),
        bias=0.12,
    ),
    ExpertProfile(
        key="math_optimizer",
        name="Math Optimizer",
        role="Focuses on scoring, budget, and optimization tradeoffs.",
        keywords=("优化", "数学", "metric", "budget", "成本", "概率", "score"),
        bias=0.10,
    ),
    ExpertProfile(
        key="legal_risk",
        name="Legal Risk",
        role="Focuses on compliance, auditability, and legal exposure.",
        keywords=("法律", "合同", "合规", "监管", "审计", "隐私"),
        bias=0.08,
    ),
    ExpertProfile(
        key="medical_safety",
        name="Medical Safety",
        role="Focuses on safety boundaries in health-related tasks.",
        keywords=("医疗", "医学", "诊断", "病人", "患者", "药物"),
        bias=0.08,
    ),
]
