"""FastAPI surface — /healthz, /readyz, /status, /events, /events/{id}.

The reader (winston-r) will read from these endpoints in D4. For D2 they
are intentionally minimal.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.application import Application

logger = logging.getLogger(__name__)


def build_app(app: Application) -> FastAPI:
    api = FastAPI(title=f"{app.NAME} API", version=app.VERSION)

    api.add_middleware(
        CORSMiddleware,
        allow_origins=app.cfg.api.cors_allow_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @api.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "service": app.NAME, "version": app.VERSION}

    @api.get("/readyz")
    async def readyz() -> dict[str, Any]:
        db_ok = await app.db.healthcheck()
        if not db_ok:
            raise HTTPException(503, "database not ready")
        return {"ok": True, "checks": {"database": db_ok}}

    @api.get("/status")
    async def status() -> dict[str, Any]:
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            articles_total = await conn.fetchval("SELECT COUNT(*) FROM articles")
            articles_enriched = await conn.fetchval(
                "SELECT COUNT(*) FROM articles WHERE enriched_at IS NOT NULL"
            )
            events_total = await conn.fetchval("SELECT COUNT(*) FROM events")
            pages_published = await conn.fetchval(
                "SELECT COUNT(*) FROM pages"
            )
        return {
            "articles_total": articles_total,
            "articles_enriched": articles_enriched,
            "events_total": events_total,
            "pages_published": pages_published,
        }

    @api.get("/events")
    async def list_events(limit: int = 20) -> list[dict[str, Any]]:
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT p.id, p.headline, p.freshness_at, p.published_at,
                       e.source_count, e.article_count, e.topic, e.language
                  FROM pages p
                  JOIN events e ON e.id = p.event_id
                 ORDER BY p.freshness_at DESC NULLS LAST
                 LIMIT $1
                """,
                limit,
            )
        return [dict(r) for r in rows]

    @api.get("/outlets")
    async def list_outlets() -> list[dict[str, Any]]:
        return await app.db.get_outlets_with_stats()

    @api.get("/events/{event_id}")
    async def get_event(event_id: str) -> dict[str, Any]:
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                """
                SELECT p.*, e.source_count, e.article_count, e.topic
                  FROM pages p JOIN events e ON e.id = p.event_id
                 WHERE p.id = $1
                """,
                event_id,
            )
        if not row:
            raise HTTPException(404, f"event {event_id} not found")
        return dict(row)

    return api
