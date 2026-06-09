# ADR-0014 — Per-Run Staging Files (stop publish amplification)

> *Status: accepted · Owner: Julián · Last updated: 2026-06-09*

## Context

On **2026-06-09** the `curator.articles-scraped` queue accumulated a
**105 143-message backlog** that had to be purged manually. Messor production
logs were full of:

```
Staging file not found for event publish: data/scrapes/1780963200.wired.db.json
```

This looked like a recurrence of [ADR-0012](./0012-staging-volume-and-url-dedup-window.md)
(staging dedup state wiped → everything re-published). Investigation showed it
was **two compounding causes**, only one of which ADR-0012 addressed.

### Trigger — the ADR-0016 migration wiped the dedup volume

The [ADR-0016](../../../Curator/docs/adr/0016-object-store-consolidation-and-embedding-durability.md)
MinIO→DO Spaces migration removed the `inkbytes-minio-data` named volume. The
teardown that removed it (`docker compose down -v` / `docker volume prune`) also
destroyed `inkbytes-messor-scrapes`, wiping **all** URL-dedup history. This is
*exactly* the failure ADR-0012 §"Risk: named volume deleted manually" predicted.

The volume **mount** was never broken — `docker inspect inkbytes-messor` still
shows `inkbytes_inkbytes-messor-scrapes → /app/apps/scraper/data/scrapes`, and a
container restart preserves the files (verified: 41 files, identical md5 before
and after `docker restart`). Only the volume's *contents* were lost, once, on
migration day. Evidence: the volume holds staging files from **only Jun 8 and
Jun 9** — everything older was gone.

### Root cause — per-DAY staging files re-published in full every cycle

This is the part ADR-0012 missed. Two Messor dedup layers disagree:

| Layer | What it counts | Behaviour |
|---|---|---|
| **Session** (`scrape.session.completed`) | `successful_articles` — only articles newly accepted *this run* | Correct. Logs "N new articles". |
| **Publish** (`_publish_articles_from_staging_file`) | Every record in the staging **file** | Re-reads and re-emits the **entire file** each cycle. |

The staging filename was `generate_today_timestamp()` → **midnight UTC**, i.e.
**one file per outlet per day**. All 4 daily cycles wrote to the same
`<midnight>.<outlet>.db.json`, so the file *accumulated* the whole day's new
articles. But the publish step re-reads the **whole file every cycle**:

```
cycle 1: file=50 new        → publish 50
cycle 2: +5 new → file=55   → publish 55  (50 already sent + 5)
cycle 3: +5 new → file=60   → publish 60
cycle 4: +5 new → file=65   → publish 65
```

→ **230 events emitted for 65 unique articles in one day** even when dedup works
perfectly. After the volume wipe, dedup found *everything* new, so the day-files
ballooned to multi-MB (Jun 8: `theguardian` 12 MB, `clarin` 9.9 MB, `cnbc`
9.4 MB) and each cycle re-published the entire growing file — turning ADR-0012's
bounded ~1 540-msg re-flood into the **105 143-msg** flood observed.

### Why "Staging file not found" is benign (the dedup-layer inconsistency)

The warning is **not** an error — it is the symptom of *healthy* dedup. A
staging file is only written when a run produces ≥1 NEW article (`StagingStore`
flushes on insert). Once URL-dedup catches up, an outlet often yields **0 new**
articles in a cycle, so the new day's file is never created — and the publish
step, expecting `<today>.<outlet>.db.json`, logs "not found." The session layer
correctly reported "0 new"; the publish layer naively expected a file. The two
layers were reconciled by this ADR.

---

## Decision

### Fix — staging files are per-RUN, not per-day

`core/scraper.py::process_outlet_articles` now names the staging file with a
**per-run** Unix timestamp (`int(time.time())`) instead of
`generate_today_timestamp()` (midnight):

```python
run_ts = int(time.time())
self.session.set_results_staging_file_name(f"{run_ts}.{outletBrand}.db.json")
```

