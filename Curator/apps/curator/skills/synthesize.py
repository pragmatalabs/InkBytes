"""Skill 3 — SYNTHESIZE.

Called when an event reaches `min_sources_to_publish`. Pulls every article
in the cluster, feeds them to Haiku, and persists a `pages` row.
"""
from __future__ import annotations

import json
import logging
import re

from contracts.page_v1 import PageV1
from core.config import LlmCfg
from services.database_service import DatabaseService
from services.llm_service import LlmService

logger = logging.getLogger(__name__)


class SynthesizeSkill:
    name = "synthesize"

    def __init__(self, llm: LlmService, db: DatabaseService, llm_cfg: LlmCfg) -> None:
        self.llm = llm
        self.db = db
        self.llm_cfg = llm_cfg
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        raw = LlmService.load_prompt("synthesize")
        return re.split(r"^## Input format", raw, flags=re.MULTILINE)[0].strip()

    async def run(self, event_id: str) -> PageV1 | None:
        async with self.db.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT id, outlet_name, url, title, body_text, language, published_at
                  FROM articles
                 WHERE event_id = $1
                 ORDER BY published_at NULLS LAST, scraped_at
                """,
                event_id,
            )
        if len(rows) < 2:
            logger.info("SYNTHESIZE skipped — event %s has < 2 articles", event_id)
            return None

        user_content = self._format_articles(rows)
        page = await self.llm.structured(
            model=self.llm_cfg.synthesize_model,
            system_prompt=self._system_prompt,
            user_content=user_content,
            response_model=PageV1,
            max_tokens=self.llm_cfg.max_tokens_synth,
        )
        await self._persist(event_id, page, rows)
        logger.info("SYNTHESIZE %s -> '%s'", event_id, page.headline)
        return page

    @staticmethod
    def _format_articles(rows: list) -> str:
        chunks = []
        for r in rows:
            body = (r["body_text"] or "")[:3500]
            chunks.append(
                f"- source: {r['outlet_name']}\n"
                f"  url:    {r['url']}\n"
                f"  title:  {r['title']}\n"
                f"  text: |\n    {body.replace(chr(10), chr(10) + '    ')}\n"
            )
        return "ARTICLES:\n" + "\n".join(chunks)

    async def _persist(self, event_id: str, page: PageV1, rows: list) -> None:
        evidence = [e.model_dump() for e in page.evidence_rail]
        entities = [{"name": n} for n in page.entities_top]
        freshness = max((r["published_at"] for r in rows if r["published_at"]), default=None)
        async with self.db.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                INSERT INTO pages (id, event_id, headline, synthesis_md,
                                   evidence_rail, entities, freshness_at, published_at)
                VALUES ($1, $1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (id) DO UPDATE
                  SET headline = EXCLUDED.headline,
                      synthesis_md = EXCLUDED.synthesis_md,
                      evidence_rail = EXCLUDED.evidence_rail,
                      entities = EXCLUDED.entities,
                      freshness_at = EXCLUDED.freshness_at,
                      published_at = NOW()
                """,
                event_id,
                page.headline,
                page.synthesis_md,
                json.dumps(evidence),
                json.dumps(entities),
                freshness,
            )
            await conn.execute(
                "UPDATE events SET status = 'published', last_updated_at = NOW() WHERE id = $1",
                event_id,
            )
