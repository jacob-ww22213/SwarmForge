from __future__ import annotations

import argparse
import os

from providers.base import BaseProvider, ProviderError
from providers.mock import MockProvider
from providers.openai_compatible import OpenAICompatibleProvider
from providers.ollama import OllamaProvider

__all__ = [
    "BaseProvider",
    "ProviderError",
    "MockProvider",
    "OpenAICompatibleProvider",
    "OllamaProvider",
    "build_provider",
]


def build_provider(args: argparse.Namespace) -> BaseProvider:
    if args.provider == "mock":
        return MockProvider()
    if args.provider == "openai-compatible":
        base_url = args.base_url or os.getenv("SWARMOS_BASE_URL")
        api_key = args.api_key or os.getenv("SWARMOS_API_KEY")
        model = args.model or os.getenv("SWARMOS_MODEL")
        if not all([base_url, api_key, model]):
            raise ProviderError(
                "openai-compatible mode requires --base-url/--api-key/--model "
                "or SWARMOS_BASE_URL/SWARMOS_API_KEY/SWARMOS_MODEL."
            )
        return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
    if args.provider == "ollama":
        model = args.model or "qwen2.5:7b"
        base_url = args.base_url or "http://127.0.0.1:11434/v1"
        return OllamaProvider(model=model, base_url=base_url)
    raise ProviderError(f"Unsupported provider: {args.provider}")
