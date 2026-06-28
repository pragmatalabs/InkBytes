"""Postgres access for the Editorial service (asyncpg).

Reads Curator's published `pages`/`events`; writes the `editorials` table. Applies
its own migration on connect (idempotent, IF NOT EXISTS).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import asyncpg

from core.config import DbCfg

logger = logging.getLogger(__name__)
_MIGRATIONS = Path(__file__).resolve().parent.parent / "db" / "migrations"


class Database:
    def __init__(self, cfg: DbCfg) -> None:
        self.cfg = cfg
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=self.cfg.url, min_size=self.cfg.pool_min, max_size=self.cfg.pool_max)
        async with self.pool.acquire() as conn:
            for sql in sorted(_MIGRATIONS.glob("*.sql")):
                await conn.execute(sql.read_text(encoding="utf-8"))
        logger.info("Editorial DB ready (pool %d-%d)", self.cfg.pool_min, self.cfg.pool_max)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def fetch_theme_events(
        self, theme: str, window_hours: int, limit: int) -> list[dict[str, Any]]:
        """The theme's recent published events (richest first) — the editorial's
        raw material. Event theme = majority article theme of its cluster."""
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT p.id AS event_id, p.headline,
                       LEFT(p.synthesis_md, 360) AS excerpt,
                       e.source_count
                  FROM pages p
                  JOIN events e ON e.id = p.event_id
                  JOIN LATERAL (
                       SELECT a.theme FROM articles a
                        WHERE a.event_id = e.id AND a.theme IS NOT NULL
                        GROUP BY a.theme ORDER BY count(*) DESC LIMIT 1
                  ) th ON true
                 WHERE p.published_at IS NOT NULL AND e.status = 'published'
                   AND p.freshness_at > NOW() - ($1 || ' hours')::interval
                   AND th.theme = $2
                 ORDER BY e.source_count DESC, p.freshness_at DESC
                 LIMIT $3
                """,
                str(window_hours), theme, limit)
        return [dict(r) for r in rows]

    async def write_editorial(self, *, ed_id: str, theme: str, language: str,
                              edition_date, persona: str, headline: str, body_md: str,
                              event_ids: list[str], model: str,
                              input_context: list[dict], prompt: str) -> None:
        """Upsert the day's editorial for (theme, language, edition_date) — a
        re-run replaces it. Carries the full generation provenance (input_context
        + prompt) so the table doubles as the Phase-2 SLM training set."""
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                INSERT INTO editorials (id, theme, language, edition_date, persona,
                       headline, body_md, event_ids, model, input_context, prompt)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11)
                ON CONFLICT (theme, language, edition_date) DO UPDATE
                  SET persona=EXCLUDED.persona, headline=EXCLUDED.headline,
                      body_md=EXCLUDED.body_md, event_ids=EXCLUDED.event_ids,
                      model=EXCLUDED.model, input_context=EXCLUDED.input_context,
                      prompt=EXCLUDED.prompt, created_at=NOW()
                """,
                ed_id, theme, language, edition_date, persona, headline, body_md,
                event_ids, model, json.dumps(input_context), prompt)
