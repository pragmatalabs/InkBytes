# ADR-0016 — Object Store Consolidation + Embedding Durability

> *Status: accepted · Sprint: 2 · Owner: Julián · Last updated: 2026-06-08*
>
> 🟡 **Design only — not started.** Decisions are final; implementation deferred to Sprint 2.

---

## Context

### Two object stores in production

The production stack (`infra/docker-compose.prod.yml`) runs **two separate object
stores**:

| Service | Object store | Endpoint |
|---|---|---|
| Messor | **DO Spaces** (managed) | `https://nyc3.digitaloceanspaces.com` |
| Curator API | **MinIO** (self-hosted, Docker) | `http://inkbytes-minio:9000` |
| Curator Worker | **MinIO** (self-hosted, Docker) | `http://inkbytes-minio:9000` |
| Backoffice | **MinIO** (self-hosted, Docker) | `http://inkbytes-minio:9000` |

MinIO is an S3-compatible server containerised inside the prod stack. It works,
but it is not the right tool for production:

- Adds ~100 MB idle memory to the Droplet budget
- Its data lives in `inkbytes-minio-data` (a Docker named volume) — a second
  stateful volume to back up alongside Postgres
- Creates a dev/prod asymmetry: MinIO is supposed to be the **dev stand-in** for
  DO Spaces; having it in prod defeats that purpose
- Article JSON archives stored in MinIO are NOT durably backed up (the named
  volume is on a single Droplet disk — no redundancy, no geo-replication)

### Embeddings have no durable backup

Article embeddings (`articles.embedding vector(1024)`) exist only in Postgres.

| Metric | Value (2026-06-08) |
|---|---|
| Articles with embeddings | 11,279 |
| Table size | 248 MB |
| Raw embedding data | ~46 MB (`11279 × 1024 × 4 bytes`) |
| Growth rate | ~1,500 articles/day (~45k/month) |
| Estimated re-embed time if lost | **~18 hours** (CPU Ollama bge-m3) |

The Postgres volume (`inkbytes-postgres-data`) is a named Docker volume on a
single Droplet. There is no off-box backup. Losing the Droplet disk means
losing both article metadata AND all embeddings.

### pgvector scale headroom

pgvector with HNSW index is comfortable to **~1M vectors** on modern hardware.
At the current growth rate (45k articles/month), the 1M ceiling is reached in
roughly 22 months. Switching to a dedicated vector DB (Qdrant, Pinecone, etc.)
before then would be premature optimisation.

---

## Decisions

### Decision 1 — Consolidate to DO Spaces in production; MinIO in dev only

**Accepted.**

In production (`docker-compose.prod.yml`), remove `inkbytes-minio` and
`inkbytes-minio-init` and point all services at DO Spaces:

```yaml
# All services in prod use DO Spaces instead of MinIO
S3_ENDPOINT:  ${DO_SPACES_ENDPOINT:-https://nyc3.digitaloceanspaces.com}
S3_KEY:       ${DO_SPACES_KEY}
S3_SECRET:    ${DO_SPACES_SECRET}
S3_BUCKET:    ${DO_SPACES_BUCKET:-inkbytes}
```

In dev (`orchestrator/docker-compose.dev.yaml`), MinIO stays as the local
stand-in:
```yaml
S3_ENDPOINT: http://inkbytes-minio:9000
S3_KEY:      ${MINIO_KEY:-minio}
S3_SECRET:   ${MINIO_SECRET:-minio123}
```

**Why DO Spaces, not a new managed Postgres service or separate vector DB:**
DO Spaces costs $5/month for 250 GB and is already provisioned. It is durable,
geo-replicated within the nyc3 region, and API-compatible with AWS S3 so no
code changes are needed beyond swapping credentials.

**Migration note (one-time):** On the first deploy after this change, any
article JSON files stored in the old MinIO bucket must be copied to DO Spaces
before removing the MinIO container. Use `mc mirror` (MinIO Client) for this.
See implementation checklist below.

### Decision 2 — Daily Postgres dump to DO Spaces

**Accepted.**

Add a `--backup` command (or a cron in the Curator worker container) that
runs a `pg_dump` of the `inkbytes` database, gzips it, and uploads to
`s3://inkbytes/backups/postgres/YYYY-MM-DD.sql.gz`.

This covers ALL data: articles, embeddings, events, pages, llm_calls. It is
simpler and more complete than a standalone embedding export.

Retention policy: keep 7 daily dumps, 4 weekly dumps (28-day window).

```
inkbytes/
  backups/
    postgres/
      2026-06-08-daily.sql.gz     (~50–200 MB compressed)
      2026-06-01-weekly.sql.gz
      ...
    messor/
      scraping/                   ← Messor staging files (already in place)
```

