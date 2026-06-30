"""Application orchestrator — wires services + skills and runs the loop."""
from __future__ import annotations

import asyncio
import json

import httpx
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from contracts.article_v1 import ArticleScrapedEvent, _Outlet
from contracts.article_v1 import ArticleV1
from core.config import CuratorConfig
from services.database_service import DatabaseService
from services.embedding_service import EmbeddingService
from services.llm_service import LlmService, LlmQuotaError
from services.media_validation import MediaValidator
from services.message_service import MessageService, ProcessingPausedError
from services import taxonomy
from services.ner_prepass import NerPrepass
from services.cover_image import pick_cover, _UA as _COVER_UA
from skills.assistant import AssistantSkill
from skills.cluster import ClusterSkill
from skills.enrich import EnrichSkill
from skills.triage import TriageSkill
from skills.illustrate import IllustrateSkill
from skills.synthesize import SynthesizeSkill

logger = logging.getLogger(__name__)


def _parse_vector(raw: Any) -> list[float]:
    """Parse a pgvector value back into a list[float].

    asyncpg has no native vector codec here, so the column round-trips as the
    text literal `[0.1,0.2,...]`. (If a list ever comes through directly, pass
    it untouched.)
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    s = str(raw).strip().lstrip("[").rstrip("]")
    if not s:
        return []
    return [float(x) for x in s.split(",")]


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
        # Lead-image hotlink guard (ADR-0019): probes og:image URLs at ingest.
        self.media = MediaValidator(
            enabled=cfg.application.validate_lead_images,
            timeout_s=cfg.application.lead_image_probe_timeout_s,
        )
        # Skills
        self.enrich = EnrichSkill(self.llm, cfg.llm)
        # Pre-enrich triage gate (ADR-0030): small local model drops junk before
        # the paid DeepSeek enrich. No-op when cfg.triage.enabled is False.
        self.triage = TriageSkill(cfg.triage)
        # spaCy NER pre-pass (ADR-0032 item 2): deterministic typed entities fed
        # to enrich as MUST_COVER hints. No-op when cfg.ner.enabled is False.
        self.ner = NerPrepass(cfg.ner)
        self.cluster = ClusterSkill(self.db, cfg.clustering)
        self.synthesize = SynthesizeSkill(
            self.llm, self.db, cfg.llm,
            filter_promotional=cfg.application.filter_promotional,
            filter_noise=cfg.application.filter_noise,
        )
        self.illustrate = IllustrateSkill(self.db)
        # Corpus chat assistant (ADR-0022): grounded digests + Q&A over
        # published events, reusing the synthesis LLM engine.
        self.assistant = AssistantSkill(self.llm, self.db, self.embed, cfg.llm)
        # Concurrency gate — article pipeline
        self._sem = asyncio.Semaphore(cfg.application.max_concurrent_articles)
        # Embed serialisation: CPU-only Ollama bge-m3 saturates (and times out)
        # under concurrent requests — this semaphore is what makes a
        # prefetch_count > 1 consumer safe, replacing the old global
        # prefetch_count=1 serialisation. Raise to 2+ only if Ollama moves to
        # GPU or a dedicated embedding server.
        self._embed_sem = asyncio.Semaphore(1)
        # Triage gate concurrency (ADR-0030): bound parallel local-model calls so
        # the shared CPU box isn't hit by max_concurrent_articles generations at
        # once (same reasoning as _embed_sem).
        self._triage_sem = asyncio.Semaphore(max(1, cfg.triage.max_concurrent))
        # NER pre-pass concurrency (ADR-0032 item 2): spaCy runs in worker threads;
        # bound them so N in-flight articles don't saturate the shared CPU box.
        self._ner_sem = asyncio.Semaphore(max(1, cfg.ner.max_concurrent))
        # Cluster-attach serialisation: two same-story articles clustering
        # concurrently would each see "no neighbour" and seed duplicate events.
        # The attach decision is fast (~1s: one ANN query + two UPDATEs), so a
        # global lock here costs little and keeps clustering race-free.
        self._cluster_lock = asyncio.Lock()
        # IllustrateSkill concurrency gate: cap at 1 concurrent browser pair.
        # Each run opens 2 Chromium instances (~400 MB combined); the worker has
        # a 1.5 GB limit on DO.  Excess calls queue and run serially after the
        # browsers close — illustration is always fire-and-forget so the delay
        # never affects the RabbitMQ ACK or synthesis latency.
        self._illustrate_sem = asyncio.Semaphore(1)
        # Cover-image agent (ADR-0034 T2): bound concurrent Wikimedia/Openverse
        # lookups. Cheap HTTP, but throttle to be a polite API citizen.
        self._cover_sem = asyncio.Semaphore(2)
        # Per-event synthesis locks: if synthesis is already in-flight for an
        # event, concurrent requests skip rather than pile up.  Prevents the
        # N-articles-in-one-event → N synthesis calls explosion during batch
        # reprocessing (each call costs ~$0.05-0.06 and rewrites the same page).
        self._synth_locks: dict[str, asyncio.Lock] = {}
        # The source_count at last synthesis lives in
        # events.last_synth_source_count (migration 015) — persistent, so a
        # worker restart no longer re-synthesizes every qualifying event on
        # its next article. The in-memory dict it replaces caused the
        # 2026-06-12 post-deploy synthesis storm (restart + 3.7k backlog →
        # hundreds of reasoner calls hogging the pipeline slots).
        # Background settings-refresh task (started in run_consumer).
        self._config_task: asyncio.Task | None = None
        # Embedding live-reconfigure status (ADR-0004), surfaced on /status:
        #   embeddings_stale   → provider/model changed; corpus needs a re-embed
        #   embeddings_blocked → chosen model's dims ≠ column width; needs migration
        self.embeddings_stale = False
        self.embeddings_blocked: str | None = None
        self._reembed_task: asyncio.Task | None = None

    # ─────────────────────────────────────────── properties ─────────

    @property
    def synths_in_flight(self) -> int:
        """Live count of per-event synthesis locks currently held.

        Exposed on /status so the API layer doesn't access _synth_locks
        directly (ADR-0006 §D5).
        """
        return sum(1 for lock in self._synth_locks.values() if lock.locked())

    @property
    def reembedding(self) -> bool:
        """True when a corpus re-embed background task is currently running.

        Exposed on /status so the API layer doesn't access _reembed_task
        directly (ADR-0006 §D5).
        """
        return bool(self._reembed_task and not self._reembed_task.done())

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
            # Resolve outlets.json — three search paths:
            # 1. Monorepo root sibling (local dev, parents[4] = InkBytes/)
            # 2. Curator app-local copy /app/data/outlets.json (Docker image)
            # 3. Skip seed — table already populated (backoffice owns it post-seed)
            try:
                monorepo_outlets = Path(__file__).resolve().parents[4] / \
                    "Messor" / "apps" / "scraper" / "data" / "outlets" / "outlets.json"
            except IndexError:
                monorepo_outlets = Path("/nonexistent")  # Docker: path too shallow
            local_outlets = Path(__file__).resolve().parents[1] / "data" / "outlets.json"
            outlets_cfg = monorepo_outlets if monorepo_outlets.exists() else local_outlets
            await self.db.seed_outlets(outlets_cfg)
            # Overlay Backoffice-owned tunables from the DB over env/YAML.
            # Absent table/row → keep env/YAML (fallback). Keys stay env-only.
            await self._refresh_config_from_db()
        logger.info(
            "%s v%s ready (mode=%s, db=%s)",
            self.NAME, self.VERSION, self.cfg.application.mode, with_db,
        )

    async def _refresh_config_from_db(self) -> bool:
        """Re-read backoffice.curator_settings and overlay it onto live cfg.

        After overlaying, rebuild the EmbeddingService client if the
        provider/model/base_url changed (the client is cached per signature, so
        a cfg mutation alone would not take effect — ADR-0004). The rebuild is
        dim-guarded: a model whose vectors don't fit the live column width is
        refused (embeddings_blocked) rather than breaking every INSERT.
        """
        row = await self.db.fetch_curator_settings()
        changed = self.cfg.apply_db_settings(row)
        expected = await self.db.embedding_column_dims()
        result = await self.embed.reconfigure(self.cfg.embeddings, expected_dims=expected)
        if result.get("changed"):
            if result.get("applied"):
                self.embeddings_stale = True
                self.embeddings_blocked = None
            elif result.get("reason") == "dim_mismatch":
                self.embeddings_blocked = (
                    f"model emits {result.get('probed_dims')}-d but column is "
                    f"{result.get('expected_dims')}-d — needs a vector-width migration"
                )
            elif result.get("reason") == "probe_failed":
                self.embeddings_blocked = f"embedder unreachable: {result.get('error')}"
        # LLM provider/model live-switch (ADR-0004). Synchronous — no network
        # probe needed. Failures keep the existing client running.
        llm_result = self.llm.reconfigure(self.cfg.llm)
        if llm_result.get("changed"):
            if llm_result.get("applied"):
                logger.info(
                    "LLM provider/model switched to %s/%s (synth=%s)",
                    self.cfg.llm.provider,
                    self.cfg.llm.enrich_model,
                    self.cfg.llm.synthesize_model,
                )
            else:
                logger.error(
                    "LLM reconfigure failed: %s — keeping current client. %s",
                    llm_result.get("reason"),
                    llm_result.get("error"),
                )
        return changed

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
        await self.llm.close()   # closes underlying httpx AsyncClient
        await self.media.aclose()
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
        must_cover = await self.ner.extract(article) if self.cfg.ner.enabled else []
        if must_cover:
            logger.info("[dry-run] MUST_COVER (%d): %s", len(must_cover),
                        ", ".join(f"{e.type}:{e.name}" for e in must_cover))
        result = await self.enrich.run(article, must_cover=must_cover)
        vec = await self.embed.embed(f"{article.title}\n\n{article.text[:4000]}")
        print()
        print("=" * 60)
        print(f"Article : {article.title}")
        print(f"Outlet  : {article.outlet.name}")
        print(f"Language: {article.language}")
        print("-" * 60)
        print(f"Theme        : {result.theme}")
        _cat = (taxonomy.normalize_category(result.article_category)
                or taxonomy.suggest_category(article.category, article.meta_categories))
        print(f"Category(33) : {_cat or '(none)'}  [llm={result.article_category or '—'}]")
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
        """Run forever, consuming RabbitMQ events + Backoffice commands.

        Stops cleanly when an LlmQuotaError is surfaced by the article consumer
        (quota exhausted — articles requeued, pipeline halted until reset).
        """
        stop = asyncio.get_event_loop().create_future()

        def _on_quota() -> None:
            logger.critical(
                "LLM quota exhausted — consumer stopping. "
                "Pending articles have been requeued. "
                "Restart the worker when the Anthropic quota resets."
            )
            if not stop.done():
                stop.set_result(None)

        await self.mq.connect()
        await self.mq.consume(self._handle_event, on_quota_exhausted=_on_quota)
        # Messor harvest run summaries (B12.1 / ADR-0006): one event per run on
        # the same `messor` exchange. Curator upserts public.scrape_sessions so
        # the Backoffice has durable run history independent of Messor's :8050.
        await self.mq.consume_scrape_sessions(self._handle_scrape_session)
        # Backoffice moderation commands (Phase 2.3): publish/unpublish/drop and
        # re-synthesize/re-cluster. Curator owns the writes to public.events /
        # public.pages; the Backoffice only issues these commands (ADR-0003).
        await self.mq.consume_commands(self._handle_command)
        # Periodic config refresh so admin edits in the Backoffice take effect
        # without a Curator redeploy (ADR-0004 / backend-architecture §6).
        self._config_task = asyncio.create_task(self._config_refresh_loop())
        # Keep the event loop alive until interrupted or quota exhausted.
        await stop

    async def run_command_consumer(self) -> None:
        """Consume ONLY the Backoffice command queue (no article pipeline).

        Used by `main.py --consume-commands` as a focused harness that does not
        bind the FastAPI port 8060, so it can run alongside an existing
        `--api-only` Curator instance during Phase 2.3 testing.
        """
        await self.mq.connect()
        await self.mq.consume_commands(self._handle_command)
        await asyncio.Future()

    async def run_session_consumer(self) -> None:
        """Consume ONLY Messor's scrape-session run summaries (B12.1 harness).

        Like `run_command_consumer`, this does NOT bind the FastAPI port 8060,
        so it can run alongside an existing `--api-only` Curator instance for
        focused round-trip testing of `scrape.session.completed` → DB upsert.
        """
        await self.mq.connect()
        await self.mq.consume_scrape_sessions(self._handle_scrape_session)
        await asyncio.Future()

    # ─────────────────────────────────────── scrape sessions ────────
    async def _handle_scrape_session(self, payload: dict[str, Any]) -> None:
        """Upsert one Messor harvest run into public.scrape_sessions (B12.1).

        Defensive by design: a malformed payload or a DB hiccup logs + returns
        (the caller ACKs regardless). A run summary is history — losing one must
        never wedge the consumer or affect the article pipeline.
        """
        data = (payload or {}).get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            logger.error("scrape.session: no 'data' object — payload=%s", str(payload)[:300])
            return
        session_id = data.get("session_id") or data.get("id")
        if not session_id:
            logger.error("scrape.session: missing session_id — data=%s", str(data)[:300])
            return

        outlets = data.get("outlets") or []
        if not isinstance(outlets, list):
            outlets = []

        try:
            await self.db.upsert_scrape_session(
                session_id=str(session_id),
                started_at=data.get("started_at") or data.get("start_time"),
                ended_at=data.get("ended_at") or data.get("end_time"),
                total_articles=int(data.get("total_articles") or 0),
                successful_articles=int(data.get("successful_articles") or 0),
                failed_articles=int(data.get("failed_articles") or 0),
                duplicates_total=int(data.get("duplicates_total") or 0),
                success_rate=float(data.get("success_rate") or 0.0),
                duration_seconds=(
                    float(data["duration"])
                    if data.get("duration") is not None else None
                ),
                outlets=outlets,
                total_outlets=int(data.get("total_outlets") or len(outlets)),
                lane=str(data.get("lane") or "cycle"),
            )
            logger.info(
                "✓ scrape_sessions upsert %s | outlets=%d total=%d new=%d dup=%d",
                session_id, int(data.get("total_outlets") or len(outlets)),
                int(data.get("total_articles") or 0),
                int(data.get("successful_articles") or 0),
                int(data.get("duplicates_total") or 0),
            )
        except Exception:
            logger.exception("scrape.session: DB upsert failed for %s", session_id)

    # ─────────────────────────────────────────── commands ───────────
    async def _handle_command(self, routing_key: str, payload: dict[str, Any]) -> None:
        """Dispatch a single Backoffice moderation command.

        routing_key is the command name; payload carries `{"id": "<target>"}`.
        Curator performs the actual write/skill re-run (it owns these tables).
        """
        target_id = (payload or {}).get("id")
        if not target_id:
            logger.error("command %s missing 'id' — payload=%s", routing_key, payload)
            return
        logger.info("← command %s id=%s", routing_key, target_id)

        if routing_key == "page.publish":
            ok = await self.db.set_page_published(target_id, published=True)
            logger.info("page.publish %s -> %s", target_id, "ok" if ok else "no such page")
        elif routing_key == "page.unpublish":
            ok = await self.db.set_page_published(target_id, published=False)
            logger.info("page.unpublish %s -> %s", target_id, "ok" if ok else "no such page")
        elif routing_key == "page.drop":
            ok = await self.db.drop_page(target_id)
            logger.info("page.drop %s -> %s", target_id, "ok" if ok else "no such page")
        elif routing_key == "event.resynthesize":
            # Re-run synthesis for this event id (writes/updates its pages row).
            # Works in stub mode without LLM keys (deterministic offline output).
            await self.synthesize.run(target_id)
            logger.info("event.resynthesize %s dispatched", target_id)
        elif routing_key == "event.recluster":
            await self._recluster_event(target_id)
            logger.info("event.recluster %s dispatched", target_id)
        elif routing_key == "event.mark_breaking":
            # Manual breaking gate (ADR-0029): editor flags this event breaking
            # regardless of the auto-detector's pulse-outlet velocity.
            ttl = (payload or {}).get("ttl_hours") or self.cfg.clustering.breaking_ttl_hours
            ok = await self.db.set_event_breaking(target_id, ttl_hours=int(ttl))
            logger.info("event.mark_breaking %s -> %s (ttl=%sh)",
                        target_id, "ok" if ok else "no such event", ttl)
        elif routing_key == "event.clear_breaking":
            ok = await self.db.clear_event_breaking(target_id)
            logger.info("event.clear_breaking %s -> %s", target_id, "ok" if ok else "no such event")
        elif routing_key == "event.force_publish":
            # Manual breaking gate (ADR-0029): synthesize + publish even below
            # the ≥2-source bar and past the promo/noise gates — the editor has
            # vetted this story. force=True bypasses those guards in the skill.
            page = await self.synthesize.run(target_id, force=True)
            logger.info("event.force_publish %s -> %s",
                        target_id, "published" if page else "skipped (no articles)")
        elif routing_key == "embeddings.reembed":
            # Corpus-wide re-embed with the CURRENT embedder (ADR-0004). Runs in
            # the background so the command consumer stays responsive; a second
            # request while one is running is ignored. payload id is advisory
            # ("all" | "missing"); default re-embeds the whole corpus.
            only_missing = str(target_id).lower() == "missing"
            if self._reembed_task and not self._reembed_task.done():
                logger.info("embeddings.reembed already running — ignoring duplicate request")
            else:
                self._reembed_task = asyncio.create_task(self._reembed_corpus(only_missing))
                logger.info("embeddings.reembed dispatched (only_missing=%s)", only_missing)
        else:
            logger.warning("unknown command routing_key=%s — ignored", routing_key)

    async def _reembed_corpus(self, only_missing: bool = False) -> None:
        """(Re-)embed articles with the current embedder, then clear the stale
        flag. Bounded concurrency; overwrites existing vectors so a post-switch
        corpus is rebuilt in the new model's vector space."""
        rows = await self.db.fetch_articles_for_embedding(only_missing=only_missing)
        logger.info("embeddings.reembed: %d articles (only_missing=%s)", len(rows), only_missing)
        sem = asyncio.Semaphore(self.cfg.application.max_concurrent_articles)
        done = 0

        async def one(r: dict[str, Any]) -> None:
            nonlocal done
            async with sem:
                text = f"{r['title']}\n\n{(r['body_text'] or '')[:4000]}"
                async with self._embed_sem:
                    vec = await self.embed.embed(text)
                await self.db.set_article_embedding(r["id"], vec)
                done += 1
                if done % 200 == 0:
                    logger.info("embeddings.reembed: %d/%d", done, len(rows))

        try:
            await asyncio.gather(*(one(r) for r in rows))
        except Exception:
            logger.exception("embeddings.reembed failed partway (%d/%d done)", done, len(rows))
            return
        self.embeddings_stale = False
        logger.info("embeddings.reembed complete: %d articles embedded.", done)

    async def _recluster_event(self, event_id: str) -> None:
        """Re-run clustering for every article currently in an event.

        Re-clustering an existing event means re-evaluating its members against
        the recent neighbourhood: we detach the articles, then feed each back
        through ClusterSkill (which may re-form the same event or split/merge).
        Re-synthesis is left to a follow-up `event.resynthesize` command so the
        two actions stay independently triggerable from the UI.
        """
        async with self.db.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT id, embedding, outlet_id, language, scraped_at
                  FROM articles
                 WHERE event_id = $1 AND embedding IS NOT NULL
                 ORDER BY scraped_at
                """,
                event_id,
            )
            if not rows:
                logger.info("event.recluster %s — no articles to recluster", event_id)
                return
            # Detach members so the cluster skill re-resolves them from scratch.
            await conn.execute(
                "UPDATE articles SET event_id = NULL, cluster_distance = NULL "
                "WHERE event_id = $1",
                event_id,
            )

        for r in rows:
            ent_rows = await self._article_entities(r["id"])
            # embedding comes back as a pgvector text literal "[..]"; parse it.
            embedding = _parse_vector(r["embedding"])
            await self.cluster.run(
                article_id=r["id"],
                embedding=embedding,
                entities=ent_rows,
                outlet_id=r["outlet_id"],
                language=r["language"],
                scraped_at=r["scraped_at"],
            )

    async def _article_entities(self, article_id: str) -> list[dict[str, Any]]:
        async with self.db.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                "SELECT name, type, salience FROM entities WHERE article_id = $1",
                article_id,
            )
        return [dict(r) for r in rows]

    # ─────────────────────────────────────────── pipeline ───────────
    async def _synthesize_once(self, event_id: str, source_count: int) -> "PageV1 | None":
        """Run synthesis for `event_id`, gated on two conditions:

        1. **New source gate** — synthesis only runs when `source_count` exceeds
           the value recorded at the last synthesis.  New articles from outlets
           that are already in the event don't warrant a full page rewrite.
           This prevents the N-articles-per-event → N synthesis calls explosion
           (e.g. a 136-article AI-stocks cluster that fired 105 synth calls).

        2. **In-flight gate** — a per-event asyncio.Lock ensures concurrent
           callers (batch reprocessing) skip if synthesis is already running.

        `source_count` is the live distinct-outlet count from the cluster result.
        Pass 0 to bypass the source-count gate (used by Moderation re-synthesize).

        Returns the PageV1 that was written (or None if skipped / already running).
        IllustrateSkill uses the headline to build a targeted search query.
        """
        from contracts.page_v1 import PageV1

        last = await self.db.get_last_synth_source_count(event_id)
        if source_count > 0 and source_count <= last:
            logger.debug(
                "SYNTHESIZE %s skipped — source_count=%d unchanged since last synth (last=%d)",
                event_id, source_count, last,
            )
            return None

        if event_id not in self._synth_locks:
            self._synth_locks[event_id] = asyncio.Lock()
        lock = self._synth_locks[event_id]
        if lock.locked():
            logger.debug("SYNTHESIZE %s skipped — already in-flight", event_id)
            return None
        page: PageV1 | None = None
        async with lock:
            page = await self.synthesize.run(event_id)
            # Persist the watermark (migration 015) so the "new outlet only"
            # re-synthesis gate survives worker restarts.
            await self.db.set_last_synth_source_count(event_id, source_count)
        # Prune the lock entry — synthesis just completed and no one else can
        # be waiting (callers skip when lock.locked(), and asyncio is
        # single-threaded: no await between lock release and pop, so no new
        # waiter can sneak in).  Keeps _synth_locks bounded (ADR-0006 §D6).
        if not lock.locked():
            self._synth_locks.pop(event_id, None)
        return page

    async def _illustrate_safe(self, event_id: str, headline: str) -> None:
        """Fire-and-forget wrapper: run IllustrateSkill without blocking the pipeline.

        Serialised via _illustrate_sem (Semaphore(1)) so at most one pair of
        Chromium instances is alive at any moment — keeps peak RSS under the
        1.5 GB worker limit even during batch harvest cycles where many events
        synthesize concurrently.

        Errors are caught and logged — a failed illustration never fails the
        event.  Runs as a background asyncio.Task spawned after synthesis.
        """
        async with self._illustrate_sem:
            try:
                await self.illustrate.run(event_id, headline)
            except Exception:
                logger.exception("ILLUSTRATE %s failed (non-fatal)", event_id)

    async def _cover_safe(self, event_id: str) -> None:
        """Cover-image agent (ADR-0034 Tier 2). Fire-and-forget after synthesis:
        if the event has no cover yet, pick a license-clean generic image —
        Wikimedia/Wikidata P18 for its top LOC/ORG entity, else an Openverse CC0
        keyword image — and store it. Reader renders it over the procedural cover.
        Fail-open: a failed lookup never affects the event (procedural cover stays).
        """
        async with self._cover_sem:
            try:
                row = await self.db.get_event_cover_inputs(event_id)
                if not row or row.get("has_cover"):
                    return
                # Context disambiguates ambiguous entity names in the Wikimedia
                # lookup (e.g. "Proton" tech story → Proton AG, not the carmaker).
                context = " ".join(filter(None, [
                    row.get("headline"), row.get("theme"), row.get("entity_terms")]))
                async with httpx.AsyncClient(
                    timeout=20.0, headers={"User-Agent": _COVER_UA}
                ) as client:
                    cover = await pick_cover(
                        row.get("theme"), row.get("top_loc"), row.get("top_org"),
                        event_id, client, context=context,
                    )
                if cover:
                    await self.db.write_cover_image(event_id, cover)
                    logger.info("COVER %s → [%s/%s] %s", event_id,
                                cover.get("provider"), cover.get("license"),
                                (cover.get("url") or "")[:48])
            except Exception:
                logger.exception("COVER %s failed (non-fatal)", event_id)

    async def _handle_event(self, payload: dict[str, Any]) -> None:
        # Kill-switch (Backoffice "Stop Curator", ADR-0023): when processing is
        # disabled, requeue the article untouched (no loss) and let the consumer
        # back off. Checked BEFORE the malformed-event try so it propagates to
        # the consumer's pause branch rather than being swallowed as a bad event.
        if not self.cfg.application.processing_enabled:
            raise ProcessingPausedError()
        async with self._sem:
            try:
                event = ArticleScrapedEvent.model_validate(payload)
            except Exception as e:
                logger.error("Skip malformed event: %s | payload=%s", e, str(payload)[:300])
                return

            article = event.article

            # Stale-message intake gate: the Reader feed window is 48h (Messor
            # ADR-0015), so an article whose harvest is older than
            # max_article_age_hours can never surface — ack-and-drop it BEFORE
            # spending an LLM call. Protects against queue floods (the 105k-msg
            # incident of 2026-06-09) and bounds worst-case backlog damage.
            max_age_h = self.cfg.application.max_article_age_hours
            if max_age_h > 0 and article.scraped_at is not None:
                try:
                    scraped = article.scraped_at
                    if isinstance(scraped, str):
                        scraped = datetime.fromisoformat(scraped.replace("Z", "+00:00"))
                    if scraped.tzinfo is None:
                        scraped = scraped.replace(tzinfo=timezone.utc)
                    age_h = (datetime.now(timezone.utc) - scraped).total_seconds() / 3600
                    if age_h > max_age_h:
                        logger.info(
                            "DROP stale message %s (%s) — scraped %.1fh ago (gate=%dh)",
                            article.id, article.outlet.name, age_h, max_age_h,
                        )
                        return
                except (ValueError, TypeError):
                    pass  # unparseable date — process normally rather than drop

            logger.info(
                "→ event %s | outlet=%s | title=%s",
                article.id, article.outlet.name, article.title[:80],
            )

            # 0. persist raw article
            # Returns True when the article is new or its content changed (needs
            # full LLM pipeline).  Returns False when content is unchanged and
            # enriched_at is already set — the duplicate fast-path (ADR-0015):
            # skip ENRICH + EMBED, the existing enrichment in the DB is valid.
            art_dict = article.model_dump()
            # Lead-image hotlink guard (ADR-0019): an og:image that a cross-origin
            # <img> can't render (CDN hotlink-redirects to a 1×1 placeholder) is
            # stored as NULL so the /events lead_image rollup falls back to
            # another source's image instead of showing a blank hero.
            lead = art_dict.get("lead_image")
            if lead and not await self.media.is_displayable(lead):
                logger.info(
                    "lead_image hotlink-blocked, dropping for %s (%s): %s",
                    article.id, article.outlet.name, lead,
                )
                art_dict["lead_image"] = None
            # Author-photo guard (ADR-0016): some outlets (e.g. Heraldo) set
            # og:image to a journalist headshot.  URL-pattern check is sync +
            # free; NULLs it so events.hero_image (YouTube thumbnail) fills in.
            lead = art_dict.get("lead_image")
            if lead and self.media.is_author_photo(lead):
                logger.info(
                    "lead_image looks like author photo, dropping for %s (%s): %s",
                    article.id, article.outlet.name, lead,
                )
                art_dict["lead_image"] = None
            needs_enrichment = await self.db.upsert_article_raw(art_dict, event.spaces_key)
            if not needs_enrichment:
                # info-level (not debug): this is the ADR-0015/0018 duplicate
                # fast-path firing — the line we grep to confirm re-scrapes are
                # NOT re-enriched. Expect a flood during a re-publish backlog
                # drain; that is the fix working, not noise.
                logger.info(
                    "SKIP %s (%s) — already enriched, content unchanged",
                    article.id, article.outlet.name,
                )
                return

            # Pre-enrich triage gate (ADR-0030): a small local model drops junk
            # (horoscopes, lottery/betting, deals, dead pages) before the paid
            # DeepSeek enrich. Runs only on articles that would actually be
            # enriched (after the dedup fast-path). Shadow mode logs the verdict
            # without dropping, so we can measure precision before enforcing.
            if self.cfg.triage.enabled:
                async with self._triage_sem:
                    tv = await self.triage.run(article)
                if tv.drop:
                    if self.cfg.triage.shadow:
                        logger.info(
                            "TRIAGE shadow-DROP %s (%s) — %s | %s",
                            article.id, article.outlet.name, tv.reason, article.title[:80],
                        )
                    else:
                        logger.info(
                            "TRIAGE DROP %s (%s) — %s | %s",
                            article.id, article.outlet.name, tv.reason, article.title[:80],
                        )
                        # Terminal marker (ADR-0030 / migration 017): keeps the
                        # raw article but stamps it dropped, so it leaves the
                        # /status pending counter and is never re-enriched.
                        await self.db.mark_triage_dropped(article.id, tv.reason)
                        return  # ack; skip enrich/cluster/synth (raw article kept)

            # NER pre-pass (ADR-0032 item 2): deterministic typed entities the
            # LLM must consider, so it can't under-extract people/orgs/places.
            # Runs only on articles that survived triage; fail-open ([] → LLM
            # only); bounded so spaCy threads don't saturate the CPU box.
            must_cover = []
            if self.cfg.ner.enabled:
                async with self._ner_sem:
                    must_cover = await self.ner.extract(article)

            # 1. ENRICH — the slow stage (8-17s of LLM network wait); runs
            # concurrently across messages up to max_concurrent_articles.
            enrichment = await self.enrich.run(article, must_cover=must_cover)
            # Embed is serialised (_embed_sem): CPU-only Ollama times out under
            # concurrent load. ~0.2-1s per call, so the lock is cheap.
            async with self._embed_sem:
                embedding = await self.embed.embed(
                    f"{article.title}\n\n{article.text[:4000]}"
                )
            # Granular category (ADR-0032 item 1): normalize the LLM's pick to
            # the canonical 33 set; fall back to the deterministic 634→33 bridge
            # over Messor's section/tags when the model abstained.
            article_category = (
                taxonomy.normalize_category(enrichment.article_category)
                or taxonomy.suggest_category(article.category, article.meta_categories)
            )
            await self.db.write_enrichment(
                article.id,
                theme=enrichment.theme,
                topic=enrichment.topic,
                sentiment=enrichment.sentiment,
                factuality=enrichment.factuality,
                summary_50w=enrichment.summary_50w,
                keywords_canonical=enrichment.keywords_canonical,
                embedding=embedding,
                entities=[e.model_dump() for e in enrichment.entities],
                article_category=article_category,
            )

            # 2. CLUSTER — serialised (_cluster_lock): two same-story articles
            # clustering concurrently would both see "no neighbour" and seed
            # duplicate events.
            async with self._cluster_lock:
                cluster_result = await self.cluster.run(
                    article_id=article.id,
                    embedding=embedding,
                    entities=[e.model_dump() for e in enrichment.entities],
                    outlet_id=article.outlet.id,
                    language=article.language,
                    scraped_at=article.scraped_at,
                )

            # 3. SYNTHESIZE — only when the event has enough distinct sources
            # and only when source_count has grown since the last synthesis.
            if cluster_result.source_count >= self.cfg.clustering.min_sources_to_publish:
                page = await self._synthesize_once(
                    cluster_result.event_id, cluster_result.source_count
                )
                # 4. ILLUSTRATE — fire-and-forget background task; never blocks
                # the pipeline or the RabbitMQ ACK.  Skipped when synthesis
                # was a no-op (page is None → skipped / already in-flight).
                if page is not None:
                    asyncio.create_task(
                        self._illustrate_safe(cluster_result.event_id, page.headline)
                    )
                    asyncio.create_task(self._cover_safe(cluster_result.event_id))
            else:
                logger.info(
                    "Hold synthesize: event %s has %d/%d sources",
                    cluster_result.event_id,
                    cluster_result.source_count,
                    self.cfg.clustering.min_sources_to_publish,
                )

    # ──────────────────────────────────────── reenrich-missing ──────

    async def _run_reenrich(self, rows: list[dict[str, Any]], label: str) -> None:
        """Shared loop body for reenrich-missing and reenrich-stubs (ADR-0006 §D7).

        Runs the full ENRICH → EMBED → CLUSTER → SYNTHESIZE pipeline on each
        row with bounded concurrency. Aborts immediately on LlmQuotaError;
        other per-article errors are logged + skipped so one bad article never
        kills the rest.
        """
        total = len(rows)
        logger.info("%s: found %d articles to process", label, total)
        if not total:
            logger.info("%s: nothing to do.", label)
            return

        sem = asyncio.Semaphore(self.cfg.application.max_concurrent_articles)
        done = 0
        errors = 0
        quota_hit = False

        async def one(row: dict[str, Any]) -> None:
            nonlocal done, errors, quota_hit
            async with sem:
                if quota_hit:
                    return
                try:
                    await self._reenrich_article(row)
                    done += 1
                    if done % 50 == 0:
                        logger.info(
                            "%s progress: %d/%d done, %d errors",
                            label, done, total, errors,
                        )
                except LlmQuotaError:
                    quota_hit = True
                    raise
                except Exception:
                    logger.exception(
                        "%s: error on article %s — skipping",
                        label, row.get("id"),
                    )
                    errors += 1

        try:
            await asyncio.gather(*(one(r) for r in rows), return_exceptions=False)
        except LlmQuotaError:
            logger.critical(
                "Quota exhausted during %s (%d/%d done). "
                "Re-run when quota resets.",
                label, done, total,
            )
            return

        logger.info("%s complete: %d done, %d errors", label, done, errors)

    async def _reenrich_article(self, row: dict[str, Any]) -> None:
        """Enrich, embed, cluster, and optionally synthesize one unenriched article.

        The article is reconstructed from the raw DB row (body_text → text,
        outlet_id + outlet_name → _Outlet). Existing enrichment writes are
        overwritten so this is idempotent on re-run.
        """
        article = ArticleV1(
            id=row["id"],
            outlet=_Outlet(id=row["outlet_id"], name=row["outlet_name"]),
            url=row["url"],
            canonical_url=row.get("canonical_url"),
            title=row["title"],
            text=row["body_text"],
            language=row["language"],
            published_at=row.get("published_at"),
            scraped_at=row["scraped_at"],
            word_count=row["word_count"] or 0,
            # Restore Messor-provided classification signals so the LLM has them
            # as context hints during re-enrichment (same as the live pipeline).
            keywords=list(row["keywords_raw"] or []),
            meta_categories=list(row["meta_categories"] or []),
            category=row.get("article_category"),
        )

        # 1. ENRICH
        enrichment = await self.enrich.run(article)

        # 2. EMBED — serialised: CPU Ollama times out under concurrent load.
        async with self._embed_sem:
            embedding = await self.embed.embed(f"{article.title}\n\n{article.text[:4000]}")

        # 3. Write enrichment to DB
        await self.db.write_enrichment(
            article.id,
            theme=enrichment.theme,
            topic=enrichment.topic,
            sentiment=enrichment.sentiment,
            factuality=enrichment.factuality,
            summary_50w=enrichment.summary_50w,
            keywords_canonical=enrichment.keywords_canonical,
            embedding=embedding,
            entities=[e.model_dump() for e in enrichment.entities],
        )

        # 4. CLUSTER
        cluster_result = await self.cluster.run(
            article_id=article.id,
            embedding=embedding,
            entities=[e.model_dump() for e in enrichment.entities],
            outlet_id=article.outlet.id,
            language=article.language,
            scraped_at=article.scraped_at,
        )

        # 5. SYNTHESIZE if cluster has enough sources and a new source joined.
        if cluster_result.source_count >= self.cfg.clustering.min_sources_to_publish:
            page = await self._synthesize_once(
                cluster_result.event_id, cluster_result.source_count
            )
            if page is not None:
                asyncio.create_task(
                    self._illustrate_safe(cluster_result.event_id, page.headline)
                )
                asyncio.create_task(self._cover_safe(cluster_result.event_id))

        logger.info("reenriched %s (%s)", article.id, article.outlet.name)

    async def run_reenrich_missing(self) -> None:
        """Re-enrich articles already in the DB that are missing enrichment.

        Fetches articles where topic IS NULL AND body_text IS NOT NULL, then
        runs the full ENRICH → EMBED → CLUSTER → SYNTHESIZE pipeline on each
        with bounded concurrency via _run_reenrich (ADR-0006 §D7).

        On LlmQuotaError the batch is aborted immediately (quota is hard wall).
        Other per-article errors are logged + skipped so one bad article never
        kills the rest.
        """
        rows = await self.db.fetch_unenriched_articles()
        await self._run_reenrich(rows, "reenrich-missing")

    async def run_synthesize_pending(self, since_hours: int | None = None) -> None:
        """Synthesize events that have ≥2 sources but no published page yet.

        Useful after restarts (in-memory gate reset), when the synthesis trigger
        was missed during a bulk re-ingest, or after a re-cluster (ADR-0031) that
        unpublished events. ``since_hours`` scopes to the feed window so a bulk
        re-cluster only re-synthesizes events that will actually surface (keeps
        the run bounded — the unscoped version over thousands of split events is
        what got killed). Passes source_count=0 to bypass the source-count gate.
        """
        rows = await self.db.fetch_events_pending_synthesis(since_hours)
        total = len(rows)
        if not total:
            logger.info("synthesize-pending: no events to process")
            return
        logger.info("synthesize-pending: %d events to synthesize", total)
        done = errors = 0
        for row in rows:
            event_id = row["id"]
            source_count = row["source_count"]
            try:
                # Pass source_count=0 to bypass the in-memory gate — these
                # events were never synthesized so there is nothing to skip.
                await self._synthesize_once(event_id, 0)
                done += 1
                logger.info(
                    "synthesize-pending [%d/%d] event=%s sources=%d",
                    done, total, event_id, source_count,
                )
            except Exception as exc:  # noqa: BLE001
                errors += 1
                logger.error("synthesize-pending event=%s error: %s", event_id, exc)
        logger.info("synthesize-pending complete: %d done, %d errors", done, errors)

    async def run_reenrich_stubs(self) -> None:
        """Re-enrich articles that were processed in stub mode.

        Stub mode writes topic='General News' and keywords=['news','stub'].
        These articles have topic IS NOT NULL so --reenrich-missing misses them.
        This mode detects them via 'stub' = ANY(keywords_canonical) and runs the
        full ENRICH → EMBED → CLUSTER → SYNTHESIZE pipeline with the real LLM,
        overwriting the fake data.  Stub pages are overwritten by re-synthesis.
        See _run_reenrich for the shared loop body (ADR-0006 §D7).
        """
        rows = await self.db.fetch_stub_enriched_articles()
        await self._run_reenrich(rows, "reenrich-stubs")

    # ──────────────────────────────────────── conclude-stories (ADR-0013) ──

    async def run_conclude_stories(self) -> None:
        """Archive events that have gone quiet for conclude_after_days days.

        For each qualifying published event:
          1. Build arc_article_ids — all article IDs ordered by scraped_at
             (ordered pointers into articles.embedding, the story's vector
             trajectory through semantic space).
          2. INSERT into story_arcs (idempotent ON CONFLICT DO NOTHING).
          3. UPDATE events SET status = 'concluded'.

        Disabled when clustering.conclude_after_days == 0 (the default until the
        feature is validated with a paying user).  Safe to re-run: events that
        already have a story_arcs row are excluded by the DB query.
        """
        conclude_after = self.cfg.clustering.conclude_after_days
        if conclude_after <= 0:
            logger.info("conclude-stories: disabled (conclude_after_days=0)")
            return

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=conclude_after)
        candidates = await self.db.fetch_events_ready_to_conclude(cutoff)
        total = len(candidates)
        if not total:
            logger.info(
                "conclude-stories: no events older than %d days", conclude_after
            )
            return

        logger.info(
            "conclude-stories: %d event(s) to conclude (cutoff=%s)",
            total,
            cutoff.strftime("%Y-%m-%d"),
        )
        done = errors = 0
        for event in candidates:
            event_id = event["id"]
            try:
                articles = await self.db.get_event_articles_ordered(event_id)
                arc_ids = [a["id"] for a in articles]
                await self.db.create_story_arc(
                    {
                        "event_id":        event_id,
                        "topic":           event.get("topic"),
                        "language":        event["language"],
                        "first_seen_at":   event["first_seen_at"],
                        "concluded_at":    event["last_updated_at"],
                        "article_count":   len(articles),
                        "source_count":    event["source_count"],
                        "arc_article_ids": arc_ids,
                    }
                )
                await self.db.conclude_event(event_id)
                done += 1
                logger.info(
                    "conclude-stories [%d/%d] event=%s topic=%r articles=%d sources=%d arc_len=%d",
                    done, total, event_id,
                    event.get("topic"), len(articles),
                    event["source_count"], len(arc_ids),
                )
            except Exception as exc:  # noqa: BLE001
                errors += 1
                logger.error(
                    "conclude-stories event=%s error: %s", event_id, exc
                )

        logger.info(
            "conclude-stories complete: %d concluded, %d errors", done, errors
        )
