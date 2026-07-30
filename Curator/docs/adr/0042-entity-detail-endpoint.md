# ADR-0042 — `GET /entities/{name}` single-entity detail endpoint

> *Status: **accepted / shipped** (index + scoped query + timeout) · Owner: Julian · Last updated: 2026-07-30*

## Context

The Reader's event page shows an "Entities in this story" drawer; tapping an
entity should open a detail sheet in place (stats · recent events · connections)
— the prototype's `entOpen` (Reader ADR-R-0013).

That data lives in the entity graph, but `GET /graph` is a **heavy (~20 s),
balanced-network query** (per-type quotas, full co-occurrence edges, all nodes'
pages) that the app deliberately loads only on the dedicated `/entities` page
(behind a loading screen, cached via the Reader's SWR wrapper — ADR-R-0004/0010).
Loading it on every event page, or on tap, is not acceptable. There is also no
per-entity endpoint, so the Reader had been deep-linking to `/entities?e=` (a
navigation away from the story) to reach the rich detail.

## Decision (design — the intended endpoint)

Add `GET /entities/{name}` — a **scoped single-entity slice** of the same
published-events → `articles.entities` model `/graph` uses, filtered to one
`name_key` (the lowercased entity name). It returns:

- `event_count` (stories), `today_count` (distinct events with `freshness_at`
  in the last 24 h), `connection_count` (distinct co-occurring entities),
- `recent_events` — up to 15 freshest pages the entity appears in
  (`id`, `headline`, `source_count`, `freshness_at`),
- `connections` — up to 15 top co-occurring entities by shared-event weight
  (`id`, `label`, `weight`),
- `type` (dominant type, same PERSON>ORG>LOC>EVENT>OTHER tiebreak as `/graph`),
  `label`, and the Commons `image`/`description`/attribution from `entity_media`.

`404` when the entity isn't in any published event. `Cache-Control: max-age=120`.

The Reader proxies it via a `GET /api/entity/[id]` route handler (the browser
can't reach the internal Curator host — same pattern as `/api/ask`); the
event-page `EntityDetailSheet` fetches it on open and **degrades to a light
sheet on 404**.

## The performance problem (and how it was solved)

An initial attempt was **deferred** because the query was too slow: prod
validation (read-only `psql`) measured a **global** first cut at **~37 s** for
Donald Trump (unbounded `connection_count` = 84 391), a **scoped** rewrite
(`target_events`-first, connections capped to top-15) at **~7 s** for Trump, and
even OPEC (**14 events**) at **~3.8 s**. Root cause: `entities` (≈3.08 M rows /
663 MB) had **no functional index on `LOWER(name)`**, so every `LOWER(ent.name)
= $1` lookup **seq-scanned** the whole table — the planner started from all
published pages and filtered per-article, instead of starting from the entity.

**The fix — two parts:**

1. **Functional index** `idx_entities_name_lower ON entities (LOWER(name))`
   (migration 025). On prod it was built **`CONCURRENTLY`** out-of-band (11.5 s,
   42 MB, no table lock); the migration guard skips it there and only creates it
   on fresh/dev DBs (small tables → instant).
2. **`ANALYZE entities`** — the planner won't pick a just-created *expression*
   index until its stats exist. This was the real unlock: before ANALYZE the
   index was ignored and the query stayed ~3–8 s; after, the planner uses it.

Post-fix timings (index + ANALYZE, scoped `target_events AS MATERIALIZED`):

| Entity | Events | Before | After |
|---|---|---|---|
| OPEC | 14 | ~2.9 s | **316 ms** ✅ |
| Brent Crude | 51 | ~3.3 s | **459 ms** ✅ |
| Donald Trump | 1 935 | ~7–8 s | **~8 s** (mega-entity — inherent) |

So **normal/mid entities answer in <500 ms** (rich sheet). The handful of
mega-entities (Trump, and similar top nodes) are still heavy because the
co-occurrence aggregation runs over ~1 900 events; a **2.5 s `fetchrow`
timeout** cuts them → `404` → the Reader's light fallback. A precomputed
per-entity rollup (aligned with the parked ADR-0039 graph matviews) would make
even those instant — a future optimisation, not required for the common case.

## What SHIPS (2026-07-30)

- `GET /entities/{name}` re-added to `api_server.py` — scoped query
  (`target_events AS MATERIALIZED` → `ev_meta` / `conns` / `dtype`), top-15
  capped connections, `entity_media` join for the Commons photo, and the 2.5 s
  timeout. `import asyncio` at module level for the `except asyncio.TimeoutError`.
- Migration **025** creates the functional index (fresh/dev) + `ANALYZE`.
- The Reader's **in-place `EntityDetailSheet`** + `GET /api/entity/[id]` proxy
  are unchanged: on a `200` they render the **rich** sheet (stats · recent
  events · connections); on the proxy's `{ available: false }` (any non-200 from
  Curator — mega-entity timeout or an entity not in a published event) they
  render the **light** fallback. No client change was needed.

## Follow-up

- **Mega-entity rollup** (optional): precompute per-entity stats in a matview
  refreshed on a schedule (ADR-0039 graph-rollup pattern) so Trump-class entities
  answer instantly too, and drop the timeout.
- Per org policy the AI-generated SQL (this endpoint + migration 025) still owes
  a documented human review + SAST pass.
