# ADR-0012 — Persistent Staging Volume + Bounded URL-Dedup Window

> *Status: accepted · Owner: Julián · Last updated: 2026-06-08*
>
> **Follow-up:** [ADR-0014](./0014-per-run-staging-files-stop-republish-amplification.md)
> — the per-day staging file this ADR assumed (`generate_today_timestamp()`)
> was itself re-published in full every cycle, amplifying any dedup gap. The
> ADR-0016 migration deleted this volume (exactly the §"Risk: named volume
> deleted manually" scenario) and the amplification turned a ~1 540-msg re-flood
> into the 105 143-msg backlog of 2026-06-09. ADR-0014 switches to per-RUN files.

## Context

Messor's URL dedup relies on `load_known_article_urls()`, which scans all prior
`*.db.json` staging files for a given outlet to build a set of already-seen
article URLs (ADR-0011 Layer 3).  When a URL is found in that set the article
is skipped without any HTTP request or RabbitMQ publish.

Two problems were discovered on 2026-06-08:

---

### Problem 1 — Staging files are not persisted across container restarts

`docker-compose.prod.yml` had **no volume mount** for the Messor container's
`data/scrapes/` directory.  The Dockerfile comment explicitly says:

> *data/ and logs/ are expected to be bind-mounted from the host.*

Without a volume mount the directory lives in the container's ephemeral layer.
Any container restart — including a routine deploy via `deploy.sh` — destroys
all staging files.

**Consequence:** after every restart `load_known_article_urls` returns an empty
set; every article on every outlet's homepage passes Layer 3 dedup and is
published to RabbitMQ as "new."  With 22 outlets × ~70 articles each, a single
restart floods the queue with ~1 540 duplicate messages.  At 4×/day (plus any
crash-restart events), this was the primary driver of the 82k-message queue
accumulation observed on 2026-06-07/08.

Curator's ADR-0015 fast-path (content-hash skip) makes those duplicates nearly
free to process, but the queue still grows unboundedly and wastes I/O.

### Problem 2 — No retention cap on staging files

`load_known_article_urls` scanned ALL `.db.json` files in `scrapes_dir` for the
outlet.  Files accumulate at 1 per outlet per day (`generate_today_timestamp()`
produces a per-day prefix — note: ADR-0014 later changed this to 1 file per
outlet per *run*).  After one year of 22 outlets: **8 030 files**.

- Startup per outlet: O(N_files) JSON reads → increasingly slow.
- Memory: entire URL set for all scraped history loaded into RAM at cycle start.
- No code to clean old files existed.

---

## Decision

### Fix 1 — Add named Docker volume for `data/scrapes/`

In `infra/docker-compose.prod.yml`:

```yaml
volumes:
  inkbytes-messor-scrapes:   # new — persists across container restarts

services:
  inkbytes-messor:
    volumes:
      - inkbytes-messor-scrapes:/app/apps/scraper/data/scrapes
```

This makes the staging directory a proper named Docker volume that survives
`docker compose up --force-recreate` and container crashes.

### Fix 2 — Scope URL dedup to a 7-day window

`load_known_article_urls` now only scans staging files whose timestamp prefix
(`<unix-day-ts>`) is within the last 7 days (`_URL_DEDUP_WINDOW_DAYS = 7`).

**Rationale for 7 days:**
- Outlet homepages rarely feature the same article beyond 7 days.
- Articles that do re-appear after >7 days are cheaply handled by Curator's
  ADR-0015 content-hash fast-path (no LLM calls).
- Limits startup scan to at most 7 × 22 = 154 file reads across all outlets.
- Files with unparseable timestamp prefixes are included unconditionally for
  backward compatibility.

### Fix 3 — Prune staging files older than 30 days

`prune_old_staging_files(scrapes_dir, keep_days=30)` is called once per
`execute_scraping_process` invocation (before the outlet loop).  It deletes
any `*.db.json` and `*.session.json` file whose timestamp prefix predates the
30-day cutoff.

Files without a parseable numeric timestamp prefix are left untouched.

30 days ≫ the 7-day dedup window, so files remain available for manual
inspection and the S3 archival path that may still need them; they are simply
not scanned by the dedup loop.

---

## Consequences

| Metric | Before | After |
|---|---|---|
| Queue flood on deploy | ~1 540 msgs/restart | 0 (staging files survive) |
| URL dedup scan at startup | All files ever | Last 7 days (≤ 7 files/outlet) |
| Disk usage after 1 year | 8 030 files (unbounded) | ~22 × 30 = 660 files (capped) |
| Articles re-published if container loses volume | All articles | None (volume is named, persistent) |

### Risk: first deploy with new volume

On the first deploy after this change, Docker creates the named volume empty.
The first scrape cycle after that restart publishes all current articles
(same as the old behaviour).  Curator's fast-path ACKs them without LLM calls.
This is a one-time event, not ongoing.

### Risk: named volume deleted manually

If an operator runs `docker volume rm inkbytes-messor-scrapes`, the staging
history is lost and the next cycle re-floods the queue.  Curator's fast-path
handles this gracefully.  Document in runbook: do not remove this volume during
normal operations.

---

## Alternatives considered

### Bind-mount a host path instead of a named volume

Would work, but named volumes are managed by Docker Engine and survive host
path changes.  Bind-mount requires the host directory to exist before the
container starts.  Named volume is simpler for DO/docker-compose production use.

### Store seen-URLs in Postgres instead of files

Fully durable, queryable, no disk management needed.  But it crosses the
ADR-0005 responsibility boundary (Messor should not query Curator's Postgres)
and adds a network dependency to Messor's boot path.  Appropriate for Sprint 2
if the file approach proves insufficient at scale.

### Keep the full-history scan (no 7-day window)

Simpler, but makes startup increasingly slow as files accumulate.  The bounded
window plus Curator's fast-path makes the trade-off cost-free.
