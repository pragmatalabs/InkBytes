"""One-off re-embed backfill: populate articles.embedding with local bge-m3
(1024d) after migration 005. Mirrors application.py's embed input
(f"{title}\n\n{text[:4000]}"). Idempotent: only touches NULL-embedding rows.

Scratch / ops utility — not part of the committed pipeline.
"""
import asyncio
import asyncpg
from core.config import EmbedCfg
from services.embedding_service import EmbeddingService

DSN = "postgresql://inkbytes:inkbytes@localhost:5432/inkbytes"
CONCURRENCY = 6


async def main():
    svc = EmbeddingService(EmbedCfg())  # local-first defaults → ollama bge-m3
    conn = await asyncpg.connect(DSN)
    rows = await conn.fetch(
        "SELECT id, title, body_text FROM articles "
        "WHERE embedding IS NULL AND body_text IS NOT NULL"
    )
    print(f"re-embedding {len(rows)} articles with bge-m3 (1024d) ...", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    done = 0

    async def one(r):
        nonlocal done
        async with sem:
            text = f"{r['title']}\n\n{(r['body_text'] or '')[:4000]}"
            vec = await svc.embed(text)
            await conn.execute(
                "UPDATE articles SET embedding = $1::vector WHERE id = $2",
                "[" + ",".join(map(str, vec)) + "]", r["id"],
            )
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(rows)}", flush=True)

    await asyncio.gather(*(one(r) for r in rows))
    n = await conn.fetchval("SELECT count(embedding) FROM articles")
    dim = await conn.fetchval("SELECT vector_dims(embedding) FROM articles WHERE embedding IS NOT NULL LIMIT 1")
    await conn.close()
    print(f"done. non-null embeddings = {n}, dim = {dim}")


asyncio.run(main())
