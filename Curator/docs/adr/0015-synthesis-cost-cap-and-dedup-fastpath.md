# ADR-0015 — Synthesis Article Cap + Duplicate Enrichment Fast-Path

> *Status: accepted / implemented · Owner: Julián · Last updated: 2026-06-08*
>
> ✅ **Deployed 2026-06-08.** Both fixes are live in production on DO (`67.205.136.61`).

## Context

Two independent cost/throughput problems were discovered by inspecting the
`llm_calls` table and the RabbitMQ queue depth on 2026-06-08.

---

### Problem 1 — Synthesis token explosion on large clusters

`SynthesizeSkill._format_articles` sends the body of **every article** in the
event cluster to the LLM on each synthesis call (truncated to 3 500 chars per
article). For high-traffic stories this is catastrophically expensive:

| Event | Articles | Tokens/synthesis call | Synthesis calls | Total cost |
|---|---|---|---|---|
| SpaceX/Anthropic IPOs | 131 | ~114k | 8 | **$0.85** |
| US-Iran war (100th day) | 65 | ~57k | 19 | **$0.42** |
| Iran Inflation | 33 | ~29k | 16 | **$0.41** |

Two independent multipliers compound cost:
1. **Article count** — each additional article adds ~875 tokens to every call.
2. **Re-synthesis frequency** — triggered on every new distinct outlet joining
   the cluster; a story that grows from 1→10 outlets fires 8+ re-syntheses,
   each one larger than the last.

A synthesis with 131 articles sends ~114k input tokens to the LLM.
The 15 most-recent, source-diverse articles would carry almost identical
informational value at ~13k tokens — **a 9× reduction**.

### Problem 2 — No fast-path for already-enriched articles in the RabbitMQ consumer

`_handle_event` calls `enrich.run()`, `embed.embed()`, and
`db.write_enrichment()` unconditionally after every `upsert_article_raw()`.

`upsert_article_raw()` uses a content-hash guard: enrichment fields are reset
to NULL only when `content_hash IS DISTINCT FROM EXCLUDED.content_hash`.
Unchanged re-scraped articles **keep their enrichment in the DB**, but the
application still re-enriches them with a fresh LLM call.

Consequence: Messor publishes every article it scrapes on every 4×/day cycle.
After 18 hours (~4 cycles), the queue contained 75 890 messages for a DB with
only 403 unenriched articles — meaning **75 487 messages were for
already-enriched articles**. At ~24 s per full enrichment, draining would take
**~21 days** instead of ~2 hours.

---

## Decision

### Fix 1 — Cap articles sent to synthesis (max 15, 2 per outlet)

In `SynthesizeSkill._format_articles`, select at most `MAX_ARTICLES=15`
articles before building the prompt:

1. Group by `outlet_name`.
2. Within each outlet, keep the 2 most-recently-published articles
   (`published_at DESC`).
3. Sort the resulting pool by `published_at DESC`, take the first
   `MAX_ARTICLES`.

This guarantees source diversity (no outlet dominates) while staying within a
predictable token budget (~13k input tokens per synthesis call regardless of
cluster size).

`MAX_ARTICLES` and `MAX_PER_OUTLET` are module-level constants — easy to tune
without touching the prompt.

### Fix 2 — Skip re-enrichment for unchanged articles (fast-path)

Modify `upsert_article_raw()` to return a boolean `content_changed` using
`RETURNING` semantics:

```sql
-- after the upsert, read back whether enriched_at is still set
-- (NULL → content changed/new article; NOT NULL → unchanged, skip pipeline)
```

In `_handle_event`, after the upsert:

```python
content_changed = await self.db.upsert_article_raw(...)
if not content_changed:
    # Article unchanged in DB — no LLM work needed.
    # Still run CLUSTER in case this re-scrape arrived before an earlier
    # message was clustered, but use the stored embedding.
    embedding = await self.db.get_embedding(article.id)
    if embedding is not None:
        await self.cluster.run(
            article_id=article.id, embedding=embedding, ...
        )
    return   # skip ENRICH, EMBED, SYNTHESIZE, ILLUSTRATE
```

**Return value contract for `upsert_article_raw`:**
- `True`  — article is new or content changed → full pipeline required.
- `False` — content unchanged → enrichment still valid, fast-path.

---

## Consequences

### Fix 1 (synthesis cap)
- **Cost**: ~9× reduction in synthesis input tokens for large clusters.
  Typical synth call: 100k → ~13k tokens.
- **Quality**: Negligible degradation — the LLM already ignores redundant
  articles from the same outlet; selecting the freshest captures the latest
  developments.
- **Re-synthesis frequency** (separate improvement, not in scope here):
  gating at every 2–3 new sources instead of every 1 would further reduce
  call count for fast-growing stories.

### Fix 2 (duplicate fast-path)
- **Queue drain time**: 75 890 messages at ~24s → ~21 days becomes
  ~75 487 × 0.1s + 403 × 24s ≈ **~2 hours**.
- **LLM cost**: eliminates re-enrichment charges for every Messor re-scrape
  cycle (currently 4×/day × all articles = massive waste).
- **Risk**: the `content_hash` guard already exists in `upsert_article_raw` —
  this fix makes the application respect it, not introduce new logic.
- **Cluster correctness**: unchanged articles still run through CLUSTER with
  their stored embedding, so newly-arriving articles can still attach to
  existing events.

---

## Alternatives considered

### Skip CLUSTER for unchanged articles
Simpler, but risks leaving articles unattached to events if they arrived
during a previous run that crashed before clustering. The fast-path re-runs
CLUSTER with the stored embedding — cheap (vector similarity query, no LLM).

### Purge the queue of duplicate messages
Could issue a `rabbitmqctl purge_queue curator.articles-scraped` and let the
next Messor cycle re-publish only new articles. Not safe without Messor-side
dedup: Messor currently re-publishes all articles every cycle, so the queue
would fill again immediately. Fix 2 is the right layer.

### Reduce Messor re-publish frequency
Messor publishing only new articles (seen-URL cache) would prevent queue
accumulation entirely. Valid long-term, but requires changes to Messor;
Fix 2 is the short-term mitigation that lives entirely within Curator.
