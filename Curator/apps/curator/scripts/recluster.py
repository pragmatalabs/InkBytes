#!/usr/bin/env python3
"""One-off: re-cluster already-enriched articles with the CURRENT config
threshold, then synthesize multi-source events.

Reuses the embeddings + entities already in Postgres — does NOT re-run
ENRICH (so it costs nothing on the embedding/enrich side). Only the final
SYNTHESIZE step makes LLM calls, bounded by the number of multi-source
events.

Usage (from apps/curator, venv active, keys exported):
    python scripts/recluster.py env.local.yaml
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import CuratorConfig
from core.application import Application


async def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "env.local.yaml"
    cfg = CuratorConfig.load(cfg_path)
    app = Application(cfg)
    await app.db.connect()
    pool = app.db.pool

    thr = cfg.clustering.similarity_threshold
    minsrc = cfg.clustering.min_sources_to_publish
    print(f"Re-cluster with similarity_threshold={thr} "
          f"(distance<= {1.0 - thr:.2f}), min_sources_to_publish={minsrc}")

    # 1. Reset event assignments + derived tables (articles/enrichment kept).
    #    NB: do NOT use `TRUNCATE events CASCADE` — articles.event_id has an FK
    #    to events, so CASCADE would truncate articles (and entities) too,
    #    destroying the enrichment. Detach articles first, then plain DELETE.
    async with pool.acquire() as c:
        await c.execute("UPDATE articles SET event_id = NULL, cluster_distance = NULL;")
        await c.execute("DELETE FROM pages;")
        await c.execute("DELETE FROM events;")

    # 2. Replay clustering over enriched articles in scrape order.
    async with pool.acquire() as c:
        arts = await c.fetch(
            """
            SELECT id, outlet_id, language, scraped_at, embedding::text AS emb
              FROM articles
             WHERE embedding IS NOT NULL
             ORDER BY scraped_at ASC, id ASC
            """
        )
    print(f"Re-clustering {len(arts)} enriched articles...")

    for i, a in enumerate(arts, 1):
        embedding = json.loads(a["emb"])  # pgvector text "[...]" -> list[float]
        async with pool.acquire() as c:
            erows = await c.fetch(
                "SELECT name FROM entities WHERE article_id = $1", a["id"]
            )
        entities = [{"name": r["name"]} for r in erows]
        await app.cluster.run(
            article_id=a["id"],
            embedding=embedding,
            entities=entities,
            outlet_id=a["outlet_id"],
            language=a["language"],
            scraped_at=a["scraped_at"],
        )
        if i % 50 == 0:
            print(f"  ...{i}/{len(arts)}")

    # 3. Report cluster shape + synthesize multi-source events.
    async with pool.acquire() as c:
        total_events = await c.fetchval("SELECT COUNT(*) FROM events")
        multi = await c.fetch(
            "SELECT id, source_count, article_count FROM events "
            "WHERE source_count >= $1 ORDER BY source_count DESC, article_count DESC",
            minsrc,
        )
    print(f"Events: {total_events} total | {len(multi)} with >= {minsrc} sources")

    synthesized = 0
    for e in multi:
        try:
            await app.synthesize.run(e["id"])
            synthesized += 1
            print(f"  SYNTHESIZE {e['id']} "
                  f"(sources={e['source_count']}, articles={e['article_count']})")
        except Exception as exc:  # keep going; report at end
            print(f"  FAILED {e['id']}: {exc}")

    async with pool.acquire() as c:
        pages = await c.fetchval("SELECT COUNT(*) FROM pages")
    print(f"Done. Synthesized {synthesized} events; pages table now has {pages} rows.")

    await app.db.close()


if __name__ == "__main__":
    asyncio.run(main())
