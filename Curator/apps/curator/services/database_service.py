"""Postgres + pgvector — async via asyncpg.

Owns connection pooling, schema introspection (just an indicator we ran
the migration), and the small set of CRUD helpers the skills need.
"""
from __future__ import annotations

import json
import logging
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
                       scraped_at, word_count, spaces_key
                  FROM articles
                 WHERE topic IS NULL
                   AND body_text IS NOT NULL
                 ORDER BY scraped_at
                """
            )
        return [dict(r) for r in rows]

    async def fetch_articles_for_embedding(self, only_missing: bool) -> list[dict[str, Any]]:
        """Rows to (re-)embed. only_missing=True → just NULL embeddings;
        False → ALL articles with body_text (a full corpus re-embed)."""
        if not self.pool:
            return []
        where = "embedding IS NULL AND " if only_missing else ""
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                f"SELECT id, title, body_text FROM articles "
                f"WHERE {where}body_text IS NOT NULL"
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

    async def get_outlets_with_stats(self) -> list[dict[str, Any]]:
        """Return all outlets joined with live article/event stats from the DB."""
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT
                    o.id, o.name, o.display_name, o.url,
                    o.region, o.language, o.vertical,
                    o.active, o.priority,
                    COUNT(a.id)              AS article_count,
                    MAX(a.scraped_at)        AS last_seen,
                    COUNT(DISTINCT a.event_id)
                        FILTER (WHERE a.event_id IS NOT NULL)
                                             AS events_contributed
                FROM outlets o
                LEFT JOIN articles a ON a.outlet_id = o.id
                GROUP BY o.id, o.name, o.display_name, o.url,
                         o.region, o.language, o.vertical, o.active, o.priority
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
                     created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11,NOW(),NOW())
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
                    updated_at          = NOW()
                """,
                session_id, started_dt, ended_dt, int(total_articles),
                int(successful_articles), int(failed_articles),
                int(duplicates_total), float(success_rate), duration_seconds,
                json.dumps(outlets or []), int(total_outlets),
            )

    # ─────────────────────────────────────────── article CRUD ──────
    async def upsert_article_raw(self, art: dict[str, Any], spaces_key: str | None) -> None:
        """Insert the article shell (Messor's v1 fields). Enrichment fills the rest later.

        spaces_key is NULL when the article arrived inline via RabbitMQ before
        the S3 archive step completed. That is the normal v0 path.
        """
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                INSERT INTO articles (id, outlet_id, outlet_name, url, canonical_url,
                                      title, body_text, language, published_at,
                                      scraped_at, word_count, spaces_key, raw_meta)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (id) DO NOTHING
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
                spaces_key or None,  # "" → NULL; real S3 key passes through
                json.dumps(art.get("metadata") or {}),
            )

    async def write_enrichment(
        self,
        article_id: str,
        *,
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
                           topic = $2, sentiment = $3, factuality = $4,
                           summary_50w = $5, keywords_canonical = $6,
                           embedding = $7
                     WHERE id = $1
                    """,
                    article_id, topic, sentiment, factuality,
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
