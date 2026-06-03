# ADR-0003 — DigitalOcean Spaces as the artifact store

* **Status**: Accepted
* **Date**: 2026-06-01
* **Deciders**: Julián de la Rosa

## Context

Messor produces two kinds of output per cycle:

1. **Structured records** (per-article rows) → headed for Postgres via the
   platform API.
2. **Raw + staged artifacts** (parsed JSON sessions, optionally raw HTML,
   logs) → need a cheap, durable, query-able object store.

A managed object store is the right fit for (2): it isolates blob storage
from the relational system of record, gives us versioning + lifecycle, and
keeps the platform Postgres small.

## Decision

Adopt **DigitalOcean Spaces** as the artifact store, bucket `inkbytes` with
the following layout:

```text
s3://inkbytes/
├── messor/
│   ├── staging/        # per-cycle session JSONs awaiting downstream consumption
│   ├── history/        # rotated session JSONs, kept ≥ 90 days
│   └── raw/            # (future) raw HTML snapshots per article
├── messor/logs/        # log archives
└── data/               # ad-hoc shared data drops
```

Access controlled by a **scoped Spaces key** with:

- `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on `inkbytes/messor/*`
- No delete on `messor/history/*` (immutable archive)
- No access to other buckets

Lifecycle:

- `messor/staging/` → 7 days then transition or delete (downstream consumed
  it via RabbitMQ event with object key).
- `messor/history/` → 90 days then `STANDARD_IA`-equivalent or delete.

Operational pattern in code (already implemented in `StorageService`):

```text
write local staging file  ─►  upload to Spaces  ─►  emit RabbitMQ event
                                      │                  │
                                      ▼                  ▼
                                durable archive    triggers Entopics
```

## Consequences

**Positive**

- S3-compatible API; works with boto3 and any existing tooling.
- ~$5/250 GB/month at the relevant volume.
- Versioning + lifecycle without writing code.
- Downstream services consume by object key, never re-fetch from outlets.

**Negative**

- Costs grow with HTML retention; mitigate via lifecycle to delete `raw/`
  after N days.
- Vendor lock-in is moderate (S3 protocol portability mitigates it).

## Alternatives considered

- **MinIO self-hosted** — cheaper at scale but adds an SRE burden we don't
  need at v1.
- **Postgres `bytea`** — wrong tool, blows up DB size and backup time.
- **AWS S3** — fine technically, but DO is our compute provider; staying in
  one cloud reduces egress and ops surface.

## Follow-ups

- Enable bucket versioning in DO console.
- Add lifecycle rules for `staging/` (7d) and `history/` (90d).
- Add an object-key field to the RabbitMQ event payload so downstream can
  fetch directly without round-tripping through the platform.
