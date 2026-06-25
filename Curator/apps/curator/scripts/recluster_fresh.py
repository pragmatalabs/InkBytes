#!/usr/bin/env python
"""Clean-slate re-cluster: build fresh tight events from recent UNCLUSTERED articles.

Companion to the "start fresh, keep recent" reset (ADR-0031/0033 cleanup). After
the wipe SQL drops all legacy events + pages and NULLs the surviving recent
articles' event_id, this clusters those flat `event_id IS NULL` articles from
scratch under the SAME precision algorithm now live in cluster.py (centroid-linkage
+ entity-specificity), so the new corpus is tight from article #1 — no legacy
mega-buckets to untangle.

Unlike recluster_megabuckets.py (which splits WITHIN one existing event), this
seeds brand-new events from a flat unclustered set.

DRY-RUN by default — reports the cluster shape, writes nothing. `--apply` creates
the events + assigns articles + sets centroid/clocks, then prints the event_ids
that have >=2 sources (run `--synthesize-pending --since-hours N` after).

  # the wipe (run + verify FIRST, after a pg_dump backup):
  #   DELETE FROM events;                                   -- cascades pages/story_arcs, NULLs article.event_id
  #   DELETE FROM articles WHERE scraped_at < NOW() - INTERVAL '7 days';   -- cascades entities
  docker exec inkbytes-curator-worker python scripts/recluster_fresh.py --since-days 7
  docker exec inkbytes-curator-worker python scripts/recluster_fresh.py --since-days 7 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ulid  # noqa: E402
from core.config import CuratorConfig  # noqa: E402
from services.database_service import DatabaseService  # noqa: E402
# reuse the exact greedy centroid-linkage + specificity simulation cluster.py uses
from scripts.recluster_megabuckets import CAP, DISTANCE, MIN_SHARED, _srcs, simulate  # noqa: E402


async def _run(config_path: str, since_days: int, apply: bool,
               distance: float = DISTANCE, cap: float = CAP,
               min_shared: int = MIN_SHARED) -> int:
    db = DatabaseService(CuratorConfig.load(config_path).database)
    await db.connect()
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT a.id, a.outlet_id, a.scraped_at, a.embedding::text AS emb,
                          ARRAY(SELECT lower(name) FROM entities WHERE article_id=a.id) AS ents
                     FROM articles a
                    WHERE a.event_id IS NULL
                      AND a.embedding IS NOT NULL
                      AND a.scraped_at > NOW() - ($1 || ' days')::interval
                    ORDER BY a.scraped_at""",
                str(since_days))
            print(f"[fresh] {len(rows)} unclustered articles in last {since_days}d "
                  f"| dist={distance} cap={cap} min_shared={min_shared} "
                  f"| mode={'APPLY' if apply else 'DRY-RUN'}")
            if len(rows) < 2:
                print("[fresh] nothing to cluster.")
                return 0

            clusters, _assign = simulate(rows, distance, cap, min_shared)
            sizes = sorted((len(c["members"]) for c in clusters), reverse=True)
            pub = sum(1 for c in clusters if _srcs(rows, c["members"]) >= 2)
            singles = sum(1 for c in clusters if len(c["members"]) == 1)
            print(f"[fresh] -> {len(clusters)} events | publishable(>=2src)={pub} "
                  f"| singletons={singles} | top sizes={sizes[:10]}")

            if not apply:
                print("[fresh] DRY-RUN — pass --apply to create events "
                      "(then --synthesize-pending --since-hours).")
                return 0

            resynth: list[str] = []
            async with conn.transaction():
                for c in clusters:
                    new_id = ulid.new().str
                    member_ids = [rows[i]["id"] for i in c["members"]]
                    await conn.execute(
                        """INSERT INTO events (id, first_seen_at, last_updated_at,
                               last_material_update_at, source_count, article_count, language, status)
                           SELECT $1, min(scraped_at), max(scraped_at), max(scraped_at),
                                  count(DISTINCT outlet_id), count(*), max(language), 'draft'
                             FROM articles WHERE id = ANY($2::text[])""",
                        new_id, member_ids)
                    await conn.execute(
                        "UPDATE articles SET event_id=$1 WHERE id = ANY($2::text[])",
                        new_id, member_ids)
                    await conn.execute(
                        "UPDATE events SET centroid=(SELECT avg(embedding) FROM articles "
                        "WHERE event_id=$1 AND embedding IS NOT NULL) WHERE id=$1", new_id)
                    if _srcs(rows, c["members"]) >= 2:
                        resynth.append(new_id)
            print(f"[fresh] APPLIED. {len(clusters)} events created, "
                  f"{len(resynth)} publishable (>=2 src) need synthesis.")
            print("[fresh] next: python main.py --config env.yaml "
                  f"--synthesize-pending --since-hours {since_days * 24}")
        return 0
    finally:
        await db.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="env.yaml")
    ap.add_argument("--since-days", type=int, default=7)
    ap.add_argument("--distance", type=float, default=DISTANCE)
    ap.add_argument("--cap", type=float, default=CAP)
    ap.add_argument("--min-shared", type=int, default=MIN_SHARED)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    sys.exit(asyncio.run(_run(args.config, args.since_days, args.apply,
                              args.distance, args.cap, args.min_shared)))


if __name__ == "__main__":
    main()
