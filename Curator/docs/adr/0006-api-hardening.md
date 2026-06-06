# ADR-0006 — Curator API Hardening: Bounds, Correctness & Performance (pre-D6)

> *Status: Accepted · Date: 2026-06-06 · Deciders: Julián de la Rosa*
> *Relates to: ADR-0005 (related events), ADR-0004 (config from DB)*

---

## Context

A pre-D6 code review of `core/api_server.py`, `core/application.py`, and
`services/database_service.py` surfaced four correctness/safety issues and
eight improvement opportunities.  All twelve are addressed in a single
pre-deploy sweep.  The service is a FastAPI + asyncpg read API; the corpus
at review time is ~240–500 published events.

---

## Decisions

### D1 — Bound query parameters (`/events?limit`, `/graph` params)

**Decision:** Cap `limit` at 500, `limit_nodes` at 200, `limit_edges` at 500.
Applied with `min(param, cap)` at the start of the handler body.  Module-level
constants (`_MAX_EVENTS_LIMIT`, `_MAX_GRAPH_NODES`, `_MAX_GRAPH_EDGES`) make
the caps visible and easy to adjust.

**Why:** Unbounded caller-supplied values allow a single request to return
millions of rows or trigger a multi-second graph self-join.  Both are DoS-class
risks before public deploy.

**Rejected:** Raising HTTP 422 when the cap is exceeded — silently clamping is
friendlier to existing callers and OpenAPI clients.

---

### D2 — Return 404 from `/events/{id}/related` for unknown IDs

**Decision:** Add a fast `SELECT EXISTS(… WHERE id=$1 AND published_at IS NOT
NULL)` pre-flight before the scoring CTE.  Raise `HTTPException(404)` when
absent.  Both the check and the main query share one acquired connection.

**Why:** Every other endpoint in the API raises 404 for unknown IDs.
Previously `/related` returned `200 []` for any unknown ID, making it
impossible for callers to distinguish "exists, no related events" from "does
not exist."

---

### D3 — Consolidate `/status` from 6 sequential `fetchval` calls to 2 `fetchrow`

**Decision:** Replace six sequential `COUNT(*)` fetchval calls with two
`fetchrow` calls using `COUNT(*) FILTER (WHERE …)` aggregates:
- **Query 1** — articles: total, enriched, embedded in one scan.
- **Query 2** — events + pages: totals, published counts via a `LEFT JOIN`.

**Why:** Six sequential round-trips add ~3 ms of serial latency per `/status`
request.  The Backoffice health dashboard and the pipeline monitor poll this
endpoint frequently.  Two queries collapse the latency without adding complexity.

**Rejected:** Caching the counts in a background task — unnecessary at current
scale; Redis is the right instrument if `/status` becomes a hot path.

---

### D4 — Reset `event_id` and `cluster_distance` on article content change

**Decision:** Add `event_id = NULL, cluster_distance = NULL` to the
`ON CONFLICT DO UPDATE SET` reset block in `upsert_article_raw`, alongside the
existing enrichment-field resets.

**Why:** Migration 006's `content_hash` guard resets enrichment fields
(`topic`, `embedding`, etc.) when a URL's content changes, but previously left
`event_id` and `cluster_distance` intact.  This violated the invariant
`event_id IS NOT NULL ↔ embedding IS NOT NULL` — the article kept its old
cluster assignment while its embedding was NULL, corrupting `events.source_count`
and preventing correct re-clustering.

**The fix restores the invariant:** after a content change, the article
re-enters the ENRICH → CLUSTER → SYNTHESIZE path from a clean state.

---

### D5 — Expose `synths_in_flight` and `reembedding` as `Application` properties

**Decision:** Add `@property synths_in_flight` and `@property reembedding` to
`Application`.  Update `api_server.py` to use them instead of accessing
`app._synth_locks` and `app._reembed_task` directly.

**Why:** `api_server.py` is a separate module.  Accessing `_synth_locks` and
`_reembed_task` (private attributes) from outside the class couples the API
layer to the internal concurrency implementation.  The properties provide a
stable, documented interface that can change internally without touching the
route handlers.

---

### D6 — Prune `_synth_locks` after synthesis completes

**Decision:** After `async with lock:` exits in `_synthesize_once`, pop the
lock entry from `_synth_locks` when `not lock.locked()`.

**Why:** `_synth_locks` grows by one entry per unique event ID.  In a
long-running deployment this is a slow unbounded memory leak — every synthesized
event leaves a `asyncio.Lock` in the dict forever.

**Why it is safe:** asyncio runs on a single thread.  `async with lock:` releases
the lock and then immediately executes the next statement (`pop`) with no `await`
between them.  No other coroutine can acquire the lock in that window.  Callers
that hit `lock.locked()` skip rather than waiting, so the lock entry has no
waiters once synthesis is complete.

---

### D7 — Extract `_run_reenrich` to eliminate the duplicated loop body

