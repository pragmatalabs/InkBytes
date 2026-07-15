#!/usr/bin/env python3
"""Backfill entity_media with Wikidata/Commons photos + descriptions for the top
PERSON entities in the graph (ADR-0034 companion).

Resolves each top person → license-clean Commons portrait (P18, human-filtered)
+ one-line description, caching into entity_media. A miss is cached as
`blocked=TRUE` so re-runs don't re-query the same person. Rate-limited; dry-run
by default; `--overwrite` re-resolves already-cached names.

  python scripts/backfill_entity_photos.py --limit 120            # dry-run
  python scripts/backfill_entity_photos.py --limit 120 --apply
  python scripts/backfill_entity_photos.py --limit 120 --apply --overwrite
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os

import asyncpg
import httpx

from services.entity_photo import resolve_person

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("backfill_entity_photos")

# Top PERSON entities by distinct published-event count + a sample headline for
# disambiguation context. Mirrors the /graph ranking (dominant type from raw
# mentions), scoped to PERSON.
TOP_PEOPLE_SQL = """
WITH published AS (
    SELECT e.id AS event_id FROM events e
     WHERE e.status='published'
       AND EXISTS (SELECT 1 FROM pages p WHERE p.event_id=e.id AND p.published_at IS NOT NULL)
),
ments AS (
    SELECT LOWER(ent.name) AS name_key, ent.name AS label, a.event_id
      FROM entities ent JOIN articles a ON a.id=ent.article_id
      JOIN published pub ON pub.event_id=a.event_id
     WHERE UPPER(ent.type)='PERSON' AND LENGTH(ent.name)>=3
),
counts AS (
    SELECT name_key, MIN(label) AS label, COUNT(DISTINCT event_id) AS ec
      FROM ments GROUP BY name_key
)
SELECT c.name_key, c.label, c.ec,
       (SELECT p.headline FROM pages p
          JOIN articles a ON a.event_id=p.event_id
          JOIN entities ent ON ent.article_id=a.id AND LOWER(ent.name)=c.name_key
         WHERE p.published_at IS NOT NULL
         ORDER BY p.freshness_at DESC LIMIT 1) AS context
  FROM counts c
 WHERE c.ec >= $1
 ORDER BY c.ec DESC
 LIMIT $2
"""


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--min-events", type=int, default=2)
    ap.add_argument("--apply", action="store_true", help="write (default dry-run)")
    ap.add_argument("--overwrite", action="store_true", help="re-resolve cached names")
    ap.add_argument("--sleep", type=float, default=0.4, help="seconds between people")
    args = ap.parse_args()

    dsn = os.environ["DATABASE_URL"]
    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=2)
    async with pool.acquire() as conn:
        people = await conn.fetch(TOP_PEOPLE_SQL, args.min_events, args.limit)
        cached = set()
        if not args.overwrite:
            cached = {r["name_norm"] for r in
                      await conn.fetch("SELECT name_norm FROM entity_media")}

    todo = [p for p in people if args.overwrite or p["name_key"] not in cached]
    log.info("people: %d candidates, %d to resolve (%d already cached)",
             len(people), len(todo), len(people) - len(todo))

    hits = misses = 0
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "InkBytes/1.0 (entity photos)"}) as client:
        for p in todo:
            name, label, context = p["name_key"], p["label"], (p["context"] or "")
            photo = await resolve_person(label, client, context=context)
            if photo:
                hits += 1
                log.info("  ✓ %s → %s (%s)", label, photo["wikidata_qid"], photo["license"])
            else:
                misses += 1
                log.info("  · %s → no license-clean human photo", label)
            if args.apply:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO entity_media (name_norm, label, type, wikidata_qid,
                            image_url, thumb_url, license, license_url, attribution,
                            source_url, description, blocked, resolved_at)
                        VALUES ($1,$2,'PERSON',$3,$4,$5,$6,$7,$8,$9,$10,$11,NOW())
                        ON CONFLICT (name_norm) DO UPDATE SET
                            label=EXCLUDED.label, wikidata_qid=EXCLUDED.wikidata_qid,
                            image_url=EXCLUDED.image_url, thumb_url=EXCLUDED.thumb_url,
                            license=EXCLUDED.license, license_url=EXCLUDED.license_url,
                            attribution=EXCLUDED.attribution, source_url=EXCLUDED.source_url,
                            description=EXCLUDED.description, blocked=EXCLUDED.blocked,
                            resolved_at=NOW()
                        """,
                        name, label, (photo or {}).get("wikidata_qid"),
                        (photo or {}).get("image_url"), (photo or {}).get("thumb_url"),
                        (photo or {}).get("license"), (photo or {}).get("license_url"),
                        (photo or {}).get("attribution"), (photo or {}).get("source_url"),
                        (photo or {}).get("description"), photo is None)
            await asyncio.sleep(args.sleep)

    await pool.close()
    log.info("done: %d photos, %d misses%s", hits, misses,
             "" if args.apply else "  (DRY-RUN — re-run with --apply to write)")


if __name__ == "__main__":
    asyncio.run(main())
