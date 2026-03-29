from __future__ import annotations

import argparse
import json
import os
import re
import textwrap
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from demo_types import ExpertProfile, ExpertProposal
from experts.aggregator import build_mock_aggregate
from experts.critic import build_mock_critique
from experts.registry import EXPERTS
from experts.strategies import build_mock_proposal
from reporting.console import render_console_report
from reporting.markdown import render_markdown_report


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def normalize_task(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def ensure_parent(path_text: str | None) -> None:
    if not path_text:
        return
    Path(path_text).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def analyze_task(task: str) -> dict[str, Any]:
    lowered = task.lower()
    profile = {
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

class ProviderError(RuntimeError):
    pass


class BaseProvider:
    mode = "base"

    def propose(self, expert: ExpertProfile, task: str, context: dict[str, Any]) -> ExpertProposal:
        raise NotImplementedError

    def critique(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    def aggregate(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError


class MockProvider(BaseProvider):
    mode = "mock"

    def propose(self, expert: ExpertProfile, task: str, context: dict[str, Any]) -> ExpertProposal:
        return build_mock_proposal(expert=expert, task=task, context=context)

    def critique(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return build_mock_critique(task=task, routed=routed, proposals=proposals, context=context)

    def aggregate(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return build_mock_aggregate(
            task=task,
            routed=routed,
            proposals=proposals,
            critique=critique,
            context=context,
        )


class OpenAICompatibleProvider(BaseProvider):
    mode = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(f"OpenAI-compatible request failed: {exc}") from exc

        try:
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Unexpected response payload: {body}") from exc

    def _prompt_for_expert(self, expert: ExpertProfile, task: str) -> tuple[str, str]:
        system_prompt = (
            "You are one expert inside a routed multi-agent system. "
            "Respond concisely. Output sections exactly as: "
            "SUMMARY:, RECOMMENDATIONS:, RISKS:, CONFIDENCE:."
        )
        user_prompt = textwrap.dedent(
            f"""
            Expert name: {expert.name}
            Expert role: {expert.role}
            Task: {task}

            Write 1 short summary sentence, 3 recommendation bullets, 1-2 risks, and a confidence score from 0 to 1.
            """
        ).strip()
        return system_prompt, user_prompt

    def _parse_structured_text(self, expert: ExpertProfile, score: float, text: str) -> ExpertProposal:
        summary = ""
        recommendations: list[str] = []
        risks: list[str] = []
        confidence = clamp(0.65 + score / 2.5, 0.50, 0.95)
        section = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            upper = line.upper()
            if upper.startswith("SUMMARY:"):
                section = "summary"
                summary = line.split(":", 1)[1].strip()
                continue
            if upper.startswith("RECOMMENDATIONS:"):
                section = "recommendations"
                continue
            if upper.startswith("RISKS:"):
                section = "risks"
                continue
            if upper.startswith("CONFIDENCE:"):
                section = "confidence"
                value_text = line.split(":", 1)[1].strip()
                try:
                    confidence = clamp(float(value_text), 0.0, 1.0)
                except ValueError:
                    pass
                continue
            if not line:
                continue
            if line.startswith("- "):
                item = line[2:].strip()
            else:
                item = line
            if section == "recommendations":
                recommendations.append(item)
            elif section == "risks":
                risks.append(item)
            elif section == "summary" and not summary:
                summary = item

        if not summary:
            summary = text.splitlines()[0].strip() if text.strip() else "No summary returned."
        if not recommendations:
            recommendations.append("No structured recommendations returned by the model.")
        return ExpertProposal(
            expert_key=expert.key,
            expert_name=expert.name,
            role=expert.role,
            score=round(score, 3),
            summary=summary,
            recommendations=recommendations,
            risks=risks or ["No explicit risks returned by the model."],
            confidence=round(confidence, 2),
        )

    def propose(self, expert: ExpertProfile, task: str, context: dict[str, Any]) -> ExpertProposal:
        system_prompt, user_prompt = self._prompt_for_expert(expert, task)
        text = self._chat(system_prompt, user_prompt)
        return self._parse_structured_text(expert, context["scores"][expert.key], text)

    def critique(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        joined = "\n".join(
            f"{proposal.expert_name}: {proposal.summary}\n"
            + "\n".join(f"- {item}" for item in proposal.recommendations)
            for proposal in proposals
        )
        system_prompt = (
            "You are the critic in a multi-agent system. "
            "Return sections exactly as FOCUS:, DUPLICATES:, NEXT_CHECKS: with bullet lists."
        )
        user_prompt = f"Task: {task}\n\nProposals:\n{joined}"
        text = self._chat(system_prompt, user_prompt)
        sections = {"focus": [], "duplicates": [], "next_checks": []}
        current = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            upper = line.upper()
            if upper.startswith("FOCUS:"):
                current = "focus"
                continue
            if upper.startswith("DUPLICATES:"):
                current = "duplicates"
                continue
            if upper.startswith("NEXT_CHECKS:"):
                current = "next_checks"
                continue
            if not line:
                continue
            item = line[2:].strip() if line.startswith("- ") else line
            if current:
                sections[current].append(item)
        if not sections["focus"]:
            sections["focus"].append("Critic did not return structured feedback.")
        return sections

    def aggregate(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        joined = "\n".join(
            f"{proposal.expert_name}: {proposal.summary}\n"
            + "\n".join(f"- {item}" for item in proposal.recommendations)
            for proposal in proposals
        )
        system_prompt = (
            "You are the final aggregator in a multi-agent system. "
            "Return sections exactly as FINAL_SUMMARY:, CONSENSUS:, NEXT_STEPS:, KEY_RISKS:."
        )
        user_prompt = (
            f"Task: {task}\n\nProposals:\n{joined}\n\nCritique:\n"
            + "\n".join(f"- {item}" for item in critique.get("focus", []))
        )
        text = self._chat(system_prompt, user_prompt)
        sections = {
            "selected_experts": [proposal.expert_name for proposal in proposals],
            "consensus": [],
            "critique_focus": critique.get("focus", []),
            "next_steps": [],
            "key_risks": [],
            "final_summary": "",
        }
        current = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            upper = line.upper()
            if upper.startswith("FINAL_SUMMARY:"):
                current = "final_summary"
                sections["final_summary"] = line.split(":", 1)[1].strip()
                continue
            if upper.startswith("CONSENSUS:"):
                current = "consensus"
                continue
            if upper.startswith("NEXT_STEPS:"):
                current = "next_steps"
                continue
            if upper.startswith("KEY_RISKS:"):
                current = "key_risks"
                continue
            if not line:
                continue
            item = line[2:].strip() if line.startswith("- ") else line
            if current == "final_summary" and not sections["final_summary"]:
                sections["final_summary"] = item
            elif current in {"consensus", "next_steps", "key_risks"}:
                sections[current].append(item)
        if not sections["final_summary"]:
            sections["final_summary"] = "Aggregator did not return a structured summary."
        return sections


class OllamaProvider(OpenAICompatibleProvider):
    mode = "ollama"

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434/v1") -> None:
        super().__init__(base_url=base_url, api_key="ollama", model=model)


def build_provider(args: argparse.Namespace) -> BaseProvider:
    if args.provider == "mock":
        return MockProvider()
    if args.provider == "openai-compatible":
        base_url = args.base_url or os.getenv("SWARMOS_BASE_URL")
        api_key = args.api_key or os.getenv("SWARMOS_API_KEY")
        model = args.model or os.getenv("SWARMOS_MODEL")
        if not all([base_url, api_key, model]):
            raise ProviderError(
                "openai-compatible mode requires --base-url/--api-key/--model or SWARMOS_BASE_URL/SWARMOS_API_KEY/SWARMOS_MODEL."
            )
        return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
    if args.provider == "ollama":
        model = args.model or "qwen2.5:7b"
        base_url = args.base_url or "http://127.0.0.1:11434/v1"
        return OllamaProvider(model=model, base_url=base_url)
    raise ProviderError(f"Unsupported provider: {args.provider}")


def score_expert(expert: ExpertProfile, task: str, profile: dict[str, Any]) -> float:
    score = 0.05 + expert.bias
    lowered = task.lower()
    for keyword in expert.keywords:
        if keyword.lower() in lowered or keyword in task:
            score += 0.14
    if expert.key == "systems_architect" and "systems" in profile["domains"]:
        score += 0.22
    if expert.key == "coding_engineer" and ("code" in profile["domains"] or profile["mentions_demo"]):
        score += 0.20
    if expert.key == "research_scientist" and "research" in profile["domains"]:
        score += 0.20
    if expert.key == "product_strategist" and ("business" in profile["domains"] or profile["mentions_demo"]):
        score += 0.14
    if expert.key == "math_optimizer" and ("math" in profile["domains"] or "evaluate" in profile["actions"]):
        score += 0.12
    if expert.key == "legal_risk" and "legal" in profile["domains"]:
        score += 0.28
    if expert.key == "medical_safety" and "medical" in profile["domains"]:
        score += 0.28
    if expert.key == "planner":
        score += 0.18
    return round(clamp(score, 0.0, 1.0), 3)


def route_experts(task: str, profile: dict[str, Any], top_k: int) -> tuple[list[tuple[ExpertProfile, float]], dict[str, float]]:
    score_map: dict[str, float] = {}
    for expert in EXPERTS:
        score_map[expert.key] = score_expert(expert, task, profile)

    always_include = {"planner"}
    optional = []
    for expert in EXPERTS:
        if expert.key in always_include:
            continue
        optional.append((expert, score_map[expert.key]))
    optional.sort(key=lambda item: item[1], reverse=True)
    selected = [(expert, score_map[expert.key]) for expert in EXPERTS if expert.key in always_include]
    selected.extend(optional[:top_k])
    return selected, score_map

def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    if args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")
    else:
        task = args.task
    if not task:
        raise ValueError("Provide --task or --task-file.")

    task = normalize_task(task)
    profile = analyze_task(task)
    routed, scores = route_experts(task=task, profile=profile, top_k=args.top_k)
    context = {"profile": profile, "scores": scores}
    provider = build_provider(args)

    with ThreadPoolExecutor(max_workers=len(routed)) as executor:
        futures = [executor.submit(provider.propose, expert, task, context) for expert, _ in routed]
        proposals = [future.result() for future in futures]

    order = {expert.key: index for index, (expert, _) in enumerate(routed)}
    proposals.sort(key=lambda proposal: order[proposal.expert_key])

    critique = provider.critique(task=task, routed=routed, proposals=proposals, context=context)
    aggregate = provider.aggregate(
        task=task,
        routed=routed,
        proposals=proposals,
        critique=critique,
        context=context,
    )
    console_report = render_console_report(task, routed, proposals, critique, aggregate)
    markdown_report = render_markdown_report(task, provider.mode, routed, proposals, critique, aggregate)
    trace = {
        "task": task,
        "provider": provider.mode,
        "profile": profile,
        "routed": [{"key": expert.key, "name": expert.name, "score": score} for expert, score in routed],
        "proposals": [asdict(proposal) for proposal in proposals],
        "critique": critique,
        "aggregate": aggregate,
    }
    return {
        "task": task,
        "provider": provider,
        "console_report": console_report,
        "markdown_report": markdown_report,
        "trace": trace,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SwarmOS routed multi-expert demo.")
    parser.add_argument("--task", help="Inline task text.")
    parser.add_argument("--task-file", help="Path to a UTF-8 text file with the task.")
    parser.add_argument(
        "--provider",
        choices=("mock", "openai-compatible", "ollama"),
        default="mock",
        help="Inference backend. Default is offline mock.",
    )
    parser.add_argument("--base-url", help="Base URL for openai-compatible or ollama providers.")
    parser.add_argument("--api-key", help="API key for openai-compatible provider.")
    parser.add_argument("--model", help="Model name for real providers.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of non-planner experts to route to.")
    parser.add_argument("--save-markdown", help="Write the markdown report to this path.")
    parser.add_argument("--save-json", help="Write the JSON trace to this path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_demo(args)
    except (ValueError, ProviderError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(result["console_report"])

    if args.save_markdown:
        ensure_parent(args.save_markdown)
        Path(args.save_markdown).write_text(result["markdown_report"], encoding="utf-8")
        print(f"\nSaved markdown report to {Path(args.save_markdown).resolve()}")

    if args.save_json:
        ensure_parent(args.save_json)
        Path(args.save_json).write_text(
            json.dumps(result["trace"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved JSON trace to {Path(args.save_json).resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
