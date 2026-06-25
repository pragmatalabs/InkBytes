#!/usr/bin/env python
"""Re-cluster legacy mega-buckets under ADR-0031 precision rules (item 4 cleanup).

The precision clustering (`clustering.precision_mode`) only governs FUTURE
attaches — the ~hundreds of pre-existing mega-buckets (e.g. "World Cup: Mexico
leads Group A" = 2,085 articles / 18 days) persist until re-clustered. This tool
re-runs the centroid-linkage + entity-specificity algorithm over each mega-bucket's
own members and splits it into tight sub-events.

DRY-RUN by default — reports the split + publish impact, writes nothing. `--apply`
performs the reassignment: the LARGEST sub-cluster keeps the original event_id (its
page survives, just stale → re-synthesize); the rest become new draft events. It
prints the event_ids needing re-synthesis (run the normal resynth path after).

  docker exec inkbytes-curator-worker python scripts/recluster_megabuckets.py --min-articles 50
  docker exec inkbytes-curator-worker python scripts/recluster_megabuckets.py --min-articles 50 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ulid  # noqa: E402
from core.config import CuratorConfig  # noqa: E402
from services.database_service import DatabaseService  # noqa: E402

DISTANCE = 0.34        # precision_distance (ADR-0031 tightened 2026-06-25); --distance overrides
CAP = 0.05             # specificity_cap; --cap overrides
MIN_SHARED = 2         # specificity_min_shared — ≥2 shared specific entities to merge


def _vec(s):
    return np.fromstring(s.strip().lstrip("[").rstrip("]"), sep=",", dtype=np.float32)


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def simulate(rows, distance=DISTANCE, cap=CAP, min_shared=MIN_SHARED):
    """Greedy online centroid-linkage + entity-specificity (mirrors cluster.py)."""
    n = len(rows)
    df = Counter()
    for r in rows:
        for e in set(r["ents"] or []):
            df[e] += 1
    embs = [_unit(_vec(r["emb"])) for r in rows]
    spec = [{e for e in (r["ents"] or []) if df.get(e, 0) <= cap * n} for r in rows]
    clusters = []  # {sum,count,spec_ents,members}
    assign = []
    for i in range(n):
        v = embs[i]
        best, bestd = -1, 1e9
        for ci, c in enumerate(clusters):
            d = 1.0 - float(np.dot(v, _unit(c["sum"] / c["count"])))
            if d < bestd:
                bestd, best = d, ci
        ok = (best >= 0 and bestd < distance
              and len(spec[i] & clusters[best]["spec_ents"]) >= min_shared)
        if ok:
            c = clusters[best]
            c["sum"] += v; c["count"] += 1; c["spec_ents"] |= spec[i]; c["members"].append(i)
            assign.append(best)
        else:
            clusters.append({"sum": v.copy(), "count": 1, "spec_ents": set(spec[i]), "members": [i]})
            assign.append(len(clusters) - 1)
    return clusters, assign


def _srcs(rows, idxs):
    return len({rows[i]["outlet_id"] for i in idxs})


async def _run(config_path: str, min_articles: int, apply: bool,
               distance: float = DISTANCE, cap: float = CAP,
               event_id: str | None = None) -> int:
    db = DatabaseService(CuratorConfig.load(config_path).database)
    await db.connect()
    try:
        async with db.pool.acquire() as conn:
            if event_id:  # target one specific event (precise staging)
                megas = await conn.fetch(
                    """SELECT e.id, e.article_count, left(p.headline,48) AS headline
                         FROM events e JOIN pages p ON p.id=e.id WHERE e.id = $1""", event_id)
            else:
                megas = await conn.fetch(
                    """SELECT e.id, e.article_count, left(p.headline,48) AS headline
                         FROM events e JOIN pages p ON p.id=e.id
                        WHERE p.published_at IS NOT NULL AND e.article_count >= $1
                        ORDER BY e.article_count DESC""", min_articles)
            print(f"[recluster] {len(megas)} mega-buckets (>= {min_articles} articles) "
                  f"| mode={'APPLY' if apply else 'DRY-RUN'}")
            tot_in = tot_sub = tot_pub = 0
            resynth: list[str] = []
            for m in megas:
                rows = await conn.fetch(
                    """SELECT a.id, a.outlet_id, a.scraped_at, a.embedding::text AS emb,
                              ARRAY(SELECT lower(name) FROM entities WHERE article_id=a.id) AS ents
                         FROM articles a WHERE a.event_id=$1 AND a.embedding IS NOT NULL
                        ORDER BY a.scraped_at""", m["id"])
                if len(rows) < 2:
                    continue
                clusters, assign = simulate(rows, distance, cap)
                sizes = sorted((len(c["members"]) for c in clusters), reverse=True)
                pub = sum(1 for c in clusters if _srcs(rows, c["members"]) >= 2)
                tot_in += len(rows); tot_sub += len(clusters); tot_pub += pub
                print(f"  {m['headline']!r}: {len(rows)} arts -> {len(clusters)} events "
                      f"| publishable(>=2src)={pub} | top sizes={sizes[:6]}")
                if apply:
                    order = sorted(range(len(clusters)), key=lambda ci: len(clusters[ci]["members"]), reverse=True)
                    keep_ci = order[0]  # largest fragment keeps the original event_id + page
                    async with conn.transaction():
                        for ci in order[1:]:
                            new_id = ulid.new().str
                            members = clusters[ci]["members"]
                            await conn.execute(
                                """INSERT INTO events (id, first_seen_at, last_updated_at,
                                       last_material_update_at, source_count, article_count, language, status)
                                   SELECT $1, min(scraped_at), max(scraped_at), max(scraped_at),
                                          count(DISTINCT outlet_id), count(*), max(language), 'draft'
                                     FROM articles WHERE id = ANY($2::text[])""",
                                new_id, [rows[i]["id"] for i in members])
                            await conn.execute(
                                "UPDATE articles SET event_id=$1 WHERE id = ANY($2::text[])",
                                new_id, [rows[i]["id"] for i in members])
                            await conn.execute(
                                "UPDATE events SET centroid=(SELECT avg(embedding) FROM articles WHERE event_id=$1 AND embedding IS NOT NULL) WHERE id=$1",
                                new_id)
                            if _srcs(rows, members) >= 2:
                                resynth.append(new_id)
                        # recompute the kept event from its surviving (largest) fragment
                        await conn.execute(
                            """UPDATE events SET article_count=(SELECT count(*) FROM articles WHERE event_id=$1),
                                   source_count=(SELECT count(DISTINCT outlet_id) FROM articles WHERE event_id=$1),
                                   centroid=(SELECT avg(embedding) FROM articles WHERE event_id=$1 AND embedding IS NOT NULL)
                                 WHERE id=$1""", m["id"])
                        # Unpublish E's now-stale page + draft it, so --synthesize-pending
                        # re-synthesizes it fresh from its (smaller) surviving membership.
                        # (synthesize-pending only picks up events WITHOUT a published page.)
                        await conn.execute("UPDATE pages SET published_at=NULL WHERE id=$1", m["id"])
                        await conn.execute("UPDATE events SET status='draft' WHERE id=$1", m["id"])
                    resynth.append(m["id"])  # re-synthesize fresh (unpublished above)
            print(f"\n[recluster] TOTAL: {tot_in} articles in {len(megas)} mega-buckets "
                  f"-> {tot_sub} events ({tot_pub} publishable)")
            if apply:
                print(f"[recluster] APPLIED. {len(resynth)} events need re-synthesis:")
                print(" ".join(resynth[:50]) + (" …" if len(resynth) > 50 else ""))
            else:
                print("[recluster] DRY-RUN — pass --apply to reassign (then re-synthesize the listed events).")
        return 0
    finally:
        await db.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="env.yaml")
    ap.add_argument("--min-articles", type=int, default=50)
    ap.add_argument("--distance", type=float, default=DISTANCE)
    ap.add_argument("--cap", type=float, default=CAP)
    ap.add_argument("--event-id", default=None, help="target one event (precise staging)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    sys.exit(asyncio.run(_run(args.config, args.min_articles, args.apply,
                              args.distance, args.cap, args.event_id)))


if __name__ == "__main__":
    main()
