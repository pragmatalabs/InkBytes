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
from services.promo_filter import is_promotional, promo_reason
from services.content_filter import is_excluded, exclusion_reason

logger = logging.getLogger(__name__)


# Maximum articles to include in a single synthesis prompt (ADR-0015).
# Prevents token explosion on large clusters (e.g. 131-article events).
_MAX_ARTICLES = 15
_MAX_PER_OUTLET = 2


class SynthesizeSkill:
    name = "synthesize"

    def __init__(self, llm: LlmService, db: DatabaseService, llm_cfg: LlmCfg,
                 filter_promotional: bool = True,
                 filter_noise: bool = True) -> None:
        self.llm = llm
        self.db = db
        self.llm_cfg = llm_cfg
        self.filter_promotional = filter_promotional
        self.filter_noise = filter_noise
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        raw = LlmService.load_prompt("synthesize")
        return re.split(r"^## Input format", raw, flags=re.MULTILINE)[0].strip()

    async def run(self, event_id: str, force: bool = False) -> PageV1 | None:
        """Synthesize (and publish) the event's page.

        ``force=True`` (manual breaking gate, ADR-0029): an editor has vetted
        this story, so bypass the ≥2-article minimum and the promo/noise
        publish gates. Still requires ≥1 article to have content to synthesize.
        """
        async with self.db.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT id, outlet_name, url, title, body_text, language, published_at, scraped_at
                  FROM articles
                 WHERE event_id = $1
                 ORDER BY published_at NULLS LAST, scraped_at
                """,
                event_id,
            )
        if not rows:
            logger.info("SYNTHESIZE skipped — event %s has no articles", event_id)
            return None
        if len(rows) < 2 and not force:
            logger.info("SYNTHESIZE skipped — event %s has < 2 articles", event_id)
            return None
        if len(rows) < 2 and force:
            logger.info("SYNTHESIZE force — event %s with %d article(s) (editor override)",
                        event_id, len(rows))

        # Promotional-cluster gate (ADR-0020): when a strict majority of the
        # cluster's article titles are shopping/affiliate content (gift guides,
        # product reviews, deals), the event is a commerce roundup, not news —
        # skip BEFORE the LLM call so we don't pay to synthesize an ad page.
        if self.filter_promotional and not force:
            titles = [r["title"] for r in rows if r["title"]]
            promo = sum(1 for t in titles if is_promotional(t))
            if titles and promo * 2 > len(titles):
                logger.info(
                    "SYNTHESIZE skipped — promotional cluster (%d/%d article titles "
                    "look commercial), event %s", promo, len(titles), event_id,
                )
                return None

        # Non-news filler gate (ADR-0021): skip a cluster that is a strict
        # majority horoscope / lottery-result / betting-pick filler — these
        # recur daily across outlets and cluster into junk pages.
        if self.filter_noise and not force:
            titles = [r["title"] for r in rows if r["title"]]
            noise = sum(1 for t in titles if is_excluded(t))
            if titles and noise * 2 > len(titles):
                logger.info(
                    "SYNTHESIZE skipped — non-news filler cluster (%d/%d article "
                    "titles are horoscope/lottery/betting), event %s",
                    noise, len(titles), event_id,
                )
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

        # Backstop: even a mixed cluster can yield an ad-style headline
        # ("X Covers Top Gifts and Y Reviews"). Don't publish those.
        if self.filter_promotional and not force and (reason := promo_reason(page.headline)):
            logger.info(
                "SYNTHESIZE skipped — ad-style headline [%s]: '%s' (event %s)",
                reason, page.headline, event_id,
            )
            return None

        # Backstop: a mixed cluster can still yield a filler headline
        # ("Horóscopo del día y resultados de la lotería"). Don't publish those.
        if self.filter_noise and not force and (reason := exclusion_reason(page.headline)):
            logger.info(
                "SYNTHESIZE skipped — filler headline [%s]: '%s' (event %s)",
                reason, page.headline, event_id,
            )
            return None

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
        # Use scraped_at (Messor wall-clock, always reliable) not published_at
        # (outlet-supplied — can be null, future-dated, or wrong). See memory:
        # freshness-at-use-scraped-at.md
        freshness = max((r["scraped_at"] for r in rows if r["scraped_at"]), default=None)
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
