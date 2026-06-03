# ADR-0002 — pgvector + OpenAI embeddings for article clustering

> *Status: Accepted · Owner: Julián de la Rosa · Date: 2026-06-02*

## Context

Curator's Skill 2 (CLUSTER) must group articles from different outlets
that cover the same real-world event. The key challenge: headlines are
paraphrased, not copied. A title-matching approach fails immediately.

Examples of same-event headlines that share no words:
- "US Fed holds rates" / "Central bank unchanged amid cooling inflation"
- "Trump-Xi summit set for June" / "White House confirms presidential meeting in Asia"

We need a similarity measure that captures meaning, not surface text.

## Decision

Use **OpenAI `text-embedding-3-small`** to produce per-article embeddings,
store them in Postgres via **pgvector**, and find article neighbors using
the `<=>` cosine distance operator with an IVFFlat approximate-NN index.

Cluster a pair of articles when:
1. Cosine similarity ≥ 0.78 (`distance ≤ 0.22`)
2. At least 1 overlapping entity name (dev) / 2 (prod)
3. Both articles are within a 48-hour recency window

The threshold combination prevents both false positives (unrelated stories
about the same entity) and false negatives (same story, different entities
mentioned).

### Why `text-embedding-3-small`

| Model | Quality | $/1M tokens | Dims | Verdict |
|---|---|---|---|---|
| `text-embedding-3-small` (OpenAI) | High | $0.02 | 1 536 | ✅ Chosen |
| `text-embedding-3-large` (OpenAI) | Highest | $0.13 | 3 072 | Overkill at 6× cost |
| `voyage-3-lite` (Anthropic) | High | $0.02 | 1 024 | Same cost, no advantage here |
| Local `all-MiniLM-L6-v2` (sentence-transformers) | Good | $0 | 384 | Adds 400 MB model + torch to container; poor fit for $24 DO droplet |
| TF-IDF cosine | Poor | $0 | variable | Fails on paraphrased headlines |
| Jaccard / Levenshtein on title | Very poor | $0 | — | Not viable at all |

**Cost**: at 5 000 articles/day × ~500 tokens each = 2.5 M tokens/day =
**$0.05/day**. This is negligible within the $75/day LLM budget.

### Why pgvector

pgvector is the simplest path: it extends the existing Postgres instance,
no new service, no new credentials, no new network hop. The IVFFlat index
provides sub-linear ANN search with acceptable recall at our volume (v0
target: < 50 k articles total).

Alternatives rejected:
- **Pinecone / Weaviate** — managed vector stores; another service, another
  credential, another failure point, overkill for v0 volume.
- **Qdrant** — excellent but requires a separate container; adds ops burden.
- **In-memory FAISS** — fast but ephemeral; rebuilt on every restart.

### Stub mode (dev without `OPENAI_API_KEY`)

When `OPENAI_API_KEY` is not set, `EmbeddingService` falls back to a
**deterministic hash stub**. The stub maps article text → a reproducible
fixed-dimension float vector by hashing the content.

**The stub is intentionally broken for clustering quality.** Hash vectors
have no semantic relationship to each other, so cosine similarity is
effectively random and the 0.78 threshold is never met across outlets.
This is by design — stub mode tests pipeline plumbing (can Curator receive
a message, call the skill, write to the DB?) without burning API tokens.

**Do not use stub mode to evaluate clustering accuracy.** Set both API
keys when you want to see real SYNTHESIZE output.

To make stub-mode behavior explicit, the log emits:

```
WARNING EmbeddingService running in STUB mode (no OPENAI_API_KEY)
```

on startup. If you see this and then observe zero pages, it is expected.

## Schema

```sql
-- In 001_initial_schema.sql
embedding vector(1536)  -- NULL until ENRICH completes

CREATE INDEX idx_articles_embedding
    ON articles USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
-- Tune `lists` to ~sqrt(row_count) once we exceed 10k articles.
```

The `CLUSTER` skill query:

```sql
SELECT a.id, a.event_id, a.outlet_id,
       (a.embedding <=> $1::vector) AS distance,
       ARRAY(SELECT lower(name) FROM entities WHERE article_id = a.id) AS entities
  FROM articles a
 WHERE a.embedding IS NOT NULL
   AND a.language = $2
   AND a.scraped_at > NOW() - ($3 || ' hours')::interval
   AND a.id <> $4
 ORDER BY a.embedding <=> $1::vector ASC
 LIMIT 20
```

The IVFFlat index makes this O(sqrt(n)) instead of O(n).

## Consequences

**Positive**
- Semantic similarity catches paraphrased headlines — the primary use case.
- Entity overlap as a second filter prevents false positives from broad
  entities (both articles mention "Trump" but cover unrelated events).
- Cost is negligible; no rate limits at v0 volume.
- Runs in the existing Postgres instance — no new service.

**Negative**
- Requires `OPENAI_API_KEY` in production. Failure of the OpenAI embedding
  endpoint means articles enrich but don't cluster.
- Stub mode is misleading without good documentation (addressed above).
- IVFFlat recall degrades when `lists` is not re-tuned as the table grows.
  Mitigation: set a calendar reminder to re-`REINDEX` at 100 k rows.

## Migration to local embeddings (v1 option)

If OpenAI costs or reliability become a concern, the swap is clean:

1. Replace `EmbeddingService` with a `sentence-transformers` wrapper.
2. Change `embedding vector(1536)` → `vector(384)` (requires re-embedding
   all existing rows — plan a maintenance window).
3. Update `env.yaml` to remove `embeddings.api_key`.

The CLUSTER skill code is unchanged; it only sees a Python `list[float]`.

## Follow-ups

- Re-tune IVFFlat `lists` parameter when articles table exceeds 10 k rows.
- Consider adding a `factuality` filter to CLUSTER (don't cluster a 0.3
  factuality article with a 0.9 factuality article even if semantically
  similar).
- Evaluate `voyage-3-lite` as a single-vendor (Anthropic) option in v1.
