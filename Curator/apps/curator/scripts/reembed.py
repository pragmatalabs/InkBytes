#!/usr/bin/env python3
"""One-off: (re-)embed articles that have no embedding, using the CURRENT
configured embedding provider (Curator ADR-0003 default: local Ollama bge-m3).

Use after migration 005 widens articles.embedding to vector(1024) and clears the
old OpenAI vectors, or any time embeddings are missing. Mirrors the pipeline's
embed input (f"{title}\n\n{body_text[:4000]}"). Idempotent: only touches rows
where embedding IS NULL.

Does NOT re-run ENRICH or SYNTHESIZE (no LLM cost). After a full re-embed you
may want `python scripts/recluster.py env.local.yaml` to rebuild events on the
new vectors.

Usage (from apps/curator, venv active):
    python scripts/reembed.py env.local.yaml
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import CuratorConfig
from services.database_service import DatabaseService
from services.embedding_service import EmbeddingService

CONCURRENCY = 6


async def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "env.local.yaml"
    cfg = CuratorConfig.load(cfg_path)
    svc = EmbeddingService(cfg.embeddings)
    print(f"Re-embed with provider={cfg.embeddings.provider} "
          f"model={cfg.embeddings.model} dims={cfg.embeddings.dimensions}")

    db = DatabaseService(cfg.database)
    await db.connect()
    pool = db.pool
    async with pool.acquire() as c:
        rows = await c.fetch(
            "SELECT id, title, body_text FROM articles "
            "WHERE embedding IS NULL AND body_text IS NOT NULL"
        )
    print(f"{len(rows)} articles to embed ...", flush=True)

    sem = asyncio.Semaphore(CONCURRENCY)
    done = 0

    async def one(r):
        nonlocal done
        async with sem:
            text = f"{r['title']}\n\n{(r['body_text'] or '')[:4000]}"
            vec = await svc.embed(text)
            async with pool.acquire() as c:
                await c.execute(
                    "UPDATE articles SET embedding = $1::vector WHERE id = $2",
                    "[" + ",".join(map(str, vec)) + "]", r["id"],
                )
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(rows)}", flush=True)

    await asyncio.gather(*(one(r) for r in rows))
    async with pool.acquire() as c:
        n = await c.fetchval("SELECT count(embedding) FROM articles")
        dim = await c.fetchval(
            "SELECT vector_dims(embedding) FROM articles WHERE embedding IS NOT NULL LIMIT 1"
        )
    await db.close()
    print(f"done. non-null embeddings = {n}, dim = {dim}")


if __name__ == "__main__":
    asyncio.run(main())