**Decision:** Extract the 59-line `asyncio.Semaphore` + `gather` loop that was
duplicated verbatim between `run_reenrich_missing` and `run_reenrich_stubs` into
a private `_run_reenrich(rows, label)` helper.  Both public methods become
3-liners.

**Why:** The two methods were semantically different in *what they fetch* but
identical in *how they process* the rows.  A single helper parameterised by
`label` eliminates the duplication so any future change (checkpointing, progress
reporting, concurrency tuning) is made once.

---

### D8 — Split `fetch_articles_for_embedding` f-string SQL into two branches

**Decision:** Replace the f-string `WHERE {where}body_text IS NOT NULL` with
an explicit `if only_missing:` branch issuing two separate string-literal
queries.

**Why:** The f-string is not a SQL injection risk (`only_missing` is a bool,
not user input), but it trips static-analysis tools, makes the two query shapes
implicit, and hides opportunities to add per-branch query hints or comments in
the future.

---

### D9 — Add `Cache-Control` headers to `/events` and `/graph`

**Decision:**
- `GET /events` → `Cache-Control: public, max-age=30`
- `GET /graph`  → `Cache-Control: public, max-age=120`

**Why 30 s for `/events`:** Synthesis fires at most once per new source joining
an event.  A 30-second stale window is invisible to users and allows an Nginx
reverse proxy (the D6 deployment topology) to absorb repeated feed-page loads
without hitting Postgres.

**Why 120 s for `/graph`:** The entity co-occurrence graph changes on a
hours-to-days timescale.  The 2-minute cache window is safe and the graph CTE
is the heaviest query in the API.

**Why `public`:** Both endpoints are unauthenticated read endpoints.  `public`
permits a CDN or reverse proxy to cache, which is the intended D6 deployment
pattern.

---

### D10 — Document `/status` LLM config exposure; defer auth to D6b

**Decision:** No code change in this sweep.  Auth for `/status` is a D6b infra
ticket.

**Why deferred:** `/status` exposes `llm.provider`, models, and `base_url`.
These are non-secret configuration values — no API keys are exposed (keys are
env-only by ADR-0004).  The risk is low-severity information disclosure.  The
auth mechanism decision (Basic Auth / Bearer / IP allowlist) is out of scope for
this hardening sweep and requires a separate decision before `inkbytes.app` goes
public.

---

## Consequences

**Positive**
- API surface is bounded: no request can trigger runaway DB scans.
- `/events/{id}/related` is consistent with the rest of the API's 404 contract.
- `/status` DB load reduced by ~67% (2 queries instead of 6) under monitoring polling.
- `event_id IS NOT NULL ↔ embedding IS NOT NULL` invariant is enforced by the DB layer.
- `_synth_locks` no longer leaks memory in long-running deployments.
- Internal state accessed through clean `@property` interface — no cross-module `_private` access.
- Cache headers enable Nginx caching at D6 without further changes.
- Duplicate reenrich loop body is eliminated — one place to maintain.
- SQL in `fetch_articles_for_embedding` is explicit and safe for static analysis.

**Trade-offs**
- The 404 pre-flight in `/events/{id}/related` adds one PK-indexed `EXISTS` lookup
  (~0.1 ms) before the scoring CTE.  Negligible at current scale.
- Query 2 in `/status` uses a `LEFT JOIN pages` rather than a bare `COUNT FROM events`.
  The join is indexed (PK + FK) and saves a third round-trip; acceptable.
- `Cache-Control: public` means a misbehaving CDN could cache error responses.
  Mitigated: the header is set before the DB query in each handler, so FastAPI's
  exception middleware strips the response headers on HTTPException paths.

---

## Implementation checklist

- [x] `database_service.py` — reset `event_id` + `cluster_distance` on content change (D4)
- [x] `database_service.py` — split f-string SQL in `fetch_articles_for_embedding` (D8)
- [x] `application.py` — add `synths_in_flight` + `reembedding` properties (D5)
- [x] `application.py` — prune `_synth_locks` after synthesis (D6)
- [x] `application.py` — extract `_run_reenrich` helper (D7)
- [x] `api_server.py` — add `Response` import; module-level `_decode_json_col` constant caps
- [x] `api_server.py` — use `app.synths_in_flight` + `app.reembedding` in `/status` (D5)
- [x] `api_server.py` — consolidate `/status` to 2 queries (D3)
- [x] `api_server.py` — cap `/events?limit` at 500 + `Cache-Control: max-age=30` (D1, D9)
- [x] `api_server.py` — cap `/graph` node/edge limits; `Cache-Control: max-age=120` (D1, D9)
- [x] `api_server.py` — 404 guard in `/events/{id}/related` (D2)
- [x] `api_server.py` — remove inline `_decode`; use module-level `_decode_json_col`
- [ ] D6b infra ticket — gate `/status` with auth before `inkbytes.app` goes public (D10)
