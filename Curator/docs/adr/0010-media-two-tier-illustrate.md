# ADR-0010 — Two-tier media strategy: passive extraction + IllustrateSkill

> *Status: Tier 1 (passive) implemented 2026-06-07 · Owner: Julian de la Rosa · Last updated: 2026-06-07*

## Context

Readers engage more with visual news. Published event pages have a headline,
synthesis, and evidence rail, but no images or video. Sourcing media requires
either (a) passive extraction from already-fetched HTML, or (b) an active
network-round-trip search (YouTube API, Bing Images).

Two quality tiers are possible:

| Tier | Effort | Coverage | Freshness |
|------|--------|----------|-----------|
| Passive extraction | zero extra HTTP | ~70 % of articles have og:image | near-zero — same scrape pass |
| Active search (Scrapling/YouTube/Bing) | 1–2 extra requests / event | ~95 %+ | requires a second pass |

## Decision

**Two-tier architecture:**

**Tier 1 — Passive** (implemented, this ADR):
Messor's `ArticleBuilder.buildFromNewspaper3K` extracts `article.top_image` and
`og:image` from already-fetched HTML at zero extra cost. If the article contains
a YouTube `<iframe>`, the URL is also captured. Both are stored in new DB columns
`articles.lead_image` and `articles.video_url`. The Curator API rolls up the
best `lead_image` per event (freshest article with a non-null image). The Reader
surfaces this as a cover photo on the Lead card, Secondary cards, and the event
detail page.

**Tier 2 — Active** (planned, not yet implemented):
A new `IllustrateSkill` (Curator Skill 4) will run after `SynthesizeSkill` for
events that lack a `lead_image`. It will search YouTube for matching footage and
Bing Images for editorial photos using the Scrapling library (anti-bot TLS
fingerprinting). Results are stored in `pages.media_rail JSONB`. This is Phase 2
and will be tracked in a future ADR.

## Why not merge the tiers?

Tier 1 is free — newspaper3k already parsed the HTML and `top_image` is a
first-class property. Adding Tier 2 work to every article scrape would (a)
double the per-article network cost, (b) add Scrapling as a Messor dependency
(Messor stays library-lean), and (c) require an LLM search-query generation step
that belongs in Curator's skill chain.

The boundary mirrors ADR-0005 (Messor/Curator responsibility split): Messor
extracts what's in the HTML it already has; Curator enriches with active network
calls.

## Data model changes

- `articles.lead_image TEXT` — og:image / top_image URL (Messor-provided)
- `articles.video_url TEXT` — first YouTube embed URL (Messor-provided)
- DB migration 008 (`008_article_media.sql`)
- `ArticleV1.lead_image`, `ArticleV1.video_url` fields (new, optional)
- `/events` and `/events/{id}` API: roll up `lead_image` from articles (freshest non-null)
- `EventSummary.lead_image` TypeScript type; Reader uses it in `LeadCard`, `SecondaryCard`, and event detail hero

## Consequences

+ Cover images appear immediately after the next Messor harvest for outlets
  that include og:image in their HTML (most major outlets do).
+ No new network cost in Messor, no new LLM calls.
+ Existing published pages have `lead_image = null` until re-scraped; the
  Reader degrades gracefully (no broken images).
- ~30 % of articles may lack og:image (outlets that don't set it, or very short
  articles). These fall through to Tier 2 (Phase 2).
- YouTube embeds in `video_url` are rare in text-heavy articles; Tier 2 active
  search is still needed for video coverage.
