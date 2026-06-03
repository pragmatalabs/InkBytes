"""Postgres + pgvector — async via asyncpg.

Owns connection pooling, schema introspection (just an indicator we ran
the migration), and the small set of CRUD helpers the skills need.
"""
from __future__ import annotations

import json
import logging
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
        """Apply each migration file when its sentinel table is absent.

        Guards per migration:
          001 → 'articles' table
          002 → 'outlets' table
        Using `IF NOT EXISTS` in the SQL makes each file idempotent if
        re-run (e.g. after a manual partial apply).
        """
        # sentinel table for each numbered migration
        GUARDS: dict[str, str] = {
            "001_initial_schema.sql": "articles",
            "002_outlets_table.sql":  "outlets",
        }
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                guard_table = GUARDS.get(sql_file.name)
                if guard_table:
                    exists = await conn.fetchval(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = $1)",
                        guard_table,
                    )
                    if exists:
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
