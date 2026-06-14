"""Postgres + pgvector — async via asyncpg.

Owns connection pooling, schema introspection (just an indicator we ran
the migration), and the small set of CRUD helpers the skills need.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg

from core.config import DbCfg

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


class DatabaseService:
    def __init__(self, cfg: DbCfg) -> None:
        self.cfg = cfg
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=self.cfg.url,
            min_size=self.cfg.pool_min,
            max_size=self.cfg.pool_max,
        )
        # Register vector codec on every new connection.
        await self._setup_vector_codec()
        await self._ensure_schema()
        logger.info("Postgres pool ready (min=%d max=%d)", self.cfg.pool_min, self.cfg.pool_max)

    async def _ensure_schema(self) -> None:
        """Apply each migration file when its guard says it's not yet applied.

        Two guard kinds:
          • table guard  — skip if a sentinel table already exists (DDL that
            creates a table). 001 → 'articles', 002 → 'outlets'.
          • predicate guard — skip if a SQL predicate already holds (DDL that
            alters an existing table). 003 → pages.published_at already nullable.
        Using `IF NOT EXISTS` / idempotent ALTERs in the SQL makes each file
        safe to re-run, but the guards avoid the churn on every boot.
        """
        # sentinel table for each numbered table-creating migration
        TABLE_GUARDS: dict[str, str] = {
            "001_initial_schema.sql":   "articles",
            "002_outlets_table.sql":    "outlets",
            "004_scrape_sessions.sql":  "scrape_sessions",
            # 010 creates story_arcs and extends the events status constraint.
            # Both the ALTER and CREATE are idempotent, but skip on warm boots.
            "010_story_arcs.sql":       "story_arcs",
        }
        # boolean SQL guard for each ALTER-style migration: TRUE → already applied
        ALTER_GUARDS: dict[str, str] = {
            # 003 makes pages.published_at nullable.
            "003_pages_moderation.sql": (
                "SELECT is_nullable = 'YES' FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'pages' "
                "AND column_name = 'published_at'"
            ),
            # 005 retypes articles.embedding vector(1536) → vector(1024)
            # (ADR-0003). TRUE once the column is already 1024-wide. COALESCE
            # guards a not-yet-created table (001 always runs first this boot).
            "005_embedding_dim_1024.sql": (
                "SELECT COALESCE("
                "(SELECT format_type(atttypid, atttypmod) = 'vector(1024)' "
                "FROM pg_attribute "
                "WHERE attrelid = to_regclass('public.articles') "
                "AND attname = 'embedding' AND NOT attisdropped), FALSE)"
            ),
            # 006 adds articles.content_hash. TRUE when the column exists.
            "006_article_content_hash.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'articles' "
                "AND column_name = 'content_hash')"
            ),
            # 007 adds theme, keywords_raw, meta_categories, article_category.
            # TRUE when articles.theme already exists.
            "007_article_theme_keywords.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'articles' "
                "AND column_name = 'theme')"
            ),
            # 008 adds lead_image, video_url. TRUE when articles.lead_image exists.
            "008_article_media.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'articles' "
                "AND column_name = 'lead_image')"
            ),
            # 009 adds pages.media_rail JSONB (IllustrateSkill Phase 2).
            "009_pages_media_rail.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'pages' "
                "AND column_name = 'media_rail')"
            ),
            # 012 adds outlets.feed_url TEXT (RSS-first harvesting, ADR-0015 follow-up).
            "012_outlet_feed_url.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'outlets' "
                "AND column_name = 'feed_url')"
            ),
            # 013 adds outlets.min_word_count INT (per-outlet word count threshold, P4).
            "013_outlet_min_word_count.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'outlets' "
                "AND column_name = 'min_word_count')"
            ),
            "014_breaking_news.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'events' "
                "AND column_name = 'breaking_at')"
            ),
            "015_events_synth_watermark.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'events' "
                "AND column_name = 'last_synth_source_count')"
            ),
            "016_scrape_session_lane.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'scrape_sessions' "
                "AND column_name = 'lane')"
            ),
            "017_triage_dropped_marker.sql": (
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'articles' "
                "AND column_name = 'triage_dropped_at')"
            ),
        }
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                guard_table = TABLE_GUARDS.get(sql_file.name)
                if guard_table:
                    exists = await conn.fetchval(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = $1)",
                        guard_table,
                    )
                    if exists:
                        continue
                alter_guard = ALTER_GUARDS.get(sql_file.name)
                if alter_guard:
                    already = await conn.fetchval(alter_guard)
                    if already:
                        continue
                logger.info("Applying migration %s", sql_file.name)
                await conn.execute(sql_file.read_text(encoding="utf-8"))
        logger.info("Schema up to date.")

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def _setup_vector_codec(self) -> None:
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute("SELECT 1")  # warm

    async def healthcheck(self) -> bool:
        if not self.pool:
            return False
        try:
            async with self.pool.acquire() as conn:
                v = await conn.fetchval("SELECT 1")
                return v == 1
        except Exception as e:
            logger.error("DB health check failed: %s", e)
            return False

    # ─────────────────────────────────────────── outlets ──────────
    async def seed_outlets(self, config_path: Path) -> int:
        """Seed outlets from outlets.json into the outlets table — only if empty.

        Seed-if-empty (ADR-0003): the Backoffice owns outlet *data* operations
        (create/update/delete via the Laravel admin), while Curator owns the
        table DDL and bootstraps the catalogue on a fresh/empty DB. A Curator
        restart must NOT overwrite admin edits, so when the `outlets` table
        already has rows we skip seeding entirely.

        Returns the number of rows seeded (0 if skipped or config missing).
        """
        import json as _json
        if not config_path.exists():
            logger.warning("outlets config not found at %s — skipping seed", config_path)
            return 0
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            existing = await conn.fetchval("SELECT count(*) FROM outlets")
        if existing and existing > 0:
            logger.info(
                "outlets table already has %d rows — skipping seed "
                "(Backoffice owns outlet data; ADR-0003)",
                existing,
            )
            return 0
        records = _json.loads(config_path.read_text(encoding="utf-8"))
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.executemany(
                """
                INSERT INTO outlets (id, name, display_name, url, region, language,
                                     vertical, active, priority)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO UPDATE SET
                    name         = EXCLUDED.name,
                    display_name = EXCLUDED.display_name,
                    url          = EXCLUDED.url,
                    region       = EXCLUDED.region,
                    language     = EXCLUDED.language,
                    vertical     = EXCLUDED.vertical,
                    active       = EXCLUDED.active,
                    priority     = EXCLUDED.priority,
                    updated_at   = NOW()
                """,
                [
                    (
                        r["id"], r["name"], r["display_name"], r["url"],
                        r.get("region", "global"), r.get("language", "en"),
                        r.get("vertical", "general"), r.get("active", True),
                        r.get("priority", 2),
                    )
                    for r in records
                ],
            )
        logger.info("Seeded %d outlets from %s", len(records), config_path.name)
        return len(records)

    # ─────────────────────────────────────────── curator settings ──
    async def fetch_curator_settings(self) -> dict[str, Any] | None:
        """Read the Backoffice-owned tunables row (read-only, schema-qualified).

        The Laravel Backoffice owns `backoffice.curator_settings` (ADR-0003);
        Curator only reads it. The table is schema-qualified because Curator's
        connection search_path is `public`. Returns None when the table or row
        is absent (fresh DB, or Backoffice migrations not yet run) so the
        caller falls back to env/YAML config.

        Curator never reads `backoffice.api_keys` — keys come from env (ADR-0004).
        """
        if not self.pool:
            return None
        try:
            async with self.pool.acquire() as conn:  # type: ignore[union-attr]
                row = await conn.fetchrow(
                    "SELECT * FROM backoffice.curator_settings ORDER BY id LIMIT 1"
                )
        except asyncpg.exceptions.UndefinedTableError:
            logger.info(
                "backoffice.curator_settings not present — using env/YAML config."
            )
            return None
        except asyncpg.exceptions.InvalidSchemaNameError:
            logger.info("backoffice schema absent — using env/YAML config.")
            return None
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("Could not read curator_settings (%s) — keeping current config.", e)
            return None
        return dict(row) if row else None

    async def embedding_column_dims(self) -> int | None:
        """Return the live width of articles.embedding (the vector(N) column).

        Used by the embedding-reconfigure dim guard (ADR-0004): a model whose
        vectors don't match this width must not be switched in live, as every
        INSERT would fail. Returns None if it can't be determined.
        """
        if not self.pool:
            return None
        try:
            async with self.pool.acquire() as conn:  # type: ignore[union-attr]
                t = await conn.fetchval(
                    "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                    "WHERE attrelid = to_regclass('public.articles') "
                    "AND attname = 'embedding' AND NOT attisdropped"
                )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("Could not read embedding column dims (%s).", e)
            return None
        if not t or not t.startswith("vector(") or not t.endswith(")"):
            return None
        try:
            return int(t[len("vector("):-1])
        except ValueError:
            return None

    async def fetch_unenriched_articles(self) -> list[dict[str, Any]]:
        """Fetch articles that have body_text but no enrichment (topic IS NULL).

        Used by `--reenrich-missing` to recover from quota-interrupted runs or
        to re-process articles that were ingested before Curator started.

        Returns a list of dicts with all columns needed to reconstruct an
        ArticleV1 and run the full ENRICH → CLUSTER → SYNTHESIZE pipeline.
        Returns [] if the pool is not initialised.
        """
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT id, outlet_id, outlet_name, url, canonical_url,
                       title, body_text, language, published_at,
                       scraped_at, word_count, spaces_key,
                       keywords_raw, meta_categories, article_category
                  FROM articles
                 WHERE topic IS NULL
                   AND body_text IS NOT NULL
                   AND triage_dropped_at IS NULL   -- ADR-0030: don't resurrect triage-dropped junk
                 ORDER BY scraped_at
                """
            )
        return [dict(r) for r in rows]

    async def mark_triage_dropped(self, article_id: str, reason: str) -> None:
        """Stamp an article as triage-dropped (ADR-0030 terminal marker).

        Set when the pre-enrich triage gate rejects an article so it carries a
        terminal state: excluded from the /status pending-enrichment counter and
        from --reenrich-missing (which keys on topic IS NULL). Best-effort —
        a failed mark only leaves the cosmetic counter drift, never blocks the ack.
        """
        if not self.pool:
            return
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "UPDATE articles SET triage_dropped_at = NOW(), triage_drop_reason = $2 "
                "WHERE id = $1",
                article_id, (reason or "")[:500],
            )

    async def fetch_stub_enriched_articles(self) -> list[dict[str, Any]]:
        """Fetch articles enriched in stub mode (keywords_canonical contains 'stub').

        Stub enrichment writes topic='General News', keywords=['news','stub'],
        entities=[{name:'Stubbed Entity'}].  These rows have topic IS NOT NULL so
        fetch_unenriched_articles() misses them.  Use this for `--reenrich-stubs`
        to overwrite fake data with a real LLM pass.
        """
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT id, outlet_id, outlet_name, url, canonical_url,
                       title, body_text, language, published_at,
                       scraped_at, word_count, spaces_key,
                       keywords_raw, meta_categories, article_category
                  FROM articles
                 WHERE 'stub' = ANY(keywords_canonical)
                   AND body_text IS NOT NULL
                 ORDER BY scraped_at
                """
            )
        return [dict(r) for r in rows]

    async def fetch_events_pending_synthesis(self) -> list[dict[str, Any]]:
        """Events that have ≥2 distinct sources but no published page yet.

        Used by ``--synthesize-pending`` to backfill synthesis for events that
        accumulated enough sources before the synthesis trigger was introduced,
        or that were skipped due to in-memory gate resets across restarts.

        Returns [{id, source_count}] ordered by source_count DESC so the
        richest events get synthesized first.
        """
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT e.id,
                       COUNT(DISTINCT a.outlet_id) AS source_count
                  FROM events e
                  JOIN articles a ON a.event_id = e.id
                 WHERE NOT EXISTS (
                         SELECT 1 FROM pages p WHERE p.event_id = e.id
                       )
                 GROUP BY e.id
                HAVING COUNT(DISTINCT a.outlet_id) >= 2
                 ORDER BY source_count DESC
                """
            )
        return [dict(r) for r in rows]

    async def fetch_articles_for_embedding(self, only_missing: bool) -> list[dict[str, Any]]:
        """Rows to (re-)embed. only_missing=True → just NULL embeddings;
        False → ALL articles with body_text (a full corpus re-embed).

        Two explicit query branches instead of f-string interpolation so each
        path is statically readable and safe for query-analysis tools (ADR-0006 §D8).
        """
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            if only_missing:
                rows = await conn.fetch(
                    "SELECT id, title, body_text FROM articles "
                    "WHERE embedding IS NULL AND body_text IS NOT NULL"
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, title, body_text FROM articles "
                    "WHERE body_text IS NOT NULL"
                )
        return [dict(r) for r in rows]

    async def set_article_embedding(self, article_id: str, vec: list[float]) -> None:
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "UPDATE articles SET embedding = $1::vector WHERE id = $2",
                "[" + ",".join(map(str, vec)) + "]", article_id,
            )

    # ─────────────────────────────────────────── model usage ──────
    async def record_model_usage(
        self,
        *,
        call_label: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        event_id: str | None = None,
    ) -> None:
        """Persist one completed LLM call into `backoffice.model_usage`.

        This is a DATA write to a Backoffice-DDL-owned table (ADR-0001/0003):
        Laravel owns the schema, Curator only INSERTs rows — the same
        cross-schema data-write pattern used for `public.outlets`. The table is
        schema-qualified because Curator's connection search_path is `public`.

        `created_at` is set here (NOW()) so the row carries the call's
        completion time even though the column also has a DB default.

        This helper deliberately does NOT swallow exceptions — the caller
        (CostMeter) wraps it so a logging/DB failure can never break the
        pipeline. Keeping the raise here lets the caller log the real cause.
        """
        if not self.pool:
            raise RuntimeError("DB pool not initialised")
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                INSERT INTO backoffice.model_usage
                    (call_label, model, input_tokens, output_tokens,
                     cost_usd, event_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                call_label, model, int(input_tokens), int(output_tokens),
                cost_usd, event_id,
            )

    # ─────────────────────────────────────────── moderation ────────
    # Curator owns all writes to public.pages / public.events (ADR-0003). The
    # Backoffice only issues RabbitMQ commands; these helpers perform the
    # actual mutation. Each returns True when a row was affected.
    async def set_page_published(self, page_id: str, *, published: bool) -> bool:
        """Publish (set published_at = NOW()) or unpublish (NULL) a page.

        Also keeps the parent event's status in sync: a published page → event
        'published'; an unpublished page → event 'draft' (unless already
        'dropped', which we leave alone — drop is a stronger, explicit state).
        """
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            async with conn.transaction():
                if published:
                    event_id = await conn.fetchval(
                        "UPDATE pages SET published_at = NOW() WHERE id = $1 "
                        "RETURNING event_id",
                        page_id,
                    )
                    if event_id is not None:
                        await conn.execute(
                            "UPDATE events SET status = 'published', "
                            "last_updated_at = NOW() WHERE id = $1",
                            event_id,
                        )
                else:
                    event_id = await conn.fetchval(
                        "UPDATE pages SET published_at = NULL WHERE id = $1 "
                        "RETURNING event_id",
                        page_id,
                    )
                    if event_id is not None:
                        await conn.execute(
                            "UPDATE events SET status = 'draft', "
                            "last_updated_at = NOW() WHERE id = $1 "
                            "AND status <> 'dropped'",
                            event_id,
                        )
        return event_id is not None

    async def drop_page(self, page_id: str) -> bool:
        """Drop a page: unpublish it (published_at = NULL) and mark its event
        'dropped'. No hard delete — the row is retained so it can be revived
        (re-publish / re-synthesize). Returns True if the page existed.
        """
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            async with conn.transaction():
                event_id = await conn.fetchval(
                    "UPDATE pages SET published_at = NULL WHERE id = $1 "
                    "RETURNING event_id",
                    page_id,
                )
                if event_id is not None:
                    await conn.execute(
                        "UPDATE events SET status = 'dropped', "
                        "last_updated_at = NOW() WHERE id = $1",
                        event_id,
                    )
        return event_id is not None

    async def set_event_breaking(self, event_id: str, *, ttl_hours: int = 2) -> bool:
        """Manually flag an event breaking (ADR-0029 manual gate).

        Sets breaking_at = NOW(), breaking_until = NOW() + ttl_hours. Mirrors the
        auto-detector's columns (ADR-0024) but editor-triggered, so it fires
        regardless of pulse-outlet velocity. Returns True if the event exists.
        """
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchval(
                "UPDATE events SET breaking_at = NOW(), "
                "breaking_until = NOW() + ($2 || ' hours')::interval "
                "WHERE id = $1 RETURNING id",
                event_id, str(int(ttl_hours)),
            )
        return row is not None

    async def clear_event_breaking(self, event_id: str) -> bool:
        """Clear an event's breaking flag (NULL breaking_at/until)."""
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchval(
                "UPDATE events SET breaking_at = NULL, breaking_until = NULL "
                "WHERE id = $1 RETURNING id",
                event_id,
            )
        return row is not None

    async def write_media_rail(self, event_id: str, items: list[dict[str, Any]]) -> None:
        """Persist IllustrateSkill results to pages.media_rail (migration 009).

        Overwrites any existing rail for the event.  Writing an empty list []
        is valid — it clears a stale rail after a re-synthesis.
        No-op if the page row doesn't exist yet (synthesis not yet complete).
        """
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "UPDATE pages SET media_rail = $2::jsonb WHERE id = $1",
                event_id,
                json.dumps(items),
            )

    async def write_hero_image(self, event_id: str, url: str) -> None:
        """Persist the best YouTube thumbnail to events.hero_image (ADR-0016).

        Used by IllustrateSkill as a story-relevant fallback for events whose
        outlet og:image was NULL, hotlink-blocked, or an author headshot.
        Overwrites any prior value — re-synthesis may yield a better video.
        """
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "UPDATE events SET hero_image = $1 WHERE id = $2",
                url, event_id,
            )

    async def get_last_synth_source_count(self, event_id: str) -> int:
        """Distinct-outlet count at the event's last synthesis (migration 015).

        Persistent replacement for the in-memory _last_synth_source_count dict
        that was wiped on every restart and caused post-deploy synthesis storms.
        """
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            val = await conn.fetchval(
                "SELECT last_synth_source_count FROM events WHERE id = $1",
                event_id,
            )
            return int(val or 0)

    async def set_last_synth_source_count(self, event_id: str, count: int) -> None:
        """Record the source_count at the moment synthesis completed."""
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "UPDATE events SET last_synth_source_count = $2 WHERE id = $1",
                event_id, count,
            )

    async def get_outlets_with_stats(self) -> list[dict[str, Any]]:
        """Return all outlets joined with live article/event stats from the DB."""
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT
                    o.id, o.name, o.display_name, o.url,
                    o.region, o.language, o.vertical,
                    o.active, o.priority,
                    o.feed_url,
                    o.min_word_count,
                    o.pulse,
                    COUNT(a.id)              AS article_count,
                    MAX(a.scraped_at)        AS last_seen,
                    COUNT(DISTINCT a.event_id)
                        FILTER (WHERE a.event_id IS NOT NULL)
                                             AS events_contributed
                FROM outlets o
                LEFT JOIN articles a ON a.outlet_id = o.id
                GROUP BY o.id, o.name, o.display_name, o.url,
                         o.region, o.language, o.vertical, o.active, o.priority,
                         o.feed_url, o.min_word_count, o.pulse
                ORDER BY o.priority ASC, o.display_name ASC
                """
            )
        return [dict(r) for r in rows]

    # ─────────────────────────────────────────── scrape sessions ──
    async def upsert_scrape_session(
        self,
        *,
        session_id: str,
        started_at: str | None,
        ended_at: str | None,
        total_articles: int,
        successful_articles: int,
        failed_articles: int,
        duplicates_total: int,
        success_rate: float,
        duration_seconds: float | None,
        outlets: list[dict[str, Any]],
        total_outlets: int,
        lane: str = "cycle",
    ) -> None:
        """Persist one Messor harvest run into `public.scrape_sessions` (B12.1).

        Keyed by `session_id` (a stable run id) with ON CONFLICT DO UPDATE so a
        re-emitted session refreshes the existing row instead of duplicating it
        (Messor may re-publish if an outlet completes late, or a run replays).

        This is a DATA write to a Curator-owned table (ADR-0006): Messor stays
        Postgres-free and only EMITS the event; Curator owns the DDL + write.
        The caller (`_handle_scrape_session`) wraps this defensively so a DB
        hiccup can never wedge the consumer.
        """
        if not self.pool:
            raise RuntimeError("DB pool not initialised")
        # asyncpg pre-encodes params against the column type, so a `::timestamptz`
        # cast in SQL won't rescue an ISO *string* — parse to datetime here.
        started_dt = _parse_ts(started_at)
        ended_dt = _parse_ts(ended_at)
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                INSERT INTO scrape_sessions
                    (session_id, started_at, ended_at, total_articles,
                     successful_articles, failed_articles, duplicates_total,
                     success_rate, duration_seconds, outlets, total_outlets,
                     lane, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11,$12,NOW(),NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    started_at          = EXCLUDED.started_at,
                    ended_at            = EXCLUDED.ended_at,
                    total_articles      = EXCLUDED.total_articles,
                    successful_articles = EXCLUDED.successful_articles,
                    failed_articles     = EXCLUDED.failed_articles,
                    duplicates_total    = EXCLUDED.duplicates_total,
                    success_rate        = EXCLUDED.success_rate,
                    duration_seconds    = EXCLUDED.duration_seconds,
                    outlets             = EXCLUDED.outlets,
                    total_outlets       = EXCLUDED.total_outlets,
                    lane                = EXCLUDED.lane,
                    updated_at          = NOW()
                """,
                session_id, started_dt, ended_dt, int(total_articles),
                int(successful_articles), int(failed_articles),
                int(duplicates_total), float(success_rate), duration_seconds,
                json.dumps(outlets or []), int(total_outlets),
                (lane if lane in ("pulse", "cycle") else "cycle"),
            )

    # ─────────────────────────────────────────── article CRUD ──────
    async def upsert_article_raw(self, art: dict[str, Any], spaces_key: str | None) -> bool:
        """Insert the article shell (Messor's v1 fields). Enrichment fills the rest later.

        Content-change detection (migration 006; hash strategy ADR-0018):
          - content_hash = _content_hash(title, body_text) is stored on first
            insert. It is a NORMALIZED PREFIX hash (lowercase + collapsed
            whitespace + first _HASH_PREFIX_CHARS of body), NOT a raw byte hash —
            see _content_hash() for why. This is what makes the ADR-0015
            duplicate fast-path actually fire on re-scrapes.
          - On re-scrape of the same URL (same id), the ON CONFLICT clause
            updates the body and RESETS all enrichment fields (topic, embedding,
            etc.) **only when the hash changes**.  Unchanged content → no-op.
          - Resetting to NULL causes the normal ENRICH→CLUSTER→SYNTHESIZE path
            to re-process the updated article, so synthesized pages reflect the
            latest content rather than the stale original.

        spaces_key is NULL when the article arrived inline via RabbitMQ before
        the S3 archive step completed. That is the normal v0 path.

        Returns:
            True  — article is new or content changed; full ENRICH→CLUSTER pipeline needed.
            False — content unchanged and enriched_at already set; caller can skip
                    the LLM pipeline entirely (ADR-0015 duplicate fast-path).
        """
        # PERF-REVIEW (checkpoint/content-aware-dedup, 2026-06-06): hash computed
        # on every upsert — negligible CPU, but the ON CONFLICT DO UPDATE WHERE
        # clause now rewrites and resets enrichment on content change.  Fine at
        # current volume; revisit if DB write contention appears.
        # Fast revert: git revert 428270e (restores ON CONFLICT DO NOTHING).
        #
        # ADR-0018: hash a NORMALIZED PREFIX, not the raw title+body. The raw
        # hash changed on nearly every re-scrape (newspaper3k boilerplate jitter)
        # so the ADR-0015 fast-path never fired and every re-scrape paid for a
        # full LLM re-enrichment. _content_hash() collapses whitespace/case and
        # hashes only the stable lede prefix.
        content_hash = _content_hash(art["title"], art.get("text") or "")

        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                INSERT INTO articles (id, outlet_id, outlet_name, url, canonical_url,
                                      title, body_text, language, published_at,
                                      scraped_at, word_count, spaces_key, raw_meta,
                                      content_hash,
                                      keywords_raw, meta_categories, article_category,
                                      lead_image, video_url)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
                ON CONFLICT (id) DO UPDATE SET
                    -- Content fields: overwrite with the freshest scrape.
                    title            = EXCLUDED.title,
                    body_text        = EXCLUDED.body_text,
                    content_hash     = EXCLUDED.content_hash,
                    scraped_at       = EXCLUDED.scraped_at,
                    word_count       = EXCLUDED.word_count,
                    -- Messor-provided classification signals (refresh on re-scrape).
                    keywords_raw     = EXCLUDED.keywords_raw,
                    meta_categories  = EXCLUDED.meta_categories,
                    article_category = EXCLUDED.article_category,
                    -- Media (refresh on re-scrape — og:image may update).
                    lead_image       = EXCLUDED.lead_image,
                    video_url        = EXCLUDED.video_url,
                    -- Reset enrichment so the pipeline re-processes fresh content.
                    enriched_at          = NULL,
                    topic                = NULL,
                    theme                = NULL,
                    sentiment            = NULL,
                    factuality           = NULL,
                    summary_50w          = NULL,
                    keywords_canonical   = NULL,
                    embedding            = NULL,
                    -- Reset cluster assignment so the article re-enters CLUSTER
                    -- with a clean slate.  Invariant: event_id IS NOT NULL ↔
                    -- embedding IS NOT NULL (ADR-0006 §D4).
                    event_id             = NULL,
                    cluster_distance     = NULL
                WHERE articles.content_hash IS DISTINCT FROM EXCLUDED.content_hash
                """,
                art["id"],
                art["outlet"]["id"],
                art["outlet"]["name"],
                art["url"],
                art.get("canonical_url"),
                art["title"],
                art["text"],
                art["language"],
                art.get("published_at"),
                art["scraped_at"],
                art["word_count"],
                spaces_key or None,
                json.dumps(art.get("metadata") or {}),
                content_hash,
                art.get("keywords") or [],
                art.get("meta_categories") or [],
                art.get("category"),
                art.get("lead_image"),
                art.get("video_url"),
            )
            # Separate SELECT so we always read the current state regardless of
            # whether the upsert above actually wrote anything.  (PostgreSQL's
            # ON CONFLICT DO UPDATE … WHERE returns nothing via RETURNING when
            # the WHERE clause is false — i.e. content unchanged — making a
            # single-query approach unreliable for the fast-path check.)
            row = await conn.fetchrow(
                "SELECT enriched_at FROM articles WHERE id = $1", art["id"]
            )
        # enriched_at IS NOT NULL  → content unchanged, enrichment still valid → fast-path.
        # enriched_at IS NULL      → new article or content changed → needs full pipeline.
        needs_enrichment = row is None or row["enriched_at"] is None
        return needs_enrichment

    async def write_enrichment(
        self,
        article_id: str,
        *,
        theme: str,
        topic: str,
        sentiment: str,
        factuality: float,
        summary_50w: str,
        keywords_canonical: list[str],
        embedding: list[float],
        entities: list[dict[str, Any]],
    ) -> None:
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE articles
                       SET enriched_at = NOW(),
                           theme = $2, topic = $3, sentiment = $4, factuality = $5,
                           summary_50w = $6, keywords_canonical = $7,
                           embedding = $8
                     WHERE id = $1
                    """,
                    article_id, theme, topic, sentiment, factuality,
                    summary_50w, keywords_canonical, _vector_literal(embedding),
                )
                await conn.execute("DELETE FROM entities WHERE article_id = $1", article_id)
                if entities:
                    await conn.executemany(
                        """
                        INSERT INTO entities (article_id, name, type, salience)
                        VALUES ($1, $2, $3, $4)
                        """,
                        [(article_id, e["name"], e["type"], e.get("salience", 0.5)) for e in entities],
                    )


    # ──────────────────────────────────────────────── story arcs (ADR-0013) ──

    async def fetch_events_ready_to_conclude(
        self, cutoff: "datetime",
    ) -> list[dict[str, Any]]:
        """Return published events whose last_updated_at is older than *cutoff*.

        Only events that do not yet have a story_arcs row are returned so the
        job is safely re-runnable (idempotent).
        """
        rows = await self.pool.fetch(  # type: ignore[union-attr]
            """
            SELECT e.id, e.topic, e.language, e.first_seen_at,
                   e.last_updated_at, e.article_count, e.source_count
              FROM events e
             WHERE e.status = 'published'
               AND e.last_updated_at < $1
               AND NOT EXISTS (
                   SELECT 1 FROM story_arcs sa WHERE sa.event_id = e.id
               )
             ORDER BY e.last_updated_at ASC
            """,
            cutoff,
        )
        return [dict(r) for r in rows]

    async def get_event_articles_ordered(
        self, event_id: str,
    ) -> list[dict[str, Any]]:
        """Return article IDs for *event_id* ordered by scraped_at ASC.

        Used to build arc_article_ids — the ordered pointer list into
        articles.embedding that forms the story's vector trajectory.
        """
        rows = await self.pool.fetch(  # type: ignore[union-attr]
            """
            SELECT id
              FROM articles
             WHERE event_id = $1
             ORDER BY scraped_at ASC
            """,
            event_id,
        )
        return [dict(r) for r in rows]

    async def create_story_arc(self, arc: dict[str, Any]) -> None:
        """Insert a story_arcs row (ON CONFLICT DO NOTHING — idempotent)."""
        await self.pool.execute(  # type: ignore[union-attr]
            """
            INSERT INTO story_arcs
                (event_id, topic, language, first_seen_at, concluded_at,
                 article_count, source_count, arc_article_ids)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (event_id) DO NOTHING
            """,
            arc["event_id"],
            arc.get("topic"),
            arc["language"],
            arc["first_seen_at"],
            arc["concluded_at"],
            arc["article_count"],
            arc["source_count"],
            arc["arc_article_ids"],
        )

    async def conclude_event(self, event_id: str) -> None:
        """Mark an event as 'concluded' (terminal state — no further transitions)."""
        await self.pool.execute(  # type: ignore[union-attr]
            """
            UPDATE events
               SET status = 'concluded',
                   last_updated_at = NOW()
             WHERE id = $1
               AND status = 'published'
            """,
            event_id,
        )


