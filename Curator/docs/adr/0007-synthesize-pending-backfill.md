# ADR-0007 — `--synthesize-pending`: backfill events missing synthesis

> *Status: Accepted · Owner: Julian · Date: 2026-06-07*

## Context

After a bulk re-ingest (e.g. the initial 7,500-article load) or after server restarts
that reset the in-memory `_last_synth_source_count` dict, events can accumulate with
≥2 distinct-outlet sources but no published page. The worker won't synthesize them
because:

1. No new article arrives to trigger the `_synthesize_once()` path.
2. The in-memory gate (`_last_synth_source_count`) resets to `{}` on restart — but
   if no NEW article arrives for a given event, the gate is never checked.

Querying production found **511 events with ≥2 sources and no page** after the
Hostinger migration.

## Decision

Add a `--synthesize-pending` one-shot CLI mode to Curator that:

1. Queries `public.events` for events with `COUNT(DISTINCT outlet_id) >= 2` that have
   no row in `public.pages`.
2. Calls `self.synthesize.run(event_id)` for each, ordered by `source_count DESC`
   (richest events first).
3. Bypasses the in-memory `_last_synth_source_count` gate by passing `source_count=0`
   to `_synthesize_once()` — valid because these events were **never** synthesized, not
   re-synthesized.
4. Logs progress `[N/total] event=... sources=...` and a completion summary.

## Implementation

- `DatabaseService.fetch_events_pending_synthesis()` — SQL query with `HAVING COUNT(DISTINCT a.outlet_id) >= 2` and `NOT EXISTS (SELECT 1 FROM pages WHERE event_id = e.id)`.
- `Application.run_synthesize_pending()` — iterates rows, calls `_synthesize_once(event_id, 0)`, catches per-event errors.
- `main.py` — `--synthesize-pending` arg wired to `run_synthesize_pending()`, same startup as `--reenrich-missing` (needs DB, no FastAPI port).

## Usage

```bash
# Run on server (one-shot, exits when done)
docker run --rm \
  --network inkbytes_inkbytes-internal \
  --env-file infra/.env \
  -e DATABASE_URL="..." -e RABBITMQ_URL="..." \
  ghcr.io/pragmatalabs/inkbytes-curator:latest \
  python main.py --config env.yaml --synthesize-pending
```

## Consequences

**Good:** Clean backfill without re-enriching articles (no LLM cost for enrichment).
Synthesis cost only (deepseek-reasoner per event).

**Watch out:** Running `--synthesize-pending` while the worker is also consuming
from RabbitMQ is safe — synthesis uses independent DB writes. The in-memory gate in
the running worker is not shared with the one-shot process.

## Alternatives considered

**Trigger re-synthesis via Backoffice moderation commands** — would require clicking
511 individual "Re-synthesize" buttons. Not practical.

**Modify `--reenrich-missing` to also synthesize** — it already does (via `_reenrich_article`),
but re-enrichment re-runs the full LLM enrich call unnecessarily when articles are
already enriched. `--synthesize-pending` skips straight to synthesis.
