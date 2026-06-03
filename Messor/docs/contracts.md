# Messor — Output Contract

> *Status: v1 · Source of truth for what Curator can rely on · §2 verified against Curator `ArticleV1` + fixtures · Last updated: 2026-06-02*

Messor is a **pure harvester**. This document is the contract Curator (and
any other downstream consumer) can code against: what Messor **always
fills**, what it **leaves null**, and what it **never touches**.

Decisions backing this contract: [ADR-0005](./adr/0005-messor-curator-responsibility-split.md).

## 1. Article schema (filtered to Messor's responsibility)

The `Article` model in the shared `inkbytes` package is a kitchen-sink
shape used across the platform. Messor only writes a **strict subset**.
Every other field is left at its default (null / `[]` / `{}`).

> **Two shapes, on purpose.** What Messor *stages to disk/S3* (this section,
> the raw `Article` model) is **not** byte-identical to what it *emits on
> RabbitMQ* (§2, the `inkbytes.article.v1` event). The event is a mapped,
> normalized projection of the staged record. §2.1 gives the exact mapping.
> Don't assume the staging file and the event use the same field names —
> they don't.

### 1.1 Fields Messor **always** populates (staged JSON / `Article` model)

These are the field names in the **staging file** (`data/scrapes/*.db.json`)
and the shared `Article` model. The RabbitMQ event renames/derives several
of them — see §2.1.

| Field | Type | Meaning | Source |
|---|---|---|---|
| `id` | `str` | Stable article id (canonical-URL hash) | computed |
| `uid` | `str` | Cycle-scoped unique id (staging only — **not** in the event) | computed |
| `title` | `str` | Article headline | newspaper3k |
| `text` | `str` | Article body, plain text (full length when staged) | newspaper3k |
| `article_url` | `str` | Final URL after redirects → event `url` | newspaper3k |
| `source_url` | `str` | URL Messor started from → event `canonical_url` | request |
| `article_source` | `str` | Outlet name (slug) → event `outlet.name` / `outlet.id` | outlet config |
| `language` | `str` | ISO 639-1 code | newspaper3k `meta_lang` |
| `publish_date` | `str \| null` | ISO 8601 if extractable → event `published_at` | newspaper3k |
| `authors` | `List[str]` | Bylines if extractable | newspaper3k |
| `fetched_on` | `str` | ISO 8601 of scrape time → event `scraped_at` | clock |
| `metadata` | `Dict[str, Any]` | Raw meta tags (og:, twitter:, etc.) | HTML `<meta>` |
| `meta_categories` | `List[str]` | Categories from HTML/meta/URL (raw) | HTML extraction |
| `category` | `str \| null` | Primary category picked from `meta_categories` | derived (no NLP) |
| `keywords` | `List[str]` | Raw `<meta name="keywords">` only | HTML meta |

### 1.2 Fields Messor **leaves untouched** (Curator's responsibility)

| Field | Owner |
|---|---|
| `entities` | Curator — **Skill 1: ENRICH** (NER) |
| `topics` | Curator — **Skill 1: ENRICH** |
| `summary` | Curator — **Skill 1: ENRICH** |
| `sentiment` | Curator — **Skill 1: ENRICH** |
| `factual` (factuality score) | Curator — **Skill 1: ENRICH** |
| `cluster` | Curator — **Skill 2: CLUSTER** |
| `cluster_centroid` | Curator — **Skill 2: CLUSTER** |
| `similars` | Curator — **Skill 2: CLUSTER** |
| `related` | Curator — **Skill 3: SYNTHESIZE** |
| `doc_id` | downstream — system-of-record (Postgres) |
| `last_updated` | downstream — Postgres trigger |

Curator MUST treat these as authoritative when present, and as
"not-yet-enriched" when null/empty.

## 2. Event payload (RabbitMQ)

Exchange: **`messor`** (topic, durable) · routing key: **`event.article.scraped`**
· **one message per article**.

This is the authoritative `inkbytes.article.v1` shape. It is mirrored
field-for-field by Curator's `ArticleV1` / `ArticleScrapedEvent` pydantic
models (`Curator/apps/curator/contracts/article_v1.py`) and by the test
fixtures in `Curator/apps/curator/fixtures/`. If you change either side,
change both **and** this section.

```json
{
  "schema": "inkbytes.article.v1",
  "session_id": "IKPGRB-2026-06-02T12:00:00Z",
  "spaces_key": "messor/staging/<session>/<article_hash>.json",
  "article": {
    "id": "sha256:c0ffee0001",
    "outlet": { "id": "bbcnews", "name": "BBC News" },
    "url": "https://www.bbc.com/news/sample-1",
    "canonical_url": "https://www.bbc.com/news/sample-1",
    "title": "Central bank holds key rate steady amid inflation easing",
    "text": "The country's central bank kept its benchmark rate ...",
    "language": "en",
    "published_at": "2026-06-02T11:30:00Z",
    "scraped_at": "2026-06-02T12:00:00Z",
    "word_count": 92,
    "authors": ["Staff"],
    "meta_categories": ["business", "economy"],
    "category": "business",
    "keywords": ["central bank", "interest rates", "inflation"],
    "metadata": { "og:type": "article", "og:locale": "en_US" }
  }
}
```

