#!/usr/bin/env python
"""Backfill ADR-0034 Tier 2 license-clean cover images (Openverse CC0/PDM).

For recent published events without a cover, builds a query from the event's top
LOC entity (a place → its landmark; "prefer places over people") or its theme, and
stores a commercially-licensed generic image in events.cover_image. The Reader
renders it over the owned procedural cover (Tier 1), which remains the fallback.

DRY-RUN by default; --apply writes. Rate-limited (Openverse anonymous limits).

  docker exec inkbytes-curator-worker python scripts/backfill_covers.py --since-hours 72
  docker exec inkbytes-curator-worker python scripts/backfill_covers.py --since-hours 72 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from core.config import CuratorConfig  # noqa: E402
from services.cover_image import pick_cover, _UA  # noqa: E402
from services.database_service import DatabaseService  # noqa: E402


async def _run(config_path: str, since_hours: int, limit: int,
               sleep: float, apply: bool, overwrite: bool) -> int:
    db = DatabaseService(CuratorConfig.load(config_path).database)
    await db.connect()
    n_q = n_found = n_written = 0
    # --overwrite re-fetches events that already have a cover (e.g. to upgrade
    # P1a Openverse covers to the P1b Wikimedia-canonical image).
    cover_filter = "" if overwrite else "AND e.cover_image IS NULL"
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT e.id,
                       (SELECT a.theme FROM articles a
                         WHERE a.event_id = e.id AND a.theme IS NOT NULL
                         GROUP BY a.theme ORDER BY count(*) DESC LIMIT 1) AS theme,
                       (SELECT ent.name
                          FROM entities ent JOIN articles a ON a.id = ent.article_id
                         WHERE a.event_id = e.id AND ent.type = 'LOC'
                           AND length(ent.name) >= 3
                         GROUP BY ent.name ORDER BY count(*) DESC LIMIT 1) AS top_loc,
                       (SELECT ent.name
                          FROM entities ent JOIN articles a ON a.id = ent.article_id
                         WHERE a.event_id = e.id AND ent.type = 'ORG'
                           AND length(ent.name) >= 3
                         GROUP BY ent.name ORDER BY count(*) DESC LIMIT 1) AS top_org,
                       p.headline,
                       (SELECT string_agg(DISTINCT ent.name, ' ')
                          FROM entities ent JOIN articles a ON a.id = ent.article_id
                         WHERE a.event_id = e.id AND length(ent.name) >= 3) AS entity_terms
                  FROM events e JOIN pages p ON p.event_id = e.id
                 WHERE p.published_at IS NOT NULL AND e.status = 'published'
                   {cover_filter}
                   AND e.last_material_update_at > NOW() - ($1 || ' hours')::interval
                 ORDER BY e.last_material_update_at DESC
                 LIMIT $2
                """,
                str(since_hours), limit)
            print(f"[covers] {len(rows)} events without a cover (last {since_hours}h) "
                  f"| mode={'APPLY' if apply else 'DRY-RUN'}")
            async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": _UA}) as client:
                for r in rows:
                    n_q += 1
                    context = " ".join(filter(None, [
                        r.get("headline"), r["theme"], r.get("entity_terms")]))
                    cover = await pick_cover(r["theme"], r["top_loc"], r["top_org"],
                                             r["id"], client, context=context)
                    if not cover:
                        print(f"  {r['id']} loc={r['top_loc']!r} -> none")
                        await asyncio.sleep(sleep)
                        continue
                    n_found += 1
                    print(f"  {r['id']} [{cover['provider']}/{cover['license']}] "
                          f"q={cover['query']!r:24} {cover['url'][:46]}")
                    if apply:
                        await conn.execute(
                            "UPDATE events SET cover_image = $2::jsonb WHERE id = $1",
                            r["id"], json.dumps(cover))
                        n_written += 1
                    await asyncio.sleep(sleep)
        print(f"\n[covers] queried={n_q} found={n_found} written={n_written}"
              + ("" if apply else "  (DRY-RUN — pass --apply to write)"))
        return 0
    finally:
        await db.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="env.yaml")
    ap.add_argument("--since-hours", type=int, default=72)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--overwrite", action="store_true",
                    help="re-fetch events that already have a cover (upgrade P1a→P1b)")
    args = ap.parse_args()
    sys.exit(asyncio.run(_run(args.config, args.since_hours, args.limit,
                              args.sleep, args.apply, args.overwrite)))


if __name__ == "__main__":
    main()
