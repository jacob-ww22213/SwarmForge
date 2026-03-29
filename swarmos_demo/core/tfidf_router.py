"""TF-IDF cosine similarity routing — pure stdlib, zero dependencies.

Strategy:
  1. Build a "document" per expert from their keywords + role + system_prompt.
  2. Pre-compute IDF across all expert documents.
  3. On each task, tokenize → TF-IDF vector → cosine similarity per expert.
  4. Return a float bonus for the router (scaled to TFIDF_MAX_BONUS).

Chinese text uses character bigrams; English uses lowercased word tokens.
"""
from __future__ import annotations

import math
import re
from typing import Any

from core.types import ExpertProfile, contains_cjk

_TFIDF_MAX_BONUS = 0.15


def _tokenize(text: str) -> list[str]:
    """Mixed CJK-bigram + English-word tokenizer."""
    tokens: list[str] = []
    buf_cjk: list[str] = []

    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            buf_cjk.append(ch)
        else:
            if buf_cjk:
                tokens.extend(_cjk_bigrams(buf_cjk))
                buf_cjk = []

    if buf_cjk:
        tokens.extend(_cjk_bigrams(buf_cjk))

    for word in re.findall(r"[a-zA-Z]{2,}", text.lower()):
        tokens.append(word)

    return tokens


def _cjk_bigrams(chars: list[str]) -> list[str]:
    if len(chars) == 1:
        return [chars[0]]
    return [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]


def _term_freq(tokens: list[str]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens) or 1
    return {t: c / total for t, c in counts.items()}


class TFIDFIndex:
    """Pre-built index over expert corpora."""

    def __init__(self, experts: list[ExpertProfile]) -> None:
        self._experts = experts
        self._docs: dict[str, dict[str, float]] = {}
        self._idf: dict[str, float] = {}
        self._build(experts)

    def _expert_text(self, expert: ExpertProfile) -> str:
        parts = [
            " ".join(expert.keywords),
            expert.role,
            expert.system_prompt,
            expert.name,
        ]
        return " ".join(parts)

    def _build(self, experts: list[ExpertProfile]) -> None:
        raw_docs: dict[str, list[str]] = {}
        for expert in experts:
            tokens = _tokenize(self._expert_text(expert))
            raw_docs[expert.key] = tokens
            self._docs[expert.key] = _term_freq(tokens)

        n = len(experts)
        df: dict[str, int] = {}
        for tokens in raw_docs.values():
            seen = set(tokens)
            for t in seen:
                df[t] = df.get(t, 0) + 1

        self._idf = {t: math.log((n + 1) / (d + 1)) + 1 for t, d in df.items()}

    def score(self, task: str) -> dict[str, float]:
        """Compute cosine similarity between task and each expert. Returns {key: 0..1}."""
        q_tokens = _tokenize(task)
        if not q_tokens:
            return {e.key: 0.0 for e in self._experts}

        q_tf = _term_freq(q_tokens)
        q_vec = {t: tf * self._idf.get(t, 1.0) for t, tf in q_tf.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        results: dict[str, float] = {}
        for expert in self._experts:
            d_tf = self._docs[expert.key]
            d_vec = {t: tf * self._idf.get(t, 1.0) for t, tf in d_tf.items()}
            d_norm = math.sqrt(sum(v * v for v in d_vec.values())) or 1.0

            dot = sum(q_vec.get(t, 0) * d_vec.get(t, 0) for t in set(q_vec) | set(d_vec))
            results[expert.key] = dot / (q_norm * d_norm)

        return results


_index: TFIDFIndex | None = None


def get_tfidf_index(experts: list[ExpertProfile]) -> TFIDFIndex:
    """Lazily build and cache the index. Rebuilds only if expert list changes."""
    global _index
    if _index is None or len(_index._experts) != len(experts):
        _index = TFIDFIndex(experts)
    return _index


def tfidf_bonus(experts: list[ExpertProfile], task: str, expert_key: str) -> float:
    """Return additive routing bonus based on TF-IDF similarity (0 .. TFIDF_MAX_BONUS)."""
    index = get_tfidf_index(experts)
    scores = index.score(task)
    raw = scores.get(expert_key, 0.0)
    return round(raw * _TFIDF_MAX_BONUS, 4)
