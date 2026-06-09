# ADR-0020 — Promotional / commerce content filter

> *Status: accepted / implemented · Owner: Julián · Last updated: 2026-06-09*
>
> Keeps affiliate/shopping content from publishing as fake news events.

## Context

A published page appeared titled **"Guardian Covers Top New Mom Gifts and Sonos
Speaker Reviews."** Its source cluster was built entirely from The Guardian's
shopping/affiliate vertical:

```
The 10 best US gifts for new moms, according to a new mom
Sonos review: Are these the best portable speakers that money can buy?
I tried 10 laundry baskets to find the best hamper in the US
The best cordless leaf blowers in the US …
The best bath towels of 2026 in the US … – tested
Dyson v Bissell: I compared their latest lightweight stick vacs head to head
… (14 articles, all theguardian, all product roundups/gift guides)
```

These are not news. Affiliate/commerce articles cluster together (shared
entities + embeddings) and synthesize into an ad-style page. The Reader then
shows a "story" that is really a shopping roundup.

This is distinct from news that merely *mentions a brand* ("Apple Unveils Siri
Overhaul", "Nvidia and Intel Vie for AI Chip Dominance") — those must keep
publishing. The target is **commerce / affiliate / product-purchase** content and
other-outlet product promos.

## Decision

A deterministic, high-precision promo classifier
([`services/promo_filter.py`](../../apps/curator/services/promo_filter.py)) —
`is_promotional(text)` / `promo_reason(text)` — matches commerce phrasing:

- **gift guides** — "gift guide/ideas", "best gifts", "N gifts for mom/dad/…"
- **product reviews / first-person testing** — "review:", "I tried/tested/compared/cut up/bought", "tested and reviewed", "hands-on review"
- **product listicles** — "the N best `<product>`" / "best `<product>` of YEAR | in the US | to buy" (gated by a product-noun lexicon so editorial "best shows/films/cities" are kept)
- **price/deal ads** — "N% off / N% de descuento", "price cut", "lowest price", "precio mínimo histórico", "cae un N%", "rebajas", "best/top deals", "shop now"
- **ad-style synthesized headline** — "X Covers/recommends/picks Top|Best … gifts/deals/reviews/products"

The gate lives in **SynthesizeSkill** (`skills/synthesize.py`), the publish point:

1. **Pre-LLM cluster gate** — if a *strict majority* of the event's article titles
   are promotional, skip synthesis entirely (don't pay to synthesize an ad page).
   The Guardian cluster flags 9/14 = 64% → skipped.
2. **Post-LLM headline backstop** — even a mixed cluster can yield an ad-style
   headline; if `promo_reason(page.headline)` fires, don't persist/publish.

A skipped event simply stays unpublished. Toggle:
`application.filter_promotional` (default `true`).

A one-time backfill
([`scripts/backfill_promo_pages.py`](../../apps/curator/scripts/backfill_promo_pages.py))
re-applies the rule to already-published pages and un-publishes the commerce ones
(`pages.published_at = NULL`; reversible).

## Precision

Tuned against the live corpus: **1 / 282** published page headlines flagged (the
Guardian ad) and **17 / 4 000** distinct article titles — all genuine
commerce/deals on manual review. Deliberately precision-first; ambiguous Spanish
verbs are disambiguated:

- `liquida` = clearance sale **or** layoffs ("liquida a sus 600 empleados") → only flagged with an accompanying % / precio.
- `rebaja` (singular) = a ratings downgrade ("rebaja la calificación") → only the plural sale noun `rebajas` counts.
- bare "record low" = an economic indicator ("consumer sentiment record low") → requires "record/lowest **price**".

News *about* shopping events (Black Friday fraud tips, Prime Day inflation
coverage, "el fenómeno de las microcompras") and editorial best-of ("Best coffee
city in the world?", "the seven best shows to stream") are kept.

## Consequences

- Commerce clusters no longer publish; soft-affiliate titles the per-title rule
  misses are still caught by the majority-cluster signal (the strong titles tip it).
- Promo articles still get enriched/embedded/clustered (negligible: ~0.35% of
  titles) — we gate at publish, not ingest, so the majority signal stays intact.
- When in doubt the filter KEEPS the item — a stray ad is cheaper than dropping
  real news.

## Alternatives considered

- **Drop promo articles at ENRICH.** Saves a little LLM cost, but removing the
  strong-promo articles before clustering would weaken the majority-cluster signal
  at synthesis (the soft-affiliate remainder wouldn't trip it). Rejected in favor
  of a single publish-point gate.
- **LLM classification of content type.** More robust to novel phrasing but adds a
  per-article LLM call and latency; the deterministic filter already covers the
  observed corpus. Revisit if new commerce phrasings slip through.
