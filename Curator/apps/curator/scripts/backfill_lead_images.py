#!/usr/bin/env python
"""One-time backfill: NULL out hotlink-blocked lead_image URLs already in the DB.

The ADR-0019 guard only validates og:images at *ingest*, so rows stored before
the guard shipped keep their blocked URLs until the article is next re-scraped.
This script re-probes every distinct `articles.lead_image` with the browser
fingerprint (same MediaValidator the ingest path uses) and NULLs the blocked
ones, so already-published events get a correct cover (the /events rollup falls
back to another source's image) without waiting for a re-scrape.

Dry-run by default — prints what it *would* change. Pass --apply to write.

Run inside the Curator container (has env.yaml + DATABASE_URL + httpx):
  docker exec inkbytes-curator-worker python scripts/backfill_lead_images.py
  docker exec inkbytes-curator-worker python scripts/backfill_lead_images.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg  # noqa: E402

from core.config import CuratorConfig  # noqa: E402
from services.media_validation import MediaValidator  # noqa: E402

CONCURRENCY = 8


async def _run(config_path: str, apply: bool) -> int:
    cfg = CuratorConfig.load(config_path)
    validator = MediaValidator(
        enabled=True, timeout_s=cfg.application.lead_image_probe_timeout_s
    )
    conn = await asyncpg.connect(cfg.database.url)
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT lead_image
              FROM articles
             WHERE lead_image IS NOT NULL AND lead_image <> ''
            """
        )
        urls = [r["lead_image"] for r in rows]
        print(f"[backfill] {len(urls)} distinct lead_image URLs to probe "
              f"(mode={'APPLY' if apply else 'dry-run'})")

        sem = asyncio.Semaphore(CONCURRENCY)

        async def probe(url: str) -> tuple[str, bool]:
            async with sem:
                return url, await validator.is_displayable(url)

        results = await asyncio.gather(*(probe(u) for u in urls))
        blocked = [u for u, ok in results if not ok]

        print(f"[backfill] displayable={len(urls) - len(blocked)} "
              f"blocked={len(blocked)}")
        for u in blocked:
            print(f"  BLOCKED  {u[:120]}")

        if not blocked:
            print("[backfill] nothing to do.")
            return 0

        if not apply:
            print(f"\n[backfill] dry-run — would NULL lead_image on rows matching "
                  f"{len(blocked)} URL(s). Re-run with --apply to write.")
            return 0

        # NULL the blocked URLs. event-level rollup is computed at query time
        # from articles.lead_image, so this immediately corrects published covers.
        updated = await conn.execute(
            "UPDATE articles SET lead_image = NULL WHERE lead_image = ANY($1::text[])",
            blocked,
        )
        print(f"\n[backfill] APPLIED — {updated} (rows updated across "
              f"{len(blocked)} blocked URLs)")
        return 0
    finally:
        await conn.close()
        await validator.aclose()


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill: NULL hotlink-blocked lead_image rows (ADR-0019)")
    ap.add_argument("--config", default="env.yaml", help="Curator config path")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = ap.parse_args()
    return asyncio.run(_run(args.config, args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
