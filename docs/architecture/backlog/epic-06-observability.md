# Epic 06 — Observability

> *Today we have stdout. Tomorrow we have logs + metrics + traces + cost tracking. Without these, post-v0 debugging is guesswork.*

Risk-links: enabler · Sprints: 3 · Total: 13 pts

---

## IB-40 · Better Stack log aggregation (free tier)

**As** ops, **I want** all service logs in one searchable UI, **so that** debugging an incident doesn't require ssh'ing into Droplets.

### Acceptance criteria

```gherkin
Given Better Stack (or Axiom) has a sink configured
When any service writes structured JSON to stdout
Then the log appears in the UI within 30s
And is searchable by service, level, correlation_id
And alerts fire on error rate > 1% over 5 min
```

### Notes

- Free tier: 1 GB/month. Sufficient for v0+.
- Use `vector` or `fluent-bit` sidecar to ship.
- Structured logging via `structlog` (already in Curator's requirements).

**Sprint**: 3 · **Points**: 2 · **Priority**: P0

---

## IB-41 · OpenTelemetry tracing across services

**As** the team, **I want** distributed traces showing the full path of an article from harvest to publication, **so that** I can pinpoint which skill or service is causing latency.

### Acceptance criteria

```gherkin
Given OTel SDK is integrated in Messor, Curator, Backoffice
When a single article's event_id is traced
Then I can see spans for: scrape → publish → consume → enrich → embed → cluster → synthesize
And total wall-clock time is measurable
And spans include LLM token counts as attributes
```

### Notes

- Backend: Tempo (self-hosted) or Datadog ($0 free tier, then $15/host).
- Auto-instrument FastAPI + asyncpg + aio-pika via opentelemetry-instrumentation-*.
- Manual spans around each skill (`with tracer.start_as_current_span("enrich")`).

**Sprint**: 3 · **Points**: 3 · **Priority**: P1

---

## IB-42 · Prometheus metrics on every FastAPI service

**As** the team, **I want** RED metrics (rate, errors, duration) on every endpoint and a custom counter for LLM cost, **so that** dashboards are populated and alert thresholds are objective.

### Acceptance criteria

```gherkin
Given prometheus-fastapi-instrumentator is wired in each service
When I hit /metrics
Then I see http_requests_total, http_request_duration_seconds, http_requests_in_progress
And custom counters: llm_calls_total{model,skill}, llm_cost_usd_total, embedding_calls_total
And Grafana (or DO managed Grafana) renders a per-service dashboard
```

### Notes

- Cheap and standard for FastAPI.
- LLM cost counter ties to IB-21 (cost guard).
- Dashboards as code in `infra/observability/grafana-dashboards/`.

**Sprint**: 3 · **Points**: 3 · **Priority**: P1

---

## IB-43 · Cost & quality dashboard in Backoffice

**As** the operator, **I want** a single Backoffice page showing today's LLM spend, last-cycle errors, top-failing outlets, and freshness lag, **so that** I see system health without leaving the admin.

### Acceptance criteria

```gherkin
Given Curator /status and Prometheus metrics expose the data
When I open Backoffice → Health
Then I see: today's USD on Anthropic, today's article count, errors per outlet, p95 freshness
And the page auto-refreshes every 30s
And clicking an outlet jumps to its detail with last 24h cycle history
```

### Notes

- Pulls from Curator `/status` + Prometheus query endpoint.
- Outlet health badge (green/yellow/red) ties to circuit breaker (IB-20).
- Surface the freshness lag from `pages.freshness_at`.

**Sprint**: 4 · **Points**: 3 · **Priority**: P1

---

## IB-44 · Sentry error tracking (free tier)

**As** the team, **I want** unhandled exceptions to land in Sentry with stack + context, **so that** errors get triaged instead of buried in stdout.

### Acceptance criteria

```gherkin
Given Sentry SDK is initialized in each service with DSN from env
When a Python exception bubbles up
Then it appears in Sentry within 5s with stack trace + request context
And duplicate errors are grouped
And a Slack alert fires for the first occurrence of a new error fingerprint
```

### Notes

- Free tier: 5k errors/month. Sufficient for early ops.
- `sentry-sdk[fastapi]` + `sentry-sdk[asyncpg]` + manual ones for the workers.
- Filter out expected exceptions (4xx) to save quota.

**Sprint**: 3 · **Points**: 2 · **Priority**: P1
