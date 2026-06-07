"""Skill 1 — ENRICH.

One LLM call per article. Produces NER + topic + summary + sentiment +
factuality + canonical keywords. Validated against `EnrichmentResult`.
"""
from __future__ import annotations

import logging
import re

from contracts.article_v1 import ArticleV1
from contracts.enriched_v1 import EnrichmentResult
from core.config import LlmCfg
from services.llm_service import LlmService

logger = logging.getLogger(__name__)


def _build_user_content(art: ArticleV1) -> str:
    body = art.text
    # Soft truncate at ~6000 chars; ENRICH doesn't need the whole text.
    if len(body) > 6000:
        body = body[:6000] + "\n[...truncated...]"

    lines = [
        f"TITLE:    {art.title}",
        f"OUTLET:   {art.outlet.name}",
        f"LANGUAGE: {art.language}",
    ]

    # Pass Messor-extracted signals as context hints so the LLM can inform
    # theme/topic/keywords without having to re-derive them from scratch.
    if art.category:
        lines.append(f"OUTLET_SECTION:  {art.category}")
    if art.meta_categories:
        lines.append(f"OUTLET_TAGS:     {', '.join(art.meta_categories[:8])}")
    if art.keywords:
        lines.append(f"META_KEYWORDS:   {', '.join(art.keywords[:10])}")

    lines.append(f"TEXT:\n{body}")
    return "\n".join(lines)


class EnrichSkill:
    name = "enrich"

    def __init__(self, llm: LlmService, llm_cfg: LlmCfg) -> None:
        self.llm = llm
        self.llm_cfg = llm_cfg
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        raw = LlmService.load_prompt("enrich")
        # Strip the input/output sections — they describe the contract for
        # humans; the API call sets system + user directly.
        return re.split(r"^## Input format", raw, flags=re.MULTILINE)[0].strip()

    async def run(self, article: ArticleV1) -> EnrichmentResult:
        logger.info("ENRICH %s (%s)", article.id, article.outlet.name)
        return await self.llm.structured(
            model=self.llm_cfg.enrich_model,
            system_prompt=self._system_prompt,
            user_content=_build_user_content(article),
            response_model=EnrichmentResult,
            max_tokens=self.llm_cfg.max_tokens_enrich,
        )
