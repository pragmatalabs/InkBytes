"""Skill 3 — SYNTHESIZE.

Called when an event reaches `min_sources_to_publish`. Pulls every article
in the cluster, feeds them to the LLM, and persists a `pages` row.

Article cap (ADR-0015): at most MAX_ARTICLES articles are sent to the LLM,
capped at MAX_PER_OUTLET per outlet and sorted by recency.  Large clusters
(e.g. 131 articles) would otherwise send ~114k input tokens per synthesis call.
The cap targets ~13k tokens per call — a 9× reduction with negligible quality
impact (the LLM already ignores redundant same-outlet content).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from contracts.page_v1 import PageV1
from core.config import LlmCfg
from services.database_service import DatabaseService
from services.llm_service import LlmService

logger = logging.getLogger(__name__)


# Maximum articles to include in a single synthesis prompt (ADR-0015).
# Prevents token explosion on large clusters (e.g. 131-article events).
_MAX_ARTICLES = 15
_MAX_PER_OUTLET = 2


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
            event_id=event_id,
        )
        await self._persist(event_id, page, rows)
        logger.info("SYNTHESIZE %s -> '%s'", event_id, page.headline)
        return page

    @staticmethod
    def _select_articles(rows: list) -> list:
        """Cap articles for synthesis: max _MAX_PER_OUTLET per outlet, then
        top _MAX_ARTICLES by recency (ADR-0015).

        Strategy:
        1. Group by outlet_name.
        2. Within each outlet keep the _MAX_PER_OUTLET most-recently-published.
        3. Merge all kept rows, sort by published_at DESC (nulls last), take
           the first _MAX_ARTICLES.

        This ensures source diversity (no single outlet crowds out others) while
        capping total tokens at a predictable level regardless of cluster size.
        """
        _EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

        by_outlet: dict[str, list] = {}
        for r in rows:
            by_outlet.setdefault(r["outlet_name"], []).append(r)

        pool: list = []
        for outlet_rows in by_outlet.values():
            # Most recent first within each outlet
            sorted_rows = sorted(
                outlet_rows,
                key=lambda x: x["published_at"] or _EPOCH,
                reverse=True,
            )
            pool.extend(sorted_rows[:_MAX_PER_OUTLET])

        # Final sort by recency across all outlets, then cap
        pool.sort(key=lambda x: x["published_at"] or _EPOCH, reverse=True)
        return pool[:_MAX_ARTICLES]

    @staticmethod
    def _format_articles(rows: list) -> str:
        selected = SynthesizeSkill._select_articles(rows)
        chunks = []
        for r in selected:
            body = (r["body_text"] or "")[:3500]
            chunks.append(
                f"- source: {r['outlet_name']}\n"
                f"  url:    {r['url']}\n"
                f"  title:  {r['title']}\n"
                f"  text: |\n    {body.replace(chr(10), chr(10) + '    ')}\n"
            )
        if len(selected) < len(rows):
            chunks.append(
                f"# Note: {len(rows) - len(selected)} additional articles from this cluster "
                f"were omitted (cap: {_MAX_ARTICLES} articles, {_MAX_PER_OUTLET} per outlet).\n"
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
