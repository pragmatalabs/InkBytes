# InkBytes — System Documentation

> *Parent-level docs for the InkBytes platform.*
> *Source of truth: this repo. Mirror: [Notion hub](https://www.notion.so/373eca56ed94818da548f66ca288593a).*

InkBytes is a paid, ad-free news reader where each newsworthy *event*
becomes a single elegant page synthesized from multiple sources.

This directory holds the **system-wide** docs that span multiple
monorepos. Per-service docs live inside each service's own monorepo
(`Messor/docs/`, `Curator/docs/`, etc.).

## Read first

- **[MVP plan (this week)](./mvp-plan.md)** — the only roadmap that matters right now
- **[System architecture](./architecture.md)** — long-term 4-stage shape (post-MVP)

## Monorepo map

```text
InkBytes/                              ← parent (this repo)
├── docs/                              ← system-wide (you are here)
├── orchestrator/                      ← parent docker-compose + scripts
├── Messor/                            ← Stage 1 — harvester (Python)
│   └── docs/                          ← Messor-specific docs
├── Curator/                           ← Stages 2+3+4 collapsed for v0 (NEW)
├── Reader/                            ← UI/UX — public + admin (NEW)
├── Entopics/  Synochi/  Unitas/       ← parked in v0, revisit post-MVP
└── (legacy folders — slated for archival)
```

## Stage owners (current shape)

| Stage | Repo | Role | Status |
|---|---|---|---|
| 1 — Harvester | `Messor/` | Scrape + dedup + stage | v1 in flight |
| 2 — NLP enrichment | `Curator/` (was `Entopics/`) | NER + topics + summary | v0 stub |
| 3 — Synthesis | `Curator/` (was `Synochi/`) | Cross-source synthesis | v0 stub |
| 4 — Clustering + QA | `Curator/` (was `Unitas/`) | Event detection + persist | v0 stub |
| 5 — Reader UX | `Reader/apps/web/` | Public reader | v0 stub |
| 6 — Admin UX | `Reader/apps/admin/` | Editor + ops | v0 stub |

## Cross-cutting concerns

- **Datastores**: Postgres + pgvector (system of record) · DO Spaces (artifacts) · RabbitMQ (events).
- **LLM**: Anthropic Claude Haiku 4.5 for ENRICH + SYNTHESIZE (locked 2026-06-02).
- **Embeddings**: OpenAI `text-embedding-3-small` for clustering.
- **Vertical for v0**: LATAM bilingual (DR/MX/CO/AR) + global EN business/tech.
- **Deploy**: single DigitalOcean Droplet running docker-compose.
- **Identity**: deferred for v0. Single shared password gate. Magic links post-MVP.
- **Billing**: deferred for v0. Stripe Checkout post-MVP.
- **Secrets**: env vars only (`DO_SPACES_*`, `RABBITMQ_URL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
- **Observability**: stdout → Better Stack (free tier) for v0.

## Branding (interim)

- Product: **InkBytes**
- Tagline: *Your Source for Comprehensive News*
- Values: Accuracy · Transparency · Accountability

(Full brand guide pending. For v0 the synthesis-prompt personality is
the most important brand decision.)
