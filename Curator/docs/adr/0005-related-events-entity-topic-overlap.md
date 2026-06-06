# ADR-0005 — Related Events via Entity + Topic Overlap (Approach A)

* **Status**: Accepted
* **Date**: 2026-06-06
* **Deciders**: Julián de la Rosa
* **Implements**: Reader product goal — surface related event pages on the event detail view
* **Superseded by**: *nothing yet — Approach B (event embeddings) will extend, not replace, this ADR*

---

## Context

Published events share structure that can be used to surface related stories
to the reader. Two events about "Colombia election tensions" and "US visa
threats over Colombian vote" share entities (Colombia, US, the candidate names)
and the same topic. Surfacing this relationship directly on the event page keeps
the reader in context and increases session depth.

The question is which similarity signal to use and at what threshold.

Available signals on existing published pages (no schema change required):

| Signal | Location | Notes |
|---|---|---|
| Entity names | `pages.entities` JSONB `[{name, type}]` | Already extracted by ENRICH skill |
| Topic | `events.topic` | Broad vertical — Technology, Politics, etc. |
| Language | `events.language` | EN / ES / … |
| Article embeddings | `articles.embedding` pgvector 1024-d | Per-article, not per-event |
| Keywords | `articles.keywords_canonical` | Per-article, needs aggregation |

Corpus size at decision time: **~240 published events**.

---

## Decision

**Approach A: pure-SQL entity + topic overlap.** No schema migration needed.
Ships today, works correctly at current corpus size.

### Score formula

```
entity_overlap = |shared_entity_names| / max(|entities_A|, |entities_B|, 1)
topic_bonus    = 1.3 if (topic_A == topic_B AND topic != NULL) else 1.0

score = entity_overlap × topic_bonus
```

*Why overlap coefficient (not Jaccard)?*  
Jaccard penalises large entity sets. An event with 10 entities and another with
4, sharing all 4, has Jaccard 4/10 = 0.40 but overlap coefficient 4/4 = 1.0.
The smaller set is entirely contained — that is a strong relationship.

*Why the topic multiplier (not additive)?*  
Topic-only matches (zero shared entities) should never qualify. The multiplier
ensures entity_overlap is always the primary driver. Two events with no shared
entity names get score=0 regardless of topic.

### Threshold

Default `min_score = 0.4`. Effective meanings:
- No topic boost: entity_overlap ≥ 0.40 (40 % of the bigger entity set shared)
- Same-topic boost: entity_overlap ≥ 0.31 (31 % × 1.3 ≈ 0.40)

### API surface

```
GET /events/{id}/related?limit=5&min_score=0.4
```

Returns a list of `{id, headline, freshness_at, source_count, article_count,
topic, language, outlet_names, score}` ordered by score descending. An empty
list is valid (no related events above threshold).

### Where it lives

- **Curator `api_server.py`** — SQL query against `pages` + `events` + `articles`
- **Reader event page** — "Related events" strip below the evidence rail (3–5 cards)
- **Reader `lib/api.ts`** — `getRelatedEvents(id, minScore?)` helper

---

## Alternatives considered

### Approach B — Event-level embeddings (deferred)

Average the existing `articles.embedding` pgvector vectors for all articles in
an event to produce an `events.embedding` column. Use `<=>` cosine distance with
a pgvector IVFFlat index.

```
score = 0.6 × cosine_similarity(emb_A, emb_B)
      + 0.4 × entity_overlap
```

**Why deferred**: at 240 events the approach A SQL query runs in < 5 ms.
Semantic gaps (e.g., "Fed rate hike" ↔ "inflation crisis" with no shared
entities) are not yet a noticeable product gap. The additional schema
migration + backfill + index creation is not justified at this scale.

**Trigger to ship B**: corpus exceeds ~1 000 published events OR product
review identifies false negatives in the related-events strip. The two
approaches compose: A can be replaced by B scoring without changing the API
contract.

### Full-text search (rejected)

`tsvector` / `websearch_to_tsquery` would catch keyword overlap but is blind to
entity identity ("the president" vs "Díaz-Canel"). Not pursued.

### LLM relation extraction (rejected)

Asking the model "are these two events related?" for every candidate pair is
O(N²) per request and would cost ~$0.01/call × thousands of pairs. Not
appropriate for a read-time request.

---

## Consequences

**Positive**
- Zero schema migration. Deployable today against the live DB.
- < 5 ms query at 240 events; < 50 ms at an estimated 5 000 events.
- Entity overlap is semantically meaningful — same real-world actors = related
  stories.
- Composable: Approach B can wrap or replace the SQL score without changing the
  Reader API contract.
- No new dependency — pure PostgreSQL JSONB operators.

**Negative**
- Blind to semantic similarity without shared entity names. "Inflation concerns"
  and "Fed rate decision" may not match unless both mention "Federal Reserve".
- Performance degrades at ~10 000 events (full table scan per request). At that
  scale, materialise a `related_events` table populated by a nightly job, or
  move to Approach B.
- `pages.entities` is populated by the ENRICH LLM call; events with poor entity
  extraction (short stubs, offline dev mode) may return no related results.

---

## Implementation checklist

- [x] ADR authored (this file)
- [x] `GET /events/{id}/related` added to `Curator/apps/curator/core/api_server.py`
- [x] `getRelatedEvents()` added to `Reader/apps/web/lib/api.ts`
- [x] `RelatedEvent` type added to `Reader/apps/web/lib/types.ts`
- [x] Related events strip added to `Reader/apps/web/app/event/[id]/page.tsx`

---

## Future: Approach B implementation plan (when triggered)

1. **Migration**: `ALTER TABLE events ADD COLUMN embedding vector(1024)`.
2. **Backfill**: for each event, `UPDATE events SET embedding = (SELECT AVG(embedding) FROM articles WHERE event_id = events.id AND embedding IS NOT NULL)`.
3. **Index**: `CREATE INDEX ON events USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`.
4. **Hook**: after `SynthesizeSkill.run()`, compute + store the event embedding.
5. **Score update**: blend cosine similarity with entity overlap in the `/related` query.
6. **Threshold review**: semantic scoring may warrant a lower threshold (e.g., 0.35).
