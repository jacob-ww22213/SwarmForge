from __future__ import annotations

from providers.openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    mode = "ollama"

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434/v1") -> None:
        super().__init__(base_url=base_url, api_key="ollama", model=model)
