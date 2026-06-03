"""Application orchestrator — wires services + skills and runs the loop."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from contracts.article_v1 import ArticleScrapedEvent
from core.config import CuratorConfig
from services.database_service import DatabaseService
from services.embedding_service import EmbeddingService
from services.llm_service import LlmService
from services.message_service import MessageService
from skills.cluster import ClusterSkill
from skills.enrich import EnrichSkill
from skills.synthesize import SynthesizeSkill

logger = logging.getLogger(__name__)


class Application:
    NAME = "Curator"
    VERSION = "0.1.0"

    def __init__(self, cfg: CuratorConfig) -> None:
        self.cfg = cfg
        # Services
        self.db = DatabaseService(cfg.database)
        self.llm = LlmService(cfg.llm)
        self.embed = EmbeddingService(cfg.embeddings)
        self.mq = MessageService(cfg.rabbitmq)
        # Skills
        self.enrich = EnrichSkill(self.llm, cfg.llm)
        self.cluster = ClusterSkill(self.db, cfg.clustering)
        self.synthesize = SynthesizeSkill(self.llm, self.db, cfg.llm)
        # Concurrency gate
        self._sem = asyncio.Semaphore(cfg.application.max_concurrent_articles)
        # Background settings-refresh task (started in run_consumer).
        self._config_task: asyncio.Task | None = None

    # ─────────────────────────────────────────── lifecycle ──────────
    async def startup(self, *, with_db: bool = True) -> None:
        if with_db:
            await self.db.connect()
            # Wire the cost meter's DB sink so every completed LLM call is
            # persisted to backoffice.model_usage (Phase 2.2). The write is
            # fire-and-forget and non-fatal; the in-memory totals + COST log
            # line are unchanged.
            self.llm.meter.set_sink(self.db.record_model_usage)
            # Bootstrap the outlets catalogue on a fresh/empty DB only.
            # seed_outlets() is seed-if-empty (ADR-0003): once the table has
            # rows, the Laravel Backoffice owns outlet data and a Curator
            # restart must not overwrite admin edits.
            outlets_cfg = Path(__file__).resolve().parents[4] / \
                "Messor" / "apps" / "scraper" / "data" / "outlets" / "outlets.json"
            if not outlets_cfg.exists():
                # Fallback: look for a local copy next to the curator app
                outlets_cfg = Path(__file__).resolve().parents[1] / "data" / "outlets.json"
            await self.db.seed_outlets(outlets_cfg)
            # Overlay Backoffice-owned tunables from the DB over env/YAML.
            # Absent table/row → keep env/YAML (fallback). Keys stay env-only.
            await self._refresh_config_from_db()
        logger.info(
            "%s v%s ready (mode=%s, db=%s)",
            self.NAME, self.VERSION, self.cfg.application.mode, with_db,
        )

    async def _refresh_config_from_db(self) -> bool:
        """Re-read backoffice.curator_settings and overlay it onto live cfg."""
        row = await self.db.fetch_curator_settings()
        return self.cfg.apply_db_settings(row)

    async def _config_refresh_loop(self) -> None:
        """Periodically re-read settings so admin edits apply without redeploy."""
        interval = self.cfg.application.config_refresh_seconds
        if interval <= 0:
            return
        while True:
            await asyncio.sleep(interval)
            try:
                await self._refresh_config_from_db()
            except Exception:  # pragma: no cover - defensive, never kill the loop
                logger.exception("config refresh failed; will retry")

    async def shutdown(self) -> None:
        if self._config_task is not None:
            self._config_task.cancel()
        await self.mq.close()
        await self.db.close()

    # ─────────────────────────────────────────── modes ──────────────
    async def run_fixture(self, fixture_path: Path) -> None:
        """Process a single Messor event from a JSON fixture file. Offline-safe."""
        payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        await self._handle_event(payload)

    async def run_dry(self, fixture_path: Path) -> None:
        """Run ENRICH + embed only on a fixture — no DB, no clustering, no synth.
        Prints the enrichment result to stdout. Use this to validate prompts +
        LLM connectivity without bringing up Postgres."""
        from contracts.article_v1 import ArticleScrapedEvent

        payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        event = ArticleScrapedEvent.model_validate(payload)
        article = event.article
        logger.info("[dry-run] ENRICH on %s (%s)", article.id, article.outlet.name)
        result = await self.enrich.run(article)
        vec = await self.embed.embed(f"{article.title}\n\n{article.text[:4000]}")
        print()
        print("=" * 60)
        print(f"Article : {article.title}")
        print(f"Outlet  : {article.outlet.name}")
        print(f"Language: {article.language}")
        print("-" * 60)
        print(f"Topic        : {result.topic}")
        print(f"Sentiment    : {result.sentiment}")
        print(f"Factuality   : {result.factuality:.2f}")
        print(f"Summary (50w): {result.summary_50w}")
        print(f"Keywords     : {', '.join(result.keywords_canonical) or '(none)'}")
        print(f"Entities ({len(result.entities)}):")
        for e in result.entities:
            print(f"   - [{e.type:7s}] {e.name}  (salience={e.salience:.2f})")
        print(f"Embedding    : {len(vec)}-dim vector, first 4 = "
              f"{[round(x, 3) for x in vec[:4]]}")
        print("=" * 60)

    async def run_consumer(self) -> None:
        """Run forever, consuming RabbitMQ events."""
        await self.mq.connect()
        await self.mq.consume(self._handle_event)
        # Periodic config refresh so admin edits in the Backoffice take effect
        # without a Curator redeploy (ADR-0004 / backend-architecture §6).
        self._config_task = asyncio.create_task(self._config_refresh_loop())
        # Keep the event loop alive until interrupted.
        await asyncio.Future()

    # ─────────────────────────────────────────── pipeline ───────────
    async def _handle_event(self, payload: dict[str, Any]) -> None:
        async with self._sem:
            try:
                event = ArticleScrapedEvent.model_validate(payload)
            except Exception as e:
                logger.error("Skip malformed event: %s | payload=%s", e, str(payload)[:300])
                return

            article = event.article
            logger.info(
                "→ event %s | outlet=%s | title=%s",
                article.id, article.outlet.name, article.title[:80],
            )

            # 0. persist raw article
            await self.db.upsert_article_raw(article.model_dump(), event.spaces_key)

            # 1. ENRICH
            enrichment = await self.enrich.run(article)
            embedding = await self.embed.embed(
                f"{article.title}\n\n{article.text[:4000]}"
            )
            await self.db.write_enrichment(
                article.id,
                topic=enrichment.topic,
                sentiment=enrichment.sentiment,
                factuality=enrichment.factuality,
                summary_50w=enrichment.summary_50w,
                keywords_canonical=enrichment.keywords_canonical,
                embedding=embedding,
                entities=[e.model_dump() for e in enrichment.entities],
            )

            # 2. CLUSTER
            cluster_result = await self.cluster.run(
                article_id=article.id,
                embedding=embedding,
                entities=[e.model_dump() for e in enrichment.entities],
                outlet_id=article.outlet.id,
                language=article.language,
                scraped_at=article.scraped_at,
            )

            # 3. SYNTHESIZE — only when the event has enough distinct sources
            if cluster_result.source_count >= self.cfg.clustering.min_sources_to_publish:
                await self.synthesize.run(cluster_result.event_id)
            else:
                logger.info(
                    "Hold synthesize: event %s has %d/%d sources",
                    cluster_result.event_id,
                    cluster_result.source_count,
                    self.cfg.clustering.min_sources_to_publish,
                )