Each cycle gets its **own** file containing **only that run's new articles**
(post URL-dedup). Re-publishing that file therefore emits **only-new** — never
the cumulative history. This aligns the code with `staging_store.py`'s own
documented intent ("Per-cycle staging store … articles for a single scraping
session").

Cross-run and cross-day dedup are **unchanged**: `load_known_article_urls()`
still scans every staging file in the 7-day window (ADR-0012), so an article
seen in an earlier run/day is still skipped without a fetch or publish.

### Fix — "Staging file not found" is now INFO, not WARNING

`storage_service._publish_articles_from_staging_file` logs the missing-file case
at INFO with a clear message ("0 new articles this run — nothing to publish"),
since it is the expected healthy outcome.

---

## Consequences

| Metric | Before (per-day file) | After (per-run file) |
|---|---|---|
| Events per outlet/day at steady state | ~2–4× unique (whole file re-sent each cycle) | 1× unique (only-new) |
| Events after a volume wipe | Multiplicative flood (105k observed) | One-time re-scrape of current homepage (~1 outlet-cycle's worth), bounded |
| Staging file size | Grows all day (multi-MB) | One cycle's new articles (≤ a few hundred KB) |
| Files on disk (capped by 30-day prune) | ~22 × 30 = 660 | ~22 × 4 × 30 = 2 640 (still pruned) |
| `Staging file not found` log noise | WARNING on every 0-new outlet | INFO, expected |

### Defence in depth vs. the original trigger

This fix does **not** prevent a future volume wipe — that remains an operational
rule (below). What it does is make a wipe *survivable*: even with dedup history
gone, each cycle now re-publishes at most one run's freshly-scraped articles
(bounded by the outlet article cap), not a day-accumulated, whole-file-replayed
flood. The 68× amplification is removed.

### Operational rule (runbook)

When removing a named volume during a migration, **target it explicitly** —
`docker volume rm inkbytes_inkbytes-minio-data` — never `docker compose down -v`
or `docker volume prune` on the prod stack, which also destroy
`inkbytes_inkbytes-messor-scrapes` (and any other dedup/state volume). Recall the
Compose project-prefixed name (`inkbytes_<volume>`), per ADR-0012 §"Pre-deploy
volume seeding order".

### Enforced guardrail (2026-06-09) — external volumes

The runbook rule above is now backed by configuration. In
`infra/docker-compose.prod.yml`, the two stateful volumes are declared
`external: true` with `name:` pinned to the existing project-prefixed volumes:

```yaml
volumes:
  inkbytes-postgres-data:
    external: true
    name: inkbytes_inkbytes-postgres-data
  inkbytes-messor-scrapes:
    external: true
    name: inkbytes_inkbytes-messor-scrapes
```

Compose never deletes a volume it does not own, so **`docker compose down -v`
can no longer destroy these** — the exact command that caused this incident is
now inert against them. `name:` pins the *existing* physical volume, so the
change moves no data. `infra/deploy.sh` creates them (idempotently) before
`compose up`, because Compose errors on a missing external volume: a fresh host
gets empty ones, an existing host is a no-op.

**Residual gap (deliberately not closed here):** a blanket `docker volume prune`
issued while the whole stack is *stopped* can still remove them (they become
dangling). The durable fix for that is managed storage (DO Managed Postgres +
Spaces) so production data never lives in droplet-local volumes — deferred to
post-MVP. `rabbitmq-data` was intentionally left internal: a lost queue is
self-healing (Messor re-publishes), and the per-run-staging fix above bounds the
re-publish.

---

## Alternatives considered

### Publish only `self.processed_articles` from the day-file (keep per-day files)

Filter the publish to the IDs newly staged this run, keeping one file per day.
Rejected: more invasive (thread new-article IDs from `process_outlet_articles`
through `ScrapingSession` into `storage_service`), and the multi-MB day-file
remains (full re-read each cycle for dedup + publish). Per-run files solve the
size and the amplification together with a single-line naming change.

### Move dedup state to Postgres

Durable and wipe-proof, but crosses the ADR-0005 responsibility boundary
(Messor must not depend on Curator's DB) and adds a network dependency to
Messor's boot path. Deferred to Sprint 2 if the file approach proves
insufficient — same conclusion as ADR-0012.

### Cycle-shared run timestamp (one prefix for all outlets in a cycle)

Would keep the Backoffice `/api/scrapesessions` view grouping all of a cycle's
outlets under one row. Rejected for this hotfix: requires threading a run
timestamp through `execute_scraping_process → scrape_outlet → NewsScraper`
(4 signatures). The per-outlet `scrape.session.completed` emit (ADR-0009) is the
authoritative telemetry and is unaffected; the `/api/scrapesessions` view simply
becomes per-run-granular, which is cosmetic.
