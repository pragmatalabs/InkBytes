# Messor — Product Vision

> *Status: Draft v1 · Owner: Julián de la Rosa · Last updated: 2026-06-01*

## 1. The product (one paragraph)

**InkBytes** is a paid, ad-free news reader. For every newsworthy *event*, the
reader sees **one elegant page** that consolidates what multiple sources said —
entities, timeline, quoted evidence, freshness, and source diversity — instead
of N versions of the same story spread across the web. Think *Grounded News*,
stripped down to its essentials and built for readers who pay to skip the noise.

**Messor** is the harvester agent that makes that possible: a self-running
24/7/365 service that goes out, collects articles from a curated set of outlets,
filters duplicates, enriches with basic metadata, and pushes them into the
downstream pipeline (Entopics → Synochi → Unitas) that turns raw articles into
one-pagers.

## 2. Why this exists

| Problem (today's reader) | InkBytes answer |
|---|---|
| 12 tabs open about the same event | One page per event |
| No way to tell which source actually added new info | Source diversity score + per-claim attribution |
| Ad walls, popups, autoplay | Paid, ad-free, fast |
| "Breaking" is mostly recycled | Freshness shows what's genuinely new |
| Bias is hidden | Source mix is visible, not buried |

## 3. Product principles

1. **Events, not articles.** The unit of reading is an event/topic, not a URL.
2. **Sources are first-class.** Every claim is traceable to its source.
3. **Calm by default.** No infinite scroll, no notifications, no engagement bait.
4. **Freshness is honest.** "Updated 12 min ago" only when something actually
   changed.
5. **Simple > clever.** If two sources disagree, the page says so. We don't
   pretend.
6. **Reader pays, reader owns.** Subscription funds the product. No ads, no
   tracking-for-sale.

## 4. Where Messor sits

```text
                       ┌──────────────────────────────┐
                       │   READER (winston-r, paid)   │
                       └──────────────▲───────────────┘
                                      │ one-pager per event
                       ┌──────────────┴───────────────┐
                       │   UNITAS  — cluster + QA     │
                       │   SYNOCHI — synthesis        │
                       │   ENTOPICS — NER + topics    │
                       └──────────────▲───────────────┘
                                      │ clean articles + metadata
              ┌───────────────────────┴────────────────────────┐
              │           MESSOR — the harvester agent          │
              │  (this repository module — what this doc covers)│
              └───────────────────────▲────────────────────────┘
                                      │ schedules, fetches, dedups
                            curated news outlets (RSS / HTML)
```

Messor is the **front door** to the whole product. If Messor stops, the product
stops. Treat it as a tier-1 service.

## 5. Messor as an agent (not a script)

Messor is not a cron-triggered one-shot scraper. It behaves as an **autonomous
harvesting agent**:

| Agent property | How Messor implements it |
|---|---|
| **Goal** | Maintain a fresh, deduplicated stream of articles from approved outlets |
| **Sensing** | Polls outlet feeds + HTML pages on a schedule (default 60 min) |
| **Memory** | Tracks scraping sessions, per-outlet stats, cross-session duplicates |
| **Action** | Stores raw + parsed articles, uploads to DO Spaces, emits RabbitMQ events |
| **Self-preservation** | Process lock prevents overlapping runs; heartbeat to RabbitMQ |
| **Observability** | Structured logs + analytics service + session JSON artifact |
| **Bounded autonomy** | Hard config limits (min word count, languages, agents, headers) |

## 6. Non-goals (for Messor)

- Messor does **not** do NLP. Entities, topics, sentiment → Entopics.
- Messor does **not** do clustering. Event detection → Unitas.
- Messor does **not** render the one-pager. UI/UX → winston-r.
- Messor does **not** manage subscriptions / billing → platform service.

Keeping Messor narrow is the whole point of the separation of concerns.

## 7. Success metrics (Messor-level KPIs)

| KPI | Target (steady state) |
|---|---|
| Uptime | ≥ 99.5% (DO single-VM tier); ≥ 99.9% with HA |
| Cycle freshness | Every approved outlet polled within its SLA window |
| Duplicate rate | Reported per session; > 30% is a signal, not a failure |
| Article extraction success | ≥ 90% per outlet (else outlet flagged) |
| Event publish latency | First event-ready signal within 15 min of source publish |
| Cost / 1k articles | Tracked monthly (DO Spaces + compute) |

## 8. Production stance (DigitalOcean)

- **Compute**: DO App Platform *or* a single Droplet running the scraper
  container under a process manager (systemd / Docker restart=always).
- **Storage**: DO Spaces (S3-compatible) for raw artifacts; Postgres (managed)
  for the system of record once Laravel platform takes over from Strapi.
- **Queue**: RabbitMQ on the existing `kloudsix.io` broker (move to DO managed
  message broker or CloudAMQP for production SLA).
- **Secrets**: DO App Platform env vars / Doppler / 1Password — **never** the
  committed `env.yaml`. See [security.md](./security.md).
- **Observability**: ship logs to a managed log service (Better Stack / Axiom /
  Datadog); RabbitMQ exchange `hermes` is the existing log fan-out.

## 9. Inspiration vs. differentiation

| | Ground News | InkBytes |
|---|---|---|
| Coverage | Global, all topics | Curated verticals (start narrow) |
| Bias framing | Left / Center / Right label | Source diversity + claim provenance |
| UX | Dense, comparison-heavy | One page, calm, evidence-rail |
| Pricing | Freemium + Vantage tier | Single paid tier, no free skim |
| Audience | News-curious | Professionals who *need* signal |

The strategic bet: be **smaller, sharper, more elegant**, and let the harvester
+ synthesis quality do the talking.

## 10. Roadmap shape for Messor

- **M0 — Now**: Monorepo migration, services consolidated under `apps/scraper`,
  Docker baseline, scheduled mode.
- **M1 — Production hardening (this milestone)**: secrets rotation, outlet
  health monitoring, structured event schema, retries with backoff,
  observability.
- **M2 — Source quality**: per-outlet SLAs, outlet trust score feeding into
  Unitas weighting.
- **M3 — Scale-out**: horizontal workers per outlet group, Celery or native
  RabbitMQ consumers replacing the in-process ThreadPool for cross-host.
- **M4 — Source intake API**: lets editors propose outlets via the platform UI
  with auto-validation.

---

**See also:** [architecture.md](./architecture.md) ·
[operations.md](./operations.md) · [security.md](./security.md) ·
[ADR-0001 Monorepo](./adr/0001-monorepo-migration.md)
