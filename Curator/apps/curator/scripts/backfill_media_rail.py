#!/usr/bin/env python
"""One-time backfill: re-run IllustrateSkill on published pages with an empty
media_rail (ADR-0011).

During the 2026-06-25 Chromium PID-leak outage (see ADR-0011 addendum) every
illustration produced 0 video items, so events synthesized in the outage window
have `media_rail = []` and show no videos. Now that the leak is fixed
(init:true + pids_limit), this re-illustrates those pages so the current feed
gets videos without waiting for them to age out.

Mirrors the live trigger exactly: `IllustrateSkill.run(page_id, headline)`
(pages.id == event_id; the skill persists media_rail + the hero fallback itself).
Runs **sequentially** — one Chromium pair at a time, same as the Semaphore(1)
gate in production — so it can't re-trigger the resource pressure.

Dry-run by default (lists candidates). Pass --apply to actually illustrate.

Run inside the Curator worker container (has Chromium + env.yaml + DB):
  docker exec inkbytes-curator-worker python scripts/backfill_media_rail.py --since 2026-06-20
  docker exec inkbytes-curator-worker python scripts/backfill_media_rail.py --since 2026-06-20 --limit 150 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import CuratorConfig  # noqa: E402
from services.database_service import DatabaseService  # noqa: E402
from skills.illustrate import IllustrateSkill  # noqa: E402


async def _run(config_path: str, since: str, limit: int, apply: bool) -> int:
    # asyncpg binds a timestamptz param from a datetime, not a str.
    since_dt = datetime.fromisoformat(since)
    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=timezone.utc)
    cfg = CuratorConfig.load(config_path)
    db = DatabaseService(cfg.database)
    await db.connect()
    try:
        rows = await db.pool.fetch(
            """
            SELECT id, headline
              FROM pages
             WHERE published_at IS NOT NULL
               AND freshness_at >= $1
               AND (media_rail IS NULL OR media_rail::text IN ('[]', 'null'))
             ORDER BY freshness_at DESC
             LIMIT $2
            """,
            since_dt, limit,
        )
        print(f"[backfill] {len(rows)} published pages with empty media_rail "
              f"since {since} (mode={'APPLY' if apply else 'dry-run'}, limit={limit})")
        if not apply:
            for r in rows[:30]:
                print(f"  - {r['id']}  {r['headline'][:70]}")
            if len(rows) > 30:
                print(f"  … and {len(rows) - 30} more")
            print("[backfill] dry-run — pass --apply to illustrate.")
            return 0

        illustrate = IllustrateSkill(db)
        filled = 0
        empty = 0
        for i, r in enumerate(rows, 1):
            try:
                items = await illustrate.run(r["id"], r["headline"])
                n = len(items)
                filled += 1 if n else 0
                empty += 0 if n else 1
                print(f"[backfill] {i}/{len(rows)} {r['id']} → {n} videos | {r['headline'][:55]}")
            except Exception as e:  # never abort the whole run on one page
                empty += 1
                print(f"[backfill] {i}/{len(rows)} {r['id']} → ERROR {repr(e)[:100]}")
        print(f"[backfill] done — {filled} pages got videos, {empty} stayed empty "
              f"(no relevant YouTube match), of {len(rows)} processed.")
        return 0
    finally:
        await db.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="env.yaml")
    ap.add_argument("--since", default="2026-06-20",
                    help="Only re-illustrate pages with freshness_at >= this (outage window).")
    ap.add_argument("--limit", type=int, default=150,
                    help="Max pages to process (newest-first, i.e. the visible feed).")
    ap.add_argument("--apply", action="store_true", help="Actually illustrate (else dry-run).")
    args = ap.parse_args()
    sys.exit(asyncio.run(_run(args.config, args.since, args.limit, args.apply)))


if __name__ == "__main__":
    main()
