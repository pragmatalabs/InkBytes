"""Provider-pluggable LLM for editorial generation (ADR-0008).

ollama + deepseek → OpenAI-compatible `/v1` (AsyncOpenAI); anthropic → native SDK.
Plain-text completion: the editorial is prose with inline [n] citations, not JSON
(the bake-off model writes the column directly), so no structured-output layer.
"""
from __future__ import annotations

import logging

from core.config import LlmCfg

logger = logging.getLogger(__name__)


class Llm:
    def __init__(self, cfg: LlmCfg) -> None:
        self.cfg = cfg
        self.provider = (cfg.provider or "ollama").lower()
        if self.provider == "anthropic":
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=cfg.api_key)
        else:  # ollama / deepseek / any OpenAI-compatible endpoint
            from openai import AsyncOpenAI
            # ollama ignores the key but the SDK requires a non-empty string
            self._client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key or "ollama")

    @property
    def label(self) -> str:
        return f"{self.provider}/{self.cfg.model}"

    async def complete(self, system: str, user: str) -> str:
        if self.provider == "anthropic":
            r = await self._client.messages.create(
                model=self.cfg.model, system=system,
                max_tokens=self.cfg.max_tokens, temperature=self.cfg.temperature,
                messages=[{"role": "user", "content": user}])
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
        r = await self._client.chat.completions.create(
            model=self.cfg.model, temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return (r.choices[0].message.content or "").strip()
