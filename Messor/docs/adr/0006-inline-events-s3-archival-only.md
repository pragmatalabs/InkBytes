# ADR-0006 — Inline per-article events; S3 becomes archival-only

> *Status: Accepted · Owner: Julián de la Rosa · Date: 2026-06-02*

## Context

ADR-0003 established the original pipeline trigger pattern:

```
scrape → save local → upload to S3 → emit RabbitMQ event (spaces_key pointer)
                                               │
                                               ▼
                                    Curator fetches article from S3
```

S3 served two purposes simultaneously: **durable artifact store** and
**data transport** to Curator. This design had three problems:

1. **S3 is on the critical path.** If the upload fails or is slow, Curator
   is blocked. Local dev without DO Spaces credentials meant the pipeline
   never triggered.

2. **Session-level granularity.** One RabbitMQ event was emitted per
   scraping session (a file of N articles). Curator processes articles
   individually — it needed to fetch the file, parse it, then iterate.
   That's three hops (MQ → S3 → parse) instead of one.

3. **Dev / prod asymmetry.** In local mode (`save_mode: local_only`) the
   S3 upload was skipped, so events were never emitted. RabbitMQ wiring
   could not be tested without real DO Spaces credentials.

## Decision

**Publish one `event.article.scraped` message per article, with the full
`ArticleScrapedEvent` payload inline, immediately after the article is
written to the local staging file.**

S3 upload continues as a **fire-and-forget archival step** that runs
after the event is already published. It does not gate, delay, or
re-trigger Curator.

```
scrape → save staging file → emit RabbitMQ (full article inline) ← pipeline trigger
                │
                ▼  (separate, async)
          upload S3  ← archival only; spaces_key stored for replay use
```

### New `spaces_key` semantics

The `spaces_key` field remains in `ArticleScrapedEvent` and in the
`articles` DB column for forward-compatibility. Its value:

| Scenario | `spaces_key` value |
|---|---|
| Article published inline (dev or prod) | `""` / `NULL` |
| S3 archive completed (future) | `"messor/staging/20260602.bbc.db.json"` |

The DB column is now `NULLABLE` (changed from `NOT NULL`). Curator's
`upsert_article_raw` coerces `""` → `NULL`.

### What changed in code

| File | Change |
|---|---|
| `services/message_service.py` | Added `publish_article_event()`. Maps Messor `Article` → `ArticleScrapedEvent`. Publishes to `messor` topic exchange, routing key `event.article.scraped`. Body text truncated to 8 000 chars (~50 KB cap per message). |
| `services/storage_service.py` | Added `_publish_articles_from_staging_file()`. Called once in `save_session_to_file()`. Removed duplicate calls from `upload_file_to_s3()` and `execute_files_move()`. |
| `core/application.py` | RabbitMQ connection no longer gated on `log_to_broker`. Always connects; failures are non-fatal. |
| `env.local.yaml` | Credentials updated to `messor:messor` (matches docker-compose). |

### Why per-article events (not per-session)

Curator's pipeline processes one article at a time through three skills
(ENRICH → CLUSTER → SYNTHESIZE). A session-level event would require
Curator to re-parse the staging file, adding a filesystem or S3 round-trip
with no benefit. Per-article events map 1:1 to Curator's processing unit
and allow back-pressure via RabbitMQ QoS (`prefetch_count=4`).

### Text truncation (8 000 chars)

Curator's embedding call uses `text[:4000]` and the LLM prompts use the
article body up to ~6 000 chars. Storing the full text (up to 80 KB for
long-form articles) in RabbitMQ messages wastes broker memory for no
processing gain. 8 000 chars covers ~1 200 words — sufficient for all
news articles; truncated only for very long features. The full text
already lives in the S3 archive for future replay.

## Consequences

**Positive**
- Dev pipeline works without DO Spaces credentials (MinIO still runs in
  docker-compose for local S3 testing, but is not blocking).
- No S3 latency on the critical path; Curator receives articles immediately.
- Single publish point eliminates the previous 2–3× duplicate-event bug.
- Exchange/routing now matches Curator's consumer (`messor` topic exchange,
  `event.article.scraped` routing key).

**Negative**
- `spaces_key` is `NULL` until the archival step populates it. Any future
  Curator feature that reads from S3 must handle `NULL` gracefully.
- Text truncation at 8 000 chars means the S3 archive is the only place
  full long-form article text is retained. The replay flow must restore
  full text from S3 before re-enriching very long articles.

## Alternatives considered

**Keep S3 as the transport, add a parallel inline path** — considered and
rejected. Two code paths for the same data would require maintaining two
payload formats and adds confusion about which path is authoritative.

**Drop S3 entirely** — rejected. S3 provides replay-without-re-scraping,
a legal audit trail of what was seen, and a safety net for very large
payloads. At $5/month it pays for itself on the first production incident
where re-scraping an outlet is not possible.

**Use a database queue instead of RabbitMQ** — rejected. Postgres polling
is simpler but loses the back-pressure, consumer-group, and dead-letter
capabilities that justify RabbitMQ.

## Follow-ups

- Add a background job that patches `articles.spaces_key` after S3 upload
  completes (v1 — not blocking v0).
- Consider capping RabbitMQ message TTL to 48 h (current: 24 h) to give
  Curator a recovery window after outages.
