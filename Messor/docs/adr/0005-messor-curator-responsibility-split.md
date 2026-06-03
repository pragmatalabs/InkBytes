# ADR-0005 — Split Messor (harvester) vs. Curator (LLM pipeline) responsibilities

* **Status**: Accepted
* **Date**: 2026-06-02
* **Deciders**: Julián de la Rosa
* **Relates to**: [v1-scope](../v1-scope.md), [docs/mvp-plan.md](../../../docs/mvp-plan.md), ADR-0002 (RabbitMQ events)

## Context

The original Messor codebase did some "enrichment-shaped" work alongside
the pure harvesting role:

- Called `newspaper3k.Article.nlp()` to extract heuristic keywords +
  summary.
- A `unify_keywords()` helper merged `.nlp()`-derived keywords with HTML
  meta keywords into a single canonical list.
- `get_comprehensive_categories()` extended categories with the same NLP
  keywords.
- The `Article` model exposes fields like `entities`, `topics`,
  `summary`, `sentiment`, `factual`, `cluster`, `cluster_centroid`,
  `similars`, `related` — all populated (or partially populated) by
  Messor at one point or another.
- `env.yaml` carried an `openai:` block, a `topics_extracted` queue, and
  a `clusters_path` storage prefix — none of which Messor consumes or
  produces.
- The interactive CLI exposed a "show topics-extracted queue depth"
  command — a queue Messor doesn't own.

With the v0 MVP plan (Curator collapses Entopics + Synochi + Unitas into
one LLM-powered service), this bleed makes the boundary unclear and
risks Curator re-doing work Messor already half-did with worse quality.

## Decision

Make Messor a **strict harvester** and move every form of enrichment,
NLP, clustering, synthesis, and downstream-queue ownership to **Curator**.

### What Messor owns

1. Fetch the article (HTTP + parse).
2. Extract objectively-present fields: title, text, URL, language,
   publish date, authors, raw meta tags, raw HTML/URL/meta categories.
3. Apply quality filters: min word count, language allowlist,
   freshness window, dedup by id/hash within and across sessions.
4. Stage the article JSON locally + upload to DO Spaces.
5. Publish one event per article on exchange `messor`, routing key
   `event.article.scraped`.

### What Messor does NOT do (anymore)

1. Call `article.nlp()` or any LLM.
2. Compute or unify NLP-derived keywords. Keywords forwarded by Messor
   are exclusively from the HTML `<meta name="keywords">` tag.
3. Populate any of: `entities`, `topics`, `summary`, `sentiment`,
   `factual`, `cluster`, `cluster_centroid`, `similars`, `related`.
4. Consume or publish on the `topics-extracted` queue. That queue is
   Curator's output (Skill 1 → Skill 2).
5. Carry an `openai:` config block. Embeddings (OpenAI
   `text-embedding-3-small`) live in Curator's config.

### What Curator owns (downstream of this ADR)

1. **Skill 1 — ENRICH**: per-article LLM call (Anthropic Haiku 4.5) that
   produces structured `{entities, topics, summary, sentiment,
   factuality, keywords_canonical}`. Persists to `articles` table.
2. **Skill 2 — CLUSTER**: embedding (OpenAI
   `text-embedding-3-small`) + cosine similarity + entity overlap →
   `cluster_id`. Persists to `events` table.
3. **Skill 3 — SYNTHESIZE**: when a cluster has ≥ 2 sources, second
   Haiku call producing the one-pager. Persists to `pages` table.
4. Publishes derived events on its own exchange: `curator.topics`
   (formerly `topics-extracted`), `curator.events`,
   `curator.pages.published`.

## Concrete code changes (INK-11)

| Where | Change |
|---|---|
| `core/scraper.py` `pre_process_article()` | Remove `article.nlp()` call. The function now only returns parsed articles with non-empty text and detected language. |
| `core/scraper.py` `unify_keywords()` | Renamed to `extract_meta_keywords()`. Body simplified to forward `metadata['keywords']` only. |
| `core/scraper.py` `get_comprehensive_categories()` | Removed the `extend(article.keywords)` branch — that was NLP keywords leaking into categories. HTML/meta/URL categories remain. |
| `core/scraper.py` `create_article_record()` | Calls the renamed `extract_meta_keywords()` instead of the old unifier. |
| `core/command_processor.py` queue-status command | Removed the `topics_extracted` queue lookup. Only `articles_scraped` displayed. |
| `core/command_processor.py` test-publish command | Removed user-prompted queue choice; Messor always publishes to its own queue. |
| `apps/scraper/env.yaml` · `env.example.yaml` · `env.local.yaml` | Removed: `storage.staging.local.clusters_path`, `rabbitmq.queues.topics_extracted`, `openai:` block. |
| `docs/contracts.md` (NEW) | Explicit output schema, the source of truth for what Curator can rely on. |

## Consequences

**Positive**

- Clear contract between stage 1 (Messor) and stage 2 (Curator).
  Curator can stub Messor's output for unit tests with no NLP libs.
- Smaller Messor image — no NLTK punkt+punkt_tab actually needed for
  enrichment (still needed by newspaper3k's parser internals, so we
  keep it for now; can be slimmed in v1).
- Single source of truth for keywords/topics/entities: Curator's LLM
  output, not a blend of LLM + heuristics + HTML scraping.
- Easier to swap the LLM provider — no second NLP layer hidden in
  Messor.

**Negative**

- Existing staging files written before this change have populated
  `keywords` from the old unifier. Curator must treat any Messor field
  as "may be present from legacy runs, prefer my own enrichment."
- The `Article` model still carries all the Curator-owned fields. We
  *could* split into `RawArticle` + `EnrichedArticle` for stricter
  typing — deferred to v1 (low ROI now).

**Neutral**

- newspaper3k is still on Messor's dependency tree; we just don't call
  its `.nlp()` method. The lib remains the parser of choice for
  title/text/authors/publish-date extraction.

## Alternatives considered

1. **Keep `.nlp()` and pass its output as "hints" to Curator** —
   rejected. It blurs the contract and forces Curator to either
   trust two NLP layers or systematically discard one of them. Pick
   one.
2. **Move newspaper3k entirely to Curator and have Messor publish raw
   HTML** — rejected for v0. Parsing in Messor is cheap, isolates
   outlet quirks, and means Curator handles only canonical JSON.
   Revisit when we have multi-language pipelines requiring
   site-specific parsers.
3. **Split `Article` into `RawArticle` and `EnrichedArticle`** —
   correct long-term, deferred to v1. Two reasons: (1) requires
   coordinated changes in the shared `inkbytes` package consumed by
   legacy code under `Entopics/Synochi/Unitas`, (2) the kitchen-sink
   shape is harmless as long as the contract (§1 in
   `docs/contracts.md`) is respected.

## Follow-ups

- `Curator/apps/curator/env.yaml` (D2 work) inherits the removed
  `clusters_path`, `topics_extracted`, and `openai:` config from
  Messor's old env.
- ADR-0006 (when Curator scaffold lands): exchange/queue naming for
  Curator-published events.
- v1: split `Article` into `RawArticle` + `EnrichedArticle` in the
  `inkbytes` package, with a migration script.
