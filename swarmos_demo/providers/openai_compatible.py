from __future__ import annotations

import json
import logging
import textwrap
import time
import urllib.error
import urllib.request
from http.client import RemoteDisconnected
from typing import Any

from core.types import (
    AggregateResult,
    BaselineResult,
    CritiqueReport,
    ExpertProfile,
    ExpertProposal,
    clamp,
)
from providers.base import BaseProvider, ProviderError

from core.config import (
    PROVIDER_BASE_BACKOFF_S as _BASE_BACKOFF_S,
    PROVIDER_MAX_RETRIES as _MAX_RETRIES,
    PROVIDER_REQUEST_TIMEOUT_S as _REQUEST_TIMEOUT_S,
)

logger = logging.getLogger(__name__)


def _is_retryable(exc: Exception) -> bool:
    """Decide if an HTTP error warrants a retry (429, 5xx, transient)."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 429 or exc.code >= 500
    if isinstance(exc, (urllib.error.URLError, RemoteDisconnected, TimeoutError, ConnectionError)):
        return True
    return False


class OpenAICompatibleProvider(BaseProvider):
    mode = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> tuple[str, dict[str, int]]:
        """Returns (content, usage_dict). usage_dict may be empty if provider omits it."""
        endpoint = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
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
                with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_S) as response:
                    body = json.loads(response.read().decode("utf-8"))
                try:
                    content = body["choices"][0]["message"]["content"].strip()
                    usage = body.get("usage", {})
                    return content, usage
                except (KeyError, IndexError, TypeError) as exc:
                    raise ProviderError(f"Unexpected response payload: {body}") from exc
            except ProviderError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1 and _is_retryable(exc):
                    wait = _BASE_BACKOFF_S * (2 ** attempt)
                    logger.warning(
                        "Retry %d/%d after %.1fs (%s)", attempt + 1, _MAX_RETRIES, wait, exc
                    )
                    time.sleep(wait)
                    continue
                break

        raise ProviderError(
            f"OpenAI-compatible request failed after {_MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    def _prompt_for_expert(self, expert: ExpertProfile, task: str) -> tuple[str, str]:
        base = expert.system_prompt or (
            f"你是 {expert.name}，角色是 {expert.role}"
        )
        system_prompt = (
            f"{base}\n"
            "你是一个路由式多智能体系统中的专家节点。"
            "除非必须保留代码、库名、接口名或英文专有名词，否则请全部使用简体中文回答。"
            "请严格按以下标题输出：SUMMARY:、RECOMMENDATIONS:、RISKS:、CONFIDENCE:。"
        )
        user_prompt = textwrap.dedent(
            f"""
            专家名称：{expert.name}
            专家角色：{expert.role}
            任务：{task}

            请输出：
            1. 一句简短总结
            2. 3 条建议
            3. 1 到 2 条风险
            4. 一个 0 到 1 之间的置信度

            如果任务是代码评审，请优先指出明确 bug、边界条件问题、测试建议和修复方向。
            你的内容必须使用简体中文。
            """
        ).strip()
        return system_prompt, user_prompt

    def _parse_structured_text(self, expert: ExpertProfile, score: float, text: str) -> ExpertProposal:
        def _split_value(raw: str) -> str:
            return raw.replace("：", ":", 1).split(":", 1)[1].strip()

        summary = ""
        recommendations: list[str] = []
        risks: list[str] = []
        confidence = clamp(0.65 + score / 2.5, 0.50, 0.95)
        section = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            upper = line.upper()
            if upper.startswith("SUMMARY:") or upper.startswith("摘要:") or upper.startswith("摘要："):
                section = "summary"
                summary = _split_value(line)
                continue
            if upper.startswith("RECOMMENDATIONS:") or upper.startswith("建议:") or upper.startswith("建议："):
                section = "recommendations"
                continue
            if upper.startswith("RISKS:") or upper.startswith("风险:") or upper.startswith("风险："):
                section = "risks"
                continue
            if upper.startswith("CONFIDENCE:") or upper.startswith("置信度:") or upper.startswith("置信度："):
                section = "confidence"
                value_text = _split_value(line)
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
            summary = text.splitlines()[0].strip() if text.strip() else "模型没有返回有效总结。"
        if not recommendations:
            recommendations.append("模型没有按要求返回结构化建议。")
        return ExpertProposal(
            expert_key=expert.key,
            expert_name=expert.name,
            role=expert.role,
            score=round(score, 3),
            summary=summary,
            recommendations=recommendations,
            risks=risks or ["模型没有明确给出风险项。"],
            confidence=round(confidence, 2),
        )

    def propose(self, expert: ExpertProfile, task: str, context: dict[str, Any]) -> ExpertProposal:
        system_prompt, user_prompt = self._prompt_for_expert(expert, task)
        text, usage = self._chat(
            system_prompt,
            user_prompt,
            temperature=expert.temperature,
            max_tokens=expert.max_tokens,
        )
        proposal = self._parse_structured_text(expert, context["scores"][expert.key], text)
        proposal._usage = usage  # type: ignore[attr-defined]
        return proposal

    def critique(
        self,
        task: str,
        routed: list[tuple[ExpertProfile, float]],
        proposals: list[ExpertProposal],
        context: dict[str, Any],
    ) -> CritiqueReport:
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
        text, _ = self._chat(system_prompt, user_prompt)
        sections: dict[str, Any] = {"focus": [], "duplicates": [], "next_checks": []}
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
        critique: CritiqueReport,
        context: dict[str, Any],
    ) -> AggregateResult:
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
        text, _ = self._chat(system_prompt, user_prompt)
        sections: dict[str, Any] = {
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

    def baseline(self, task: str, context: dict[str, Any]) -> BaselineResult:
        system_prompt = (
            "You are a single generalist assistant. Respond concisely. "
            "Output sections exactly as: SUMMARY:, RECOMMENDATIONS:, RISKS:, CONFIDENCE:."
        )
        user_prompt = (
            f"Task: {task}\n\n"
            "Provide a brief analysis: 1 summary sentence, 2-3 recommendations, "
            "1-2 risks, and a confidence score from 0 to 1."
        )
        text, _ = self._chat(system_prompt, user_prompt)

        summary = ""
        recommendations: list[str] = []
        risks: list[str] = []
        confidence = 0.60
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
                try:
                    confidence = clamp(float(line.split(":", 1)[1].strip()), 0.0, 1.0)
                except ValueError:
                    pass
                section = None
                continue
            if not line:
                continue
            item = line[2:].strip() if line.startswith("- ") else line
            if section == "recommendations":
                recommendations.append(item)
            elif section == "risks":
                risks.append(item)
            elif section == "summary" and not summary:
                summary = item

        return {
            "summary": summary or "No baseline summary returned.",
            "recommendations": recommendations or ["No baseline recommendations returned."],
            "risks": risks or ["No baseline risks returned."],
            "confidence": round(confidence, 2),
        }
