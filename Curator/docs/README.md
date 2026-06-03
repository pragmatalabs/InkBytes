# Curator — Documentation

## Read first

- [Architecture](./architecture.md) — three skills, agent loop, data flow
- [Configuration](./configuration.md) — every `env.yaml` field + env-var overlay
- [Prompts](./prompts.md) — how the Haiku prompts are structured and versioned

## Decision records

- [ADR-0001 — Why Curator collapses Entopics + Synochi + Unitas for v0](./adr/0001-curator-collapses-pipeline.md)
- [ADR-0002 — pgvector + OpenAI embeddings for article clustering](./adr/0002-pgvector-embeddings-clustering.md)

## Contracts (input)

Curator's input contract is **owned by Messor**:
[`../../Messor/docs/contracts.md`](../../Messor/docs/contracts.md)
(`inkbytes.article.v1`).

## Contracts (output)

Curator produces three logical outputs that the Reader consumes:

| Output | Where | Schema |
|---|---|---|
| Enriched article rows | Postgres `articles` table | columns map to `EnrichmentResult` |
| Event clusters | Postgres `events` table | `events.status = 'published'` when a page exists |
| One-pager pages | Postgres `pages` table | `PageV1` (see `contracts/page_v1.py`) |

The Reader reads these via Curator's FastAPI surface (`GET /events`,
`GET /events/{id}`) — no direct DB access from the frontend.
