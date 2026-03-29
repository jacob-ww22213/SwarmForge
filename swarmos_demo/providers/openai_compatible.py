from __future__ import annotations

import json
import logging
import textwrap
import time
import urllib.error
import urllib.request
from http.client import RemoteDisconnected
from typing import Any

from core.types import ExpertProfile, ExpertProposal, clamp
from providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.0
_REQUEST_TIMEOUT_S = 60


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
            f"You are {expert.name}, {expert.role}"
        )
        system_prompt = (
            f"{base}\n"
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
        text, usage = self._chat(
            system_prompt,
            user_prompt,
            temperature=expert.temperature,
            max_tokens=expert.max_tokens,
        )
        context.setdefault("_usage", {})[expert.key] = usage
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

    def baseline(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
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
