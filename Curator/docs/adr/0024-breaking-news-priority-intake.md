# Curator ADR-0024 — Breaking-news priority intake + cluster-velocity detector

> *Status: accepted · Owner: Julian · Date: 2026-06-11*

## Context

Messor's pulse lane (Messor ADR-0017) delivers articles from the 10
highest-signal outlets within ~5 minutes of publication, flagged with AMQP
`priority=9`. Curator must (a) process those messages ahead of the regular
backlog, and (b) decide which events are actually *breaking* so later phases
(breaking synthesis persona, Reader rail) can treat them specially.

Keyword-based detection ("BREAKING:" in titles) is locale-dependent and
gameable. The signal that actually defines breaking news is **velocity**:
multiple top outlets publishing the same story within a short window.

## Decision

### 1. Priority queue

`curator.articles-scraped` is declared with `arguments={"x-max-priority": 10}`.
RabbitMQ then delivers priority-9 (pulse) messages before priority-0
(cycle) messages whenever the queue has a backlog. Enrichment itself is
unchanged (same model, same prompt) — the special treatment is *latency*,
not quality. The ADR-0015/0018 dedup fast-path already bounds cost.

**Migration gotcha**: RabbitMQ refuses to redeclare an existing queue with
different arguments (`PRECONDITION_FAILED`). The consumer handles this
gracefully: on precondition failure it reopens the channel, declares the
queue *without* priority args, and logs a warning. To enable priority on an
existing deployment: wait for the queue to drain (or accept loss), then
`rabbitmqadmin delete queue name=curator.articles-scraped` (or via mgmt UI)
and restart the worker — the next declare creates it priority-enabled.
Until then the pipeline runs exactly as before.

### 2. Breaking detector (cluster velocity)

At cluster-attach time (`ClusterSkill.run`, attach branch only — a 1-source
event can't be breaking), one SQL statement:

```sql
UPDATE events e
   SET breaking_at    = NOW(),
       breaking_until = NOW() + interval '2 hours'
 WHERE e.id = $1
   AND e.breaking_at IS NULL                          -- fire once
   AND e.first_seen_at > NOW() - interval '60 minutes' -- young story
   AND (SELECT COUNT(DISTINCT a.outlet_id)
          FROM articles a JOIN outlets o ON o.id = a.outlet_id
         WHERE a.event_id = e.id AND o.pulse) >= 2     -- ≥2 pulse outlets
```

An event is **breaking** iff ≥2 distinct pulse outlets published it within
60 minutes of the cluster's first sighting. This inherently preserves the
≥2-source publish bar — no single-outlet story is ever flagged.

- `breaking_window_minutes` (60) and `breaking_ttl_hours` (2, per Julian
  2026-06-11) live in `ClusterCfg`; `breaking_window_minutes=0` disables
  detection.
- `breaking_until` is the auto-demotion deadline: 2 h after detection the
  event rejoins normal ranking. Phases 3+4 (breaking synthesis persona,
  Reader rail) consume these columns; nothing else changes in this phase.

### Schema (migration 014)

```sql
ALTER TABLE events  ADD COLUMN breaking_at    TIMESTAMPTZ;  -- NULL = never flagged
ALTER TABLE events  ADD COLUMN breaking_until TIMESTAMPTZ;
ALTER TABLE outlets ADD COLUMN pulse BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX idx_events_breaking ON events(breaking_until) WHERE breaking_until IS NOT NULL;
```

## Alternatives considered

| Option | Rejected because |
|---|---|
| Separate breaking queue + dedicated consumer | Two consumers competing for one Ollama (prefetch=1 exists precisely to serialize embeddings); priority on one queue gives the same ordering with no concurrency change |
| Title-keyword detection | Locale-dependent (EN/ES), outlet-dependent, gameable; velocity is observable ground truth |
| Flag in message payload deciding "breaking" at ingest | A single article can't be breaking — breaking is a property of the *cluster*, only observable after ≥2 sources attach |
| Allow 1-source breaking pages ("developing") | Violates the ≥2-source quality bar; a wrong single-source page on the breaking rail is the worst possible failure mode |

## Phases 3+4 (deferred, agreed 2026-06-11)

- `prompts/synthesize_breaking.md` persona ("what we know / what's
  unconfirmed", timestamps, no speculation); re-synthesis at source counts
  2→3→5 then every +3 sources or 30 min (whichever is less frequent).
- Reader breaking rail: top of feed, max 5, ordered by recency of
  `breaking_at`, red pulse badge, demote at `breaking_until`.