**Implementation**: A lightweight Python script (`scripts/pg_backup.py`) using
`subprocess.run(["pg_dump", ...])` piped through `gzip` and uploaded via
`boto3` / the existing `S3Client` in `services/storage_service.py`.

Trigger options (TBD at implementation):
- Cron inside `inkbytes-curator-worker` container (simplest, no new container)
- Separate `inkbytes-backup` init container (cleaner, no coupling to Curator)
- DigitalOcean Managed Database snapshots (if/when we move Postgres to DO Managed)

### Decision 3 — Stay on pgvector; revisit at 100k articles

**Accepted.**

pgvector with HNSW index handles the current scale comfortably. A dedicated
vector DB (Qdrant, Weaviate, Pinecone) would add operational complexity with
no query-latency benefit at <100k articles.

Trigger for re-evaluation: when `SELECT COUNT(*) FROM articles WHERE embedding IS NOT NULL`
exceeds **100,000** OR when the ANN clustering query in `ClusterSkill` exceeds
**500ms p95**, whichever comes first.

At the current growth rate (45k/month) the 100k milestone arrives in ~Sprint 3
(~2 months). The Postgres backup from Decision 2 makes the embedding corpus
portable: if we migrate to Qdrant, we reconstruct from the SQL dump rather than
re-embedding from scratch.

---

## Consequences

| | Before | After |
|---|---|---|
| Object stores in prod | 2 (MinIO + DO Spaces) | 1 (DO Spaces only) |
| MinIO memory overhead | ~100 MB | 0 (dev only) |
| Article JSON archival | MinIO volume (Droplet disk) | DO Spaces (geo-replicated) |
| Embedding recovery time | ~18h (full re-embed) | ~10 min (restore from daily dump) |
| Postgres backup | None | Daily `.sql.gz` in DO Spaces, 28-day retention |
| MinIO in dev | Unchanged | Unchanged |

---

## Alternatives considered

| Option | Rejected because |
|---|---|
| Export embeddings separately as `.npy` / Parquet files to Spaces | Full `pg_dump` is simpler, covers all tables, and handles schema migrations cleanly. A standalone embedding export duplicates data without adding recovery speed |
| DO Managed Postgres ($15/mo) | Valid Sprint 3 option — automated snapshots, point-in-time recovery, no volume ops. Deferred: adds cost and migration risk while Droplet Postgres is working |
| Qdrant (with S3 snapshot support) | Correct long-term direction but premature at 11k vectors. Revisit at 100k articles |
| Keep MinIO in prod | MinIO in prod was never the plan (it was the dev stand-in). Keeping it means maintaining two separate credential sets, two volumes to back up, and a confusing dev/prod split |
| AWS S3 instead of DO Spaces | DO Spaces is already provisioned, API-compatible, and cheaper for our Droplet-collocated traffic. No reason to add a cross-provider dependency |

---

## Implementation checklist (Sprint 2)

**Phase 1 — Postgres backup (no prod change, safe to do first):**
- [ ] `Curator/scripts/pg_backup.py`: `pg_dump` → `gzip` → `boto3` upload to Spaces
- [ ] `infra/docker-compose.prod.yml`: cron or `--backup` schedule in curator-worker
- [ ] Validate: restore dump to local Postgres; confirm article + embedding counts match
- [ ] `infra/.env.production.example`: add `DO_SPACES_KEY`, `DO_SPACES_SECRET` if missing

**Phase 2 — MinIO → DO Spaces migration (prod change, test in dev first):**
- [ ] Dev test: swap `S3_ENDPOINT` in dev compose to point at a test DO Spaces bucket;
      confirm Curator API/Worker and Backoffice can read/write correctly
- [ ] One-time migration: `mc mirror inkbytes-minio/inkbytes s3://inkbytes/`
      (copy existing MinIO content to DO Spaces before switching)
- [ ] `infra/docker-compose.prod.yml`: replace MinIO env vars with DO Spaces vars
      for Curator API, Curator Worker, Backoffice
- [ ] `infra/docker-compose.prod.yml`: remove `inkbytes-minio`, `inkbytes-minio-init`,
      `inkbytes-minio-data` volume
- [ ] `infra/docker-compose.do.yml`: no MinIO-related entries (verify)
- [ ] `infra/volumes:` section: remove `inkbytes-minio-data` declaration
- [ ] Deploy and verify no 500s on Curator API, Backoffice article detail pages
- [ ] After 24h green: delete the old `inkbytes-minio-data` Docker volume on DO

**Phase 3 — pgvector scale checkpoint:**
- [ ] Add monitoring query to Backoffice dashboard:
      `SELECT COUNT(*) FROM articles WHERE embedding IS NOT NULL`
- [ ] Set calendar reminder at 100k articles to evaluate Qdrant migration
