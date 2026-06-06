# Epic 02 — Reliability & Resilience

> *Stop relying on luck. Add the retry / health / circuit-breaker layer that lets the system fail gracefully under load and outage.*

Risk-links: **R-005 (High)**, **R-002 (High)**, **R-003 (High)**, **R-008 (High)** · Sprints: 2 & 4 · Total: 21 pts

---

## IB-18 · Production Dockerfile + health endpoints for Curator and Messor

**As** the platform owner, **I want** every service container to expose `/healthz` and `/readyz`, **so that** Docker, DO App Platform and load balancers can detect and replace unhealthy instances automatically.

### Acceptance criteria

```gherkin
Given a service container is starting
When the HEALTHCHECK directive runs
Then /healthz returns 200 within 30s of start
And /readyz returns 200 only when DB + RabbitMQ + Spaces are all reachable
And both endpoints return JSON with the failing check name when 503
```

### Notes

- Build on the existing FastAPI `core/api_server.py` in Curator (already has `/healthz` and `/readyz`).
- Add equivalent to Messor's `api/main.py`.
- `HEALTHCHECK CMD curl -fs http://127.0.0.1:PORT/healthz || exit 1` in each Dockerfile.
- Sprint-1 INK-3 covered this for Messor; this story extends it consistently.

**Sprint**: 2 · **Points**: 3 · **Risk**: R-005 · **Priority**: P0 · **Was**: INK-3

---

## IB-19 · Tenacity retry wrapper around outbound HTTP

**As** the pipeline, **I want** every Anthropic, OpenAI, Spaces and outlet call to retry with exponential backoff on transient failures, **so that** one provider hiccup doesn't drop a whole cycle.

### Acceptance criteria

```gherkin
Given Anthropic returns a 5xx or 429
When the retry decorator catches the exception
Then it retries 3 times with exponential backoff + jitter (0.5s → 1s → 2s)
And succeeds if any retry succeeds
And after the final failure, the error is logged with full context and re-raised
```

### Notes

- Use `tenacity` decorators on `LlmService.structured`, `EmbeddingService.embed`, `StorageService.upload`, and `core/scraper.scrape_outlet`.
- Distinguish retryable (5xx, 429, timeouts) from non-retryable (4xx auth errors).
- Add unit tests with mocked failures.

**Sprint**: 2 · **Points**: 3 · **Risk**: R-002, R-003 · **Priority**: P0 · **Was**: INK-6

---

## IB-20 · Per-outlet circuit breaker in Messor

**As** the harvester, **I want** to skip outlets that have failed 5 consecutive cycles, **so that** a blocked source doesn't poison every subsequent run.

### Acceptance criteria

```gherkin
Given outlet "techcrunch" returned 0 articles in 5 consecutive cycles
When the next cycle starts
Then techcrunch is skipped for the next 3 cycles
And a log line records the circuit breaker state
And after the cool-down, one probe cycle runs
And if the probe succeeds, the breaker resets
```

### Notes

- State persisted in `data/outlet_health.json` so it survives restarts.
- Counter resets on any successful cycle.
- Backoffice should show outlet health badge (green/yellow/red) — separate story IB-43.

**Sprint**: 2 · **Points**: 3 · **Risk**: R-002 · **Priority**: P1

---

## IB-21 · LLM cost guard per cycle

**As** the platform owner, **I want** the Curator to halt the pipeline if any single cycle exceeds a configurable USD cap, **so that** a runaway prompt loop can't accidentally bill us $1000.

### Acceptance criteria

```gherkin
Given cost_guard_per_cycle_usd = 5.00
When a single Messor cycle's ENRICH + SYNTHESIZE calls exceed $5.00
Then Curator stops consuming further articles from that cycle
And emits an alert event on curator.logs
And the next cycle resumes normally (the guard is per-cycle, not cumulative)
```

### Notes

- Track cost by aggregating Anthropic `usage.input_tokens` × tariff + `usage.output_tokens` × tariff.
- Pricing constants in `core/config.py` so they update when Anthropic changes prices.
- Pair with a daily-total guard at $50 (separate config) as a backstop.

**Sprint**: 2 · **Points**: 3 · **Risk**: R-003 · **Priority**: P0

---

## IB-22 · Queue workers as docker compose services with restart=always

**As** ops, **I want** Backoffice's `queue:work` and `schedule:work` to run as managed docker services that auto-restart, **so that** the "▶ Iniciar Scraping" button never silently stops working.

### Acceptance criteria

```gherkin
Given the production docker-compose.prod.yaml
When queue:work or schedule:work containers exit
Then docker restarts them with restart=always
And a healthcheck (php artisan queue:size) reports OK within 30s
And container logs go to stdout for log shipping
```

### Notes

- Two new services in compose: `backoffice-queue` and `backoffice-schedule`.
- Both depend_on: backoffice (for shared codebase + DB connection).
- Document in `docs/architecture/components/backoffice.md`.

**Sprint**: 2 · **Points**: 2 · **Risk**: R-008 · **Priority**: P0

---

## IB-23 · DO Managed Postgres restore drill (monthly)

**As** the platform owner, **I want** to validate every month that I can actually restore from DO's managed backups, **so that** R-004 stops being a theoretical risk.

### Acceptance criteria

```gherkin
Given DO managed backups run daily
When the first Monday of the month arrives
Then a restore-drill script provisions a temporary DB from the latest backup
And runs SELECT COUNT(*) on pages, events, articles to confirm row counts ≥ live - 1 day
And tears down the temporary DB
And posts result to #ops Slack
```

### Notes

- Script in `infra/restore-drill.sh`.
- Cron via DO Droplet OR GitHub Actions scheduled workflow.
- Counts as evidence in any compliance audit.

**Sprint**: 3 · **Points**: 3 · **Risk**: R-004 · **Priority**: P1

---

## IB-24 · Two-Droplet active-active for the Reader (HA path)

**As** the platform owner, **I want** the Reader to survive a single Droplet failure, **so that** the SLA can credibly claim 99.9% instead of 99.5%.

### Acceptance criteria

```gherkin
Given two Droplets behind a DO Load Balancer, both running the Reader + Curator API
When one Droplet is stopped (simulated failure)
Then the LB drains it within 60s
And /event/[id] keeps returning 200 from the other instance
And /healthz on the LB-level monitor stays green throughout
```

### Notes

- Workers (Messor, Curator pipeline) stay single-instance — only the Reader + APIs are duplicated.
- Cost impact: +$24/mo (2nd Droplet) + $12/mo (LB).
- Postgres + Spaces + RabbitMQ are already shared between Droplets in this design.
- Defer if v0 + 4 weeks doesn't show real availability issues.

**Sprint**: 4 · **Points**: 5 · **Risk**: R-005 · **Priority**: P2
