# ADR-0013 — Story Arc Archive: concluded events + vector timeline pointers

> *Status: proposed · Owner: Julian · Date: 2026-06-07*

## Context

InkBytes events accumulate indefinitely. Once published, an event remains in
`status = 'published'` regardless of whether new articles continue to arrive.
There is no concept of a **concluded story** — a news cycle that has gone quiet.

This creates three downstream problems:

1. **No story lifecycle signal for the Reader**: A page published 3 weeks ago
   with no new coverage looks identical to one published this morning. Users
   have no indication the story is over.

2. **No historical story corpus**: Without a concluded-event concept, there is
   no durable record of how individual news stories evolved over time. This
   blocks future features: "related historical stories", story-arc similarity,
   RAG context from past events, drift detection.

3. **Re-synthesis on stale events**: The synthesis gate fires on new sources,
   not on age. A new article joining a months-old event re-triggers synthesis
   and overwrites the published page with stale context.

## Decision

When a published event's `last_updated_at` is older than **7 days**, mark it
`concluded` and write a `story_arcs` record. The arc stores an ordered list of
**article IDs as pointers** into `articles.embedding` — the existing
1024-dimensional pgvector column — creating a durable, zero-duplication vector
timeline of the story's unfolding.

### Rationale for pointer-only storage

The 1024-dim embeddings already live in `articles.embedding`. Duplicating them
into `story_arcs` would cost ~4 KB × N articles per event per dimension, with
no benefit over querying through the article IDs. Pointers (`TEXT[]`) are the
canonical approach: one integer-sized reference per article, retrievable with a
single `WHERE id = ANY($1::TEXT[])` query in scraped_at order.

Future Sprint 2 work may materialise `centroid_start`/`centroid_end` aggregate
vectors in the same table for fast similarity search — see §Future work below.

### Data model

**Migration 010** adds:

```sql
-- 1. Extend events.status to include 'concluded'
ALTER TABLE events DROP CONSTRAINT IF EXISTS events_status_check;
ALTER TABLE events ADD CONSTRAINT events_status_check
    CHECK (status IN ('draft', 'published', 'dropped', 'concluded'));

-- 2. Story arc archive
CREATE TABLE story_arcs (
    event_id        TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    topic           TEXT,
    language        TEXT NOT NULL,
    first_seen_at   TIMESTAMPTZ NOT NULL,   -- = events.first_seen_at (immutable)
    concluded_at    TIMESTAMPTZ NOT NULL,   -- = events.last_updated_at at archive time
    article_count   INT NOT NULL,
    source_count    INT NOT NULL,
    arc_article_ids TEXT[] NOT NULL,        -- article.id ordered by scraped_at ASC
                                             -- pointers into articles.embedding (vector(1024))
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_story_arcs_topic     ON story_arcs (topic);
CREATE INDEX idx_story_arcs_concluded ON story_arcs (concluded_at DESC);
CREATE INDEX idx_story_arcs_language  ON story_arcs (language);
```

### Replaying the vector trajectory

A consumer walking the story arc executes:

```sql
SELECT a.id, a.scraped_at, a.title, a.embedding
FROM   articles a
WHERE  a.id = ANY($1::TEXT[])   -- pass arc_article_ids
ORDER  BY a.scraped_at;
```

Each row is one step in the story's progression through semantic space. The
embedding column is a `vector(1024)` pgvector value — compatible with cosine
distance, centroid computation, or any downstream ML consumer.

### Event lifecycle state machine (extended)

```
draft        ──(≥2 sources, synthesis)──► published
published    ──(Backoffice manual)──────► dropped
published    ──(last_updated_at > 7d)───► concluded   ← NEW transition
dropped      ──(Backoffice manual)──────► published
concluded    ──────────────────────────► [frozen]     (no further transitions)
```

`concluded` events and their pages remain **fully visible** in the Reader and
API. They are excluded from the active clustering window only indirectly:
the `scraped_at > NOW() - 48h` recency filter in ClusterSkill already prevents
concluded events from attracting new articles, since the event's seed articles
are weeks old.

### ConcludeStoriesSkill (new command --conclude-stories)

Follows the pattern of existing recovery commands (`--synthesize-pending`,
`--reenrich-missing`, `--recluster-event`).

