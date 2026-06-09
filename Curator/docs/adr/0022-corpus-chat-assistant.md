# ADR-0022 — Corpus chat assistant: grounded digests & Q&A over published events

> *Status: accepted (Phase 1+2 implemented) · Owner: Julian · Date: 2026-06-09*

## Context

InkBytes already turns clusters of articles into cited summaries
(`SynthesizeSkill` → `pages.synthesis_md` + `evidence_rail`). Readers asked for a
lightweight, conversational layer on top of that corpus:

- **Daily digests** — "today's resume", "top 10 to watch in tech", "what
  happened in LATAM today".
- **Free-form Q&A** — "what's the latest on the Iran–Israel ceasefire?"

The hard requirement: the assistant must answer **only from InkBytes article
information** — no outside model knowledge, every claim traceable to a source the
reader can open. It must surface as a simple overlay screen in the Reader with
tappable source links.

## Decision

Add a thin, retrieval-augmented assistant that **reuses the synthesis engine
unchanged**. The synthesizer is already a RAG agent ("articles in → cited summary
out"); the assistant is the same `LlmService.structured()` call with (a) a
different retrieval step and (b) a different prompt. No new model, DB, or
infrastructure.

```
question / "today" / "top 10 tech"
        ↓  retrieve (SQL filter or pgvector ANN)          ← the only new part
   top-K published-event sources (headline, synthesis_excerpt, url, outlet, theme)
        ↓  LlmService.structured(prompt=assistant.md, response_model=AnswerV1)
   { answer_md, sources: [{ n, title, url, outlet }] }     ← existing engine
        ↓
   Reader overlay renders markdown + source chips
```

### Corpus scope: published events only

Retrieval draws **exclusively from published events** (`events.status =
'published'` AND `pages.published_at IS NOT NULL`) and their member articles —
the same curated set the feed already shows. Rationale:

- Quality: published events passed the ≥2-source gate, the promo filter
  (ADR-0020) and the non-news filler filter (filler ADR), so digests never
  surface single-source rumor, shopping, or horoscope/lottery junk.
- Trust: every source the assistant cites is a page the reader can already open
  in InkBytes — citations resolve to event pages, not raw external URLs.
- Smaller, cleaner index → cheaper retrieval, fewer hallucination openings.

(Out of scope for v1: single-source / never-published articles. Revisit only if
"top 10" coverage proves too thin — see Future work.)

### Two retrieval modes

**1. Digest (deterministic, no vector search) — ship first.**
A structured query over recently published events, optionally filtered by the
existing `theme` / derived category:

```sql
SELECT p.id, p.headline, p.synthesis_md, e.topic, e.language,
       (SELECT theme FROM articles a WHERE a.event_id = e.id
         AND a.theme IS NOT NULL LIMIT 1) AS theme
FROM pages p
JOIN events e ON e.id = p.event_id
WHERE p.published_at IS NOT NULL
  AND e.status = 'published'
  AND p.freshness_at > NOW() - INTERVAL '24 hours'   -- scraped_at-based (ADR freshness)
ORDER BY p.freshness_at DESC
LIMIT 40;
```

The LLM ranks/summarizes into "today's resume" or "top 10 in tech", each bullet
citing its source event. No embeddings needed — cheapest, highest-value path.

**2. Free-form Q&A (RAG) — phase 2.**
Embed the question with the existing `EmbeddingService.embed()` (Ollama bge-m3,
1024-dim) and ANN-search the published events' article embeddings using the exact
pgvector `<=>` pattern already in `skills/cluster.py`:

```sql
SELECT p.id, p.headline, a.title, a.summary_50w, a.url, a.outlet_name
FROM articles a
JOIN events e ON e.id = a.event_id
JOIN pages  p ON p.event_id = e.id
WHERE p.published_at IS NOT NULL AND e.status = 'published'
ORDER BY a.embedding <=> $1::vector ASC
LIMIT 12;
```

Top-K → same `assistant.md` prompt → cited answer.

### The grounding rule (what makes it "articles only")

Lives in `prompts/assistant.md` (diffable, same convention as `synthesize.md`):

> *Answer ONLY from the numbered SOURCES below. Every claim must cite its
> source number. If the sources do not cover the question, say so plainly —
> never use outside or prior knowledge. Do not invent sources.*

Because the model only ever sees retrieved InkBytes text and is forbidden from
outside knowledge, hallucination is bounded by construction. An empty/thin
retrieval yields an honest "I don't have InkBytes coverage on that yet."

### Surfaces

**Curator (`core/api_server.py`):** one read endpoint
`POST /ask { question?, mode: "resume"|"top10"|"chat", category? }` returning
`AnswerV1 { answer_md, sources[] }`. Same `force-dynamic` rules as the rest of
the read surface (no ISR baking — ADR-R-0005).

**New skill (`skills/assistant.py`):** `AssistantSkill.answer(...)` —
retrieve (SQL or vector) → `LlmService.structured(...)`. `AnswerV1` is a pydantic
v2 model mirroring `PageV1.evidence_rail`'s citation shape.

**Reader (`Reader/apps/web`):** a full-screen overlay (same pattern as
`media-rail-drawer.tsx`, `animate-slide-up`, `md:` aware) opened by a floating
"Ask / Today" button. Quick-action chips — `Today's resume`, `Top 10 Tech`,
`Top 10 World` — fire digest queries with one tap; a text box handles free-form
(phase 2). Renders `answer_md` as markdown and `sources[]` as tappable chips
linking to each InkBytes event page.

## Phased rollout (simple first)

1. **Phase 1** — `assistant.md` + `AssistantSkill` (digest only) + `/ask` +
   Reader overlay with the 3 canned chips. Deterministic SQL, no vector search.
2. **Phase 2** — free-form RAG chat (pgvector retrieval over published events).
3. **Phase 3 (optional)** — inject concluded **story arcs** (ADR-0013) as
   historical context for "how did this story unfold" questions.

## Consequences

- New read-only surface; no writes, no new tables, no new model. Cost is one LLM
  call per question, metered through the existing cost meter.
- Answers are only as fresh/broad as the published-events set — acceptable and
  intentional (curated > comprehensive for v1).
- Adds a public LLM endpoint → must cap question length and rate-limit per the
  API-hardening conventions (ADR-0006).

## Alternatives considered

| Option | Rejected because |
|---|---|
| Retrieve from all enriched articles | Includes single-source/unverified + filtered junk; defeats the trust model. Deferred to a possible hybrid fallback |
| A separate agent framework (LangGraph/etc.) | Root ADR-0001 already rejected multi-agent frameworks; one `LlmService.structured()` call is enough |
| Pre-generate a static daily digest page | No Q&A, stale between cycles; the on-demand call is simpler and always current |
| Client-side summarization in the Reader | Would ship article text to the browser and a third LLM; keeps grounding + cost server-side instead |

## Future work

- Hybrid corpus fallback (published events → all enriched) when a query has thin
  published coverage.
- Cache digest answers per (category, cycle) so repeated "top 10 tech" taps in
  one cycle reuse one LLM call.
- Story-arc-aware historical answers (ADR-0013).

## Implementation checklist

- [x] `prompts/assistant.md` — grounding rule + digest/Q&A formats
- [x] `contracts/answer_v1.py` — `AnswerV1 { answer_md }` (sources assembled
      deterministically by the skill → no hallucinated URLs)
- [x] `skills/assistant.py` — `AssistantSkill.answer(question, mode)`
- [x] `core/api_server.py` — `POST /ask` (500-char cap; CORS allows POST)
- [x] Reader overlay component + discrete always-on floating round button + chips
- [x] Phase 2: pgvector retrieval over published events; free-form box

## Implemented (2026-06-09)

Phase 1 (digest) and Phase 2 (free-form RAG) shipped together. Notes from build:

- **Source list is deterministic, not LLM-emitted.** `AnswerV1` is just
  `{ answer_md }`; the skill numbers the retrieved candidates and returns them as
  `sources[]`, so the model can cite `[n]` but never fabricates a URL.
- **Chat retrieval ranks by nearest-article distance per event.** A first cut
  used `DISTINCT ON (event_id)` whose required `ORDER BY event_id` discards
  distance order — it returned arbitrary events. Fixed with an inner
  nearest-per-event query wrapped in an outer `ORDER BY dist`.
- **Reader UX:** clicking any source (inline `[n]` or the Sources list) dismisses
  the overlay (`setOpen(false)`) before client-navigating to `/event/{id}`.
- **Surfaces:** Reader `POST /api/ask` proxies to Curator `POST /ask`
  (`CURATOR_API_URL`). Floating button lives in `app/layout.tsx`.
- Deferred: per-(category,cycle) digest caching; rate limiting; hybrid corpus
  fallback; story-arc (ADR-0013) historical context.
