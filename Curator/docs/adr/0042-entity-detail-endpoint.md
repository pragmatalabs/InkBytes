# ADR-0042 — `GET /entities/{name}` single-entity detail endpoint

> *Status: accepted · Owner: Julian · Last updated: 2026-07-29*

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

## Decision

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

`404` when the entity isn't in any published event. `Cache-Control: max-age=120`
(same as `/graph`). Because it filters to one entity, it avoids the balanced
per-type ranking + full pairwise edge build that make `/graph` slow.

The Reader proxies it via a `GET /api/entity/[id]` route handler (the browser
can't reach the internal Curator host — same pattern as `/api/ask`); the
event-page `EntityDetailSheet` fetches it on open and **degrades to a light
sheet on 404** (so nothing breaks before this endpoint is deployed, or for
entities outside the graph).

## Consequences

- The inside-news entity detail opens **in place** (a stacked sub-sheet over the
  story) instead of navigating to `/entities`.
- Read-only + isolated: a bug in this endpoint fails only this one route (Reader
  falls back to the light sheet); it does not touch the enrich→cluster→
  synthesize pipeline or existing endpoints.
- The query reuses `/graph`'s `published` + `ev_ents` CTE shape, so its
  correctness tracks `/graph` (same dedup: one row per `(event_id, name_key)`).

## Verification note (⚠️)

Shipped `py_compile`-clean but **the SQL was validated against prod data before
deploy** (a read-only `psql` run of the query for a sample entity) rather than
in local dev — local Curator has no representative data, and the prod Curator (the
Reader dev tunnel target) did not yet have the route. Per the org policy this
AI-generated endpoint should also get a documented human review + SAST pass.