# ─────────────────────────────────────── content fingerprint (ADR-0018) ──
# The duplicate fast-path (ADR-0015) keys off content_hash: an unchanged
# re-scrape must produce the SAME hash so enrichment is preserved and the LLM
# pipeline is skipped. The old hash (raw MD5(title + body_text)) was unstable —
# newspaper3k yields slightly different body_text on every scrape of the same
# URL, so the hash changed on nearly every re-scrape and the fast-path NEVER
# fired (observed 0 SKIP / 176 ENRICH). ADR-0018 documents the fix below.
_HASH_PREFIX_CHARS = 500          # normalized body chars that feed the hash
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_for_hash(text: str) -> str:
    """Canonicalise text for the content fingerprint.

    Lowercase, then collapse every whitespace run (spaces, tabs, newlines) to a
    single space and strip the ends. This removes the formatting jitter
    newspaper3k introduces between scrapes (re-indentation, extra blank lines,
    case flips in re-rendered headers) so cosmetically-identical content hashes
    identically.
    """
    return _WHITESPACE_RE.sub(" ", text or "").strip().lower()


def _content_hash(title: str, body: str) -> str:
    """Stable content fingerprint resistant to re-scrape noise (ADR-0018).

    newspaper3k yields slightly different ``body_text`` on each scrape of the
    same URL — trailing boilerplate ("N min read"), related-links blocks, share
    widgets, and dynamic view/comment counts churn the *tail* of the
    extraction. Hashing the raw ``title + body_text`` therefore changed on
    nearly every re-scrape, defeating the ADR-0015 duplicate fast-path (every
    re-scrape looked "changed" → a full, paid LLM re-enrichment).

    Strategy — hash a NORMALIZED PREFIX:
      • normalize → lowercase + collapse all whitespace to single spaces
        (kills indentation/newline jitter and case flips)
      • prefix    → only the first ``_HASH_PREFIX_CHARS`` of the normalized body
        (the substantive lede is stable across scrapes; the volatile boilerplate
        is appended at the END of the extraction, beyond the prefix window, so
        it never moves the hash). News ledes comfortably exceed 500 chars, so
        for real articles the boilerplate is always outside the window.

    A genuine edit to the headline or lede still lands inside the window and
    changes the hash, so material content changes still trigger re-enrichment.
    """
    norm_title = _normalize_for_hash(title)
    norm_body = _normalize_for_hash(body)[:_HASH_PREFIX_CHARS]
    return hashlib.md5(f"{norm_title}\n{norm_body}".encode("utf-8")).hexdigest()


def _vector_literal(v: list[float]) -> str:
    """asyncpg has no native vector type; pgvector accepts text literal `[…]`."""
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def _parse_ts(value: Any):
    """Coerce an ISO-8601 string (or datetime/None) to a datetime for asyncpg.

    asyncpg encodes a timestamptz param against the column type *before* any
    SQL-level cast runs, so a bare ISO string raises. Handles a trailing 'Z'
    (Python <3.11 fromisoformat rejects it). Returns None on empty/unparseable
    input so the column stays NULL rather than failing the whole upsert.
    """
    if value is None or isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None
