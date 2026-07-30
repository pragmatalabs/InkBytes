# ADR-0042 — `GET /entities/{name}` single-entity detail endpoint

> *Status: **deferred** (design accepted; endpoint NOT shipped — needs a supporting index) · Owner: Julian · Last updated: 2026-07-30*

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

## ⚠️ Why it is DEFERRED (not shipped in the 2026-07-30 deploy)

Pre-deploy validation against **prod data** (read-only `psql`) found the query is
too slow to ship without a supporting index — exactly the check that saved us
from shipping a 37 s endpoint:

| Version | Entity | Wall time | Notes |
|---|---|---|---|
| Global (`published`+`ev_ents`, as first committed in 42a9551) | Donald Trump | **~37 s** | `connection_count` = 84 391 (unbounded co-occurrence) |
| Scoped (`target_events`-first, `connection_count` capped to top-15) | Donald Trump | **~7 s** | still too slow |
| Scoped | OPEC (**only 14 events**) | **~3.8 s** | a *tiny* entity still costs ~3.8 s |

Root cause: `entities` has **no functional index on `LOWER(name)`** (and the
co-occurrence aggregation joins `entities`→`articles` by `event_id`), so every
lookup **sequential-scans the large `entities` table**. Scoping the query and
capping `connection_count` fixes the mega-entity blow-up, but the base per-entity
cost stays ~3.8 s — so a `timeout` guard (which I trialled at 3.5 s) would 404
*almost everything*, making the endpoint effectively useless.

The correct fix is a **migration adding a functional index** on
`entities (LOWER(name))` — and likely a supporting index for the
`event_id`-scoped co-occurrence aggregation — created `CONCURRENTLY` (the
`entities` table is large; a plain `CREATE INDEX` would lock harvest/enrich
writes). That is real, careful migration work, not a pre-deploy hotfix, so the
endpoint is deferred until it lands.

## What SHIPS now (2026-07-30)

- The Reader's **in-place `EntityDetailSheet`** + `GET /api/entity/[id]` proxy
  (committed in 42a9551) stay. With no Curator endpoint the proxy returns
  **`200 { available: false }`** (NOT a 404 — that put a red error on every entity
  tap in the console; fixed 2026-07-30) and the sheet renders its **light
  fallback** — entity name + type + a "View full profile →" link into
  `/entities?e=`. Tapping an entity now opens a sheet in place instead of
  navigating away; the rich stats fill in **for free, with no client change**,
  once the endpoint + index ship (the proxy then returns the real detail and the
  client shows the rich sheet).
- The Curator `get_entity` handler was **removed** from `api_server.py` so no
  slow/index-starved route reaches prod.

## Follow-up (to make it shippable)

1. Migration: `CREATE INDEX CONCURRENTLY … ON entities (LOWER(name))` (+ review
   the `articles(event_id)` / `entities(article_id)` indexes for the co-occurrence
   join).
2. Re-add the **scoped** `get_entity` (target_events-first, top-15 capped
   connections). Re-validate on prod: a small entity should be well under ~200 ms
   with the index; re-check a mega-entity (Trump) stays bounded.
3. Then human review + SAST pass on the AI-generated SQL per org policy, and
   flip this ADR back to `accepted`.