**Trigger options (TBD at implementation):**
- On-demand: `python main.py --config env.yaml --conclude-stories`
- Post-harvest hook in `application._run_scheduled_mode()` (after each cycle)
- Preferred: standalone daily lightweight cron (minimises interference with
  the main harvest worker's memory/CPU budget)

**Pseudocode:**

```python
async def conclude_stories(self, conclude_after_days: int = 7) -> None:
    """Archive events that have gone quiet for conclude_after_days days."""
    cutoff = now_utc - timedelta(days=conclude_after_days)

    # SELECT id, topic, language, first_seen_at, last_updated_at, source_count
    # FROM events
    # WHERE status = 'published'
    #   AND last_updated_at < cutoff
    #   AND id NOT IN (SELECT event_id FROM story_arcs)
    candidates = await self.db.fetch_events_ready_to_conclude(cutoff)

    for event in candidates:
        # SELECT id, scraped_at FROM articles
        # WHERE event_id = $1 ORDER BY scraped_at ASC
        articles  = await self.db.get_event_articles_ordered(event["id"])
        arc_ids   = [a["id"] for a in articles]

        await self.db.create_story_arc({
            "event_id":        event["id"],
            "topic":           event["topic"],
            "language":        event["language"],
            "first_seen_at":   event["first_seen_at"],
            "concluded_at":    event["last_updated_at"],
            "article_count":   len(articles),
            "source_count":    event["source_count"],
            "arc_article_ids": arc_ids,
        })
        await self.db.conclude_event(event["id"])   # UPDATE events SET status='concluded'

        logger.info(
            "CONCLUDED %s | topic=%s | articles=%d | sources=%d | arc_len=%d",
            event["id"], event["topic"], len(articles),
            event["source_count"], len(arc_ids),
        )
```

**New configuration key** (`core/config.py` + hot-reload via `curator_settings`):
```python
conclude_after_days: int = 7    # 0 = feature disabled
```

## Consequences

- Events permanently transition to `concluded`; no re-synthesis will fire on them
- `story_arcs` grows at ~(article_count × text_id_size) bytes per concluded event
  — negligible: avg 8 articles × 26 bytes per ULID = ~208 bytes per arc
- Future queries "find events similar to this arc" require materialising centroid
  vectors — deferred to Sprint 2 (see below)
- Reader and API must handle `status = 'concluded'` without crashing; defensive
  reads already exist (force-dynamic pages, no ISR)

## Alternatives considered

| Option | Rejected because |
|---|---|
| Store full 1024-dim embeddings in story_arcs | ~4 KB × N articles per event; data already in articles.embedding; pointer array is the correct abstraction |
| Materialise centroid_start + centroid_end now | Useful for similarity search but no consumer exists yet; adds complexity before value is validated |
| Delete old events after conclusion | Destroys the vector corpus and page content; recoverable only from S3 archive |
| Automatic re-synthesis exclusion flag on events | Simpler than `concluded` status but doesn't capture the semantic meaning and doesn't enable arc archive |
| `concluded_at` timestamp on events table only (no story_arcs) | Loses the ordered arc structure; `arc_article_ids` is what enables future vector replay |

## Future work (Sprint 2+)

1. **Reader badge**: "This story concluded N days ago" on pages where
   `events.status = 'concluded'`. Requires `events.last_updated_at` in the API
   response (already present in `_decode_event_row`).

2. **Centroid materialisation**: Add to `story_arcs`:
   ```sql
   centroid_start vector(1024),   -- mean(embeddings[:3])
   centroid_end   vector(1024),   -- mean(embeddings[-3:])
   trajectory_dist REAL,          -- cosine_distance(start, end)
   ```
   `trajectory_dist` measures how much the story's framing shifted over its
   lifetime (near 0 = factual update loop; near 1 = story changed character).
   Enables ANN queries: "find concluded stories whose end-centroid is closest
   to this new event's first article" — historical story recommendation.

3. **RAG context injection**: When synthesising a new event, retrieve concluded
   arcs with a similar `centroid_start` and inject their `synthesis_md` as
   historical context in the synthesis prompt.

4. **Arc similarity API**: `GET /arcs/similar?event_id=<id>&limit=5` — returns
   the 5 most similar concluded stories by centroid cosine distance.

## Implementation checklist (Sprint 2)

- [ ] `db/migrations/010_story_arcs.sql`: migration (constraint + table + indexes)
- [ ] `core/config.py`: add `conclude_after_days: int = 0` (disabled by default)
- [ ] `services/database_service.py`: add `fetch_events_ready_to_conclude()`,
      `get_event_articles_ordered()`, `create_story_arc()`, `conclude_event()`
- [ ] `core/application.py`: add `conclude_stories()` and `--conclude-stories` CLI flag
- [ ] `core/api_server.py`: include `status` in events response (guard Reader from
      `concluded` status if not already handled)
- [ ] `Reader/apps/web/lib/types.ts`: add `'concluded'` to event status union type
- [ ] Validation: run `--conclude-stories` on production snapshot;
      verify `arc_article_ids` order + `events.status = 'concluded'` for
      events with `last_updated_at < 7 days ago`
