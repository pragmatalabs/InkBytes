# ADR-0007 — --synthesize-pending CLI mode for synthesis backfill

> *Status: accepted · Owner: Julian · Date: 2026-06-07*

## Context

After restarts or bulk re-ingests the Curator worker's in-memory
`_last_synth_source_count` dict is cleared.  Events that already have ≥ 2 distinct
outlet sources but no published page (because synthesis was skipped during the original
ingest or across a restart boundary) accumulate silently.

On 2026-06-07 this produced **511 events with ≥ 2 sources and no page** that the
running worker would never pick up without new articles arriving for those events.

The existing `--reenrich-missing` mode re-runs the full ENRICH→EMBED→CLUSTER→SYNTHESIZE
pipeline — too expensive and slow for events that are already fully enriched and clustered.

## Decision

Add `--synthesize-pending` one-shot CLI mode that:
1. Queries `events` where `COUNT(DISTINCT a.outlet_id) >= 2` and no corresponding `pages` row exists.
2. Calls `self.synthesize.run(event_id)` for each (skips ENRICH/EMBED/CLUSTER entirely).
3. Passes `source_count=0` to `_synthesize_once()` to bypass the in-memory source-count gate.
4. Logs `synthesize-pending [N/total] event=X sources=Y` for each.
5. Exits when done (one-shot, not a daemon).

## Usage

```bash
# On server — one-time backfill
docker run --rm \
  --network inkbytes_inkbytes-internal \
  --env-file infra/.env \
  -e DATABASE_URL=... \
  -e RABBITMQ_URL=... \
  ghcr.io/pragmatalabs/inkbytes-curator:latest \
  python main.py --config env.yaml --synthesize-pending
```

Also available via `make shell-curator` and running locally.

## When to use

- After a Curator restart that clears the in-memory gate.
- After a bulk `--reenrich-missing` run that re-clusters articles.
- After manually inserting articles directly into the DB.
- As a scheduled maintenance task (idempotent — events with pages are excluded).

## Implementation

`Curator/apps/curator/services/database_service.py` — `fetch_events_pending_synthesis()`:
```sql
SELECT e.id, COUNT(DISTINCT a.outlet_id) AS source_count
FROM events e
JOIN articles a ON a.event_id = e.id
WHERE NOT EXISTS (SELECT 1 FROM pages p WHERE p.event_id = e.id)
GROUP BY e.id
HAVING COUNT(DISTINCT a.outlet_id) >= 2
ORDER BY source_count DESC
```

`Curator/apps/curator/core/application.py` — `run_synthesize_pending()`:
iterates results, calls `_synthesize_once(event_id, 0)`, logs progress.

`Curator/apps/curator/main.py` — adds `--synthesize-pending` to argparse,
routes to `app.run_synthesize_pending()`.

## Alternatives considered

- **Publish RabbitMQ `event.resynthesize` messages** — requires knowing which event IDs;
  same query needed, extra RabbitMQ round-trip.
- **Auto-synthesize on worker startup** — rejected; startup time grows with DB size,
  and re-synthesizing everything on every restart is wasteful.
- **Periodic cron** — considered; deferred until synthesis backlog becomes routine.
