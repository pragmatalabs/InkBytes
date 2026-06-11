# Messor ADR-0017 — Breaking-news pulse: 5-minute RSS poll over flagged outlets

> *Status: accepted · Owner: Julian · Date: 2026-06-11*

## Context

The scheduled harvest runs every ~2 hours. A story that breaks right after a
cycle waits up to 2 hours before Messor even sees it, plus enrich/cluster/
synthesize time. For breaking news that latency is the product gap: readers
check other apps first.

RSS-first harvesting (ADR-0013, fixed and verified live 2026-06-11) makes a
much tighter loop affordable: one feed fetch is a single ~200 ms XML request,
so polling the 10 highest-signal outlets every 5 minutes costs ~10 requests
per pulse (~2,880/day) — negligible against a single homepage crawl.

## Decision

Add a **pulse lane** beside the existing scheduled cycle:

1. **`pulse` flag per outlet** (`public.outlets.pulse BOOLEAN DEFAULT FALSE`),
   following the ADR-0016 per-outlet config pattern (Curator migration →
   Pydantic field → `SCRAPER_FIELDS` → Backoffice CRUD). Pulse outlets MUST
   have a verified `feed_url` — the pulse never falls back to newspaper3k
   (a homepage crawl takes 30–90 s/outlet and would destroy the cadence).
2. **Pulse scheduler**: a daemon thread started in scheduled mode, firing
   every `MESSOR_PULSE_INTERVAL_MINUTES` (env var → `scraping.pulse_interval_
   minutes` in env.yaml → default 5; `0` disables). Each tick scrapes only
   `pulse=true` outlets via the normal pipeline with `feed_only=True`.
3. **Priority publish**: pulse runs publish their per-article
   `event.article.scraped` messages with AMQP `priority=9` (normal cycle
   = unset/0). Curator's consume queue is priority-enabled (Curator
   ADR-0024), so pulse articles jump the enrich queue. The
   `inkbytes.article.v1` payload is unchanged — priority is transport
   metadata, not contract.
4. **Locking**: the pulse reuses the global scraping lock with
   `blocking=False` — if a full cycle is running, the pulse tick is skipped
   (the full cycle covers those outlets anyway; only the priority hint is
   lost). To prevent the inverse starvation (a <60 s pulse holding the lock
   exactly when the 2-hour cycle fires, which previously meant the whole
   cycle was skipped), the scheduled loop now retries the lock up to 5×
   at 60 s intervals before giving up.

Seeded pulse outlets (10 — all with droplet-verified feeds, 2026-06-11):
`bbc, aljazeera, theguardian, npr, latimes, cnbc, infobae, clarin,
lanacionar, eluniversalmx`.

## What the pulse does NOT do

- No newspaper3k fallback (`feed_only=True` — a failed feed fetch = skip
  outlet until next tick).
- No new dedup machinery: the existing per-run staging files + 7-day
  known-URL window make a quiet tick publish nothing and cost nothing.
- No "breaking" decision: Messor stays a pure harvester (ADR-0005). The
  breaking determination is cluster velocity, computed by Curator
  (ADR-0024).

## Consequences

- A story published by a pulse outlet is in RabbitMQ within ≤5 min + feed
  propagation, with priority 9.
- Worst-case extra load: 10 feed fetches per 5 min + downloads for genuinely
  new articles only. No newspaper3k memory spikes (RSS path never builds a
  paper object).
- During a full cycle (~25 min today) pulse ticks are skipped — acceptable;
  the cycle itself harvests the pulse outlets. If cycles get longer this
  needs per-outlet locking (deferred).
- The Backoffice can flip `pulse` per outlet live; the next tick picks it up
  (outlets are re-fetched from the Curator API each run).
