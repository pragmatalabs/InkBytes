#!/usr/bin/env python
"""Backfill events.centroid = avg(member embeddings) — ADR-0031.

Centroid-linkage's candidate query (`_run_precision`) skips events whose centroid
is NULL, so existing events must be seeded BEFORE `clustering.precision_mode` is
flipped on (otherwise new articles can't attach to them and the corpus fragments).
One pgvector aggregate per event; idempotent — fills only NULL centroids unless
--all is passed (e.g. to refresh after a re-cluster).

Run inside the Curator container:
  docker exec inkbytes-curator-worker python scripts/backfill_event_centroids.py
  docker exec inkbytes-curator-worker python scripts/backfill_event_centroids.py --all
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import CuratorConfig  # noqa: E402
from services.database_service import DatabaseService  # noqa: E402


async def _run(config_path: str, do_all: bool) -> int:
    db = DatabaseService(CuratorConfig.load(config_path).database)
    await db.connect()  # applies migration 019
    try:
        async with db.pool.acquire() as c:
            where = "" if do_all else "AND e.centroid IS NULL"
            todo = await c.fetchval(
                f"SELECT count(*) FROM events e WHERE 1=1 {where}")
            print(f"[backfill] {todo} events to set centroid (mode={'ALL' if do_all else 'NULL-only'})")
            # Single set-based UPDATE; avg() is a pgvector aggregate.
            res = await c.execute(
                f"""
                UPDATE events e
                   SET centroid = sub.c
                  FROM (SELECT event_id, avg(embedding) AS c
                          FROM articles
                         WHERE event_id IS NOT NULL AND embedding IS NOT NULL
                         GROUP BY event_id) sub
                 WHERE e.id = sub.event_id {where}
                """)
            filled = await c.fetchval("SELECT count(*) FROM events WHERE centroid IS NOT NULL")
            print(f"[backfill] done ({res}); events with centroid now: {filled}")
        return 0
    finally:
        await db.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="env.yaml")
    ap.add_argument("--all", action="store_true", help="recompute every centroid (else NULL-only)")
    args = ap.parse_args()
    sys.exit(asyncio.run(_run(args.config, args.all)))


if __name__ == "__main__":
    main()