Envelope notes:

- `schema` is mandatory; bump to `v2` on any breaking change.
- `outlet` lives **inside `article`** — not at the envelope top level.
- `session_id`, `article`, `spaces_key` are all required by the consumer.
- `spaces_key` lets Curator fetch the full staged JSON directly from
  DO Spaces (or MinIO locally) without round-tripping through any API.
- The embedded `article` is a **mapped projection** of the staged record
  (§2.1), **not** byte-identical to the staging file. An offline Curator
  test should use an event-shaped fixture (see `fixtures/`), not a raw
  `*.db.json` staging file.

### 2.1 Staged `Article` → event `article` mapping

| Event field (`ArticleV1`) | Type | Source (staged `Article`) |
|---|---|---|
| `id` | `str` | `id` |
| `outlet.name` | `str` | `article_source` |
| `outlet.id` | `str` | `article_source`, slugified (lowercased, spaces→`-`) |
| `url` | `str` | `article_url` |
| `canonical_url` | `str \| null` | `source_url`, else `article_url` |
| `title` | `str` | `title` |
| `text` | `str` | `text`, **truncated to 8 000 chars** |
| `language` | `str` | `language` (default `"en"`) |
| `published_at` | `datetime \| null` | `publish_date` |
| `scraped_at` | `datetime` | `fetched_on`, else publish time (UTC now) |
| `word_count` | `int` | `len(text.split())` over the **full** body (pre-truncation) |
| `authors` | `List[str]` | `authors` |
| `meta_categories` | `List[str]` | `meta_categories` |
| `category` | `str \| null` | `category` |
| `keywords` | `List[str]` | `keywords` |
| `metadata` | `Dict[str, Any]` | `metadata` |

Notes:
- `uid` is staging-only; it is **not** carried in the event.
- `text` is capped at 8 000 chars to keep messages small (Curator only
  uses `text[:4000]`); `word_count` reflects the **original** length, so a
  truncated `text` can still report a larger `word_count`. The full body
  remains in the staged JSON / S3 object at `spaces_key`.

Code that emits this: `MessageService.publish_article_event()` in
[`services/message_service.py`](../apps/scraper/services/message_service.py),
called per-article from `StorageService` as staging files are written.

### 2.2 Legacy batch event (`articles_scraped`) — internal only

`MessageService.publish_articles_scraped_event()` emits a separate
end-of-cycle summary (`{"event_type": "articles_scraped", "data": {bucket,
file_path, article_count, outlet, session_id}}`) to the **default exchange**
on queue `articles-scraped`. This is **not** part of the
`inkbytes.article.v1` contract and has **no Curator consumer**. Treat it as
an internal/operational signal, not a downstream contract; it may be removed
without a schema bump.

## 3. What Messor **never** does

- Calls an LLM. Not for enrichment, not for synthesis, not for anything.
- Runs `newspaper3k.Article.nlp()` (heuristic keyword + summary).
- Computes entities, topics, sentiment, factuality, summaries.
- Embeds articles.
- Clusters articles or computes similarity.
- Renders one-pager content.
- Writes to the system-of-record Postgres `events` / `pages` tables.

If you find Messor doing any of those things again, file a bug; it's a
contract regression.

## 4. Filters Messor **does** apply

| Filter | Behaviour |
|---|---|
| Minimum word count | Articles shorter than `scraper.min_word_count` (default 40) are dropped. |
| Language allowlist | Only `articles.supported_languages` (e.g. `en`, `es`) pass through. |
| Freshness window | Articles older than `scraper.timestamp` minutes (default 2880 = 48h) are dropped. |
| Dedup within session | Same `id` in the current cycle → dropped. |
| Dedup across sessions | Same `id` in any session-file under `staging.local.scraping` → dropped. |

These are quality gates, not enrichment. They stay in Messor.

## 5. Versioning

This contract is **`inkbytes.article.v1`**.

Breaking-change rules:

- Removing or renaming a §1.1 field → new major (`v2`), parallel exchange.
- Adding a field to §1.1 → optional, same `v1`; downstream tolerates.
- Tightening a filter (e.g. raising `min_word_count`) → config-level, not
  contract-level.

When Curator wants something Messor doesn't currently produce, Curator
proposes it via a one-page PR amending §1.1 and bumps `v2` if it would
break older consumers.

## 6. Reference

- Decision: [ADR-0005](./adr/0005-messor-curator-responsibility-split.md)
- Code that fills §1.1: [`core/scraper.py`](../apps/scraper/core/scraper.py)
- Code that publishes §2: [`services/message_service.py`](../apps/scraper/services/message_service.py)
- Article model: `packages/inkbytes/inkbytes/models/articles.py` (shared kernel)
