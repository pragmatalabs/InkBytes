# ADR-0021 — Non-news filler filter: no horoscope / lottery / betting pages

> *Status: accepted · Owner: Julian · Date: 2026-06-09*

## Context

As the outlet catalogue expanded to LATAM/ES and European general-interest
dailies, the harvester started ingesting recurring **non-news filler** that
those outlets publish every day alongside real reporting:

- **Horoscopes / astrology** — "Horóscopo de hoy: predicciones para tu signo"
- **Lottery results & number picks** — "Resultados de la Lotería Nacional:
  números ganadores", "Powerball winning numbers", "Quiniela de hoy"
- **Sports-betting tips / projections** — "Pronósticos deportivos de la jornada"

This content is worse than promotional content (ADR-0020) for clustering: every
outlet runs a *daily* horoscope and lottery roundup, so they cluster strongly by
recurrence across sources and synthesize into junk pages that crowd out news in
the Reader feed.

## Decision

Add a deterministic, high-precision filter `services/content_filter.py`
(`is_excluded()` / `exclusion_reason()`), parallel to the promotional filter, and
gate publishing in `SynthesizeSkill` exactly as ADR-0020 does:

1. **Cluster gate (pre-LLM):** skip synthesis when a *strict majority* of the
   cluster's article titles are filler — `noise * 2 > len(titles)`. Saves the
   LLM call entirely.
2. **Headline backstop (post-LLM):** refuse to persist a page whose synthesized
   headline is filler ("Horóscopo del día y resultados de la lotería").

Gated behind a config flag `application.filter_noise` (default `True`; env/YAML,
same as `filter_promotional`).

### Precision over recall

Same philosophy as ADR-0020 — **when in doubt, KEEP**. The patterns target
unambiguous filler and deliberately avoid:

- Sign-name collisions — `Cáncer` (disease), Pope `León`, `Virgo`/`Virgin` brands.
  Only explicit astrology vocabulary (`horóscopo`, `zodiac`, `astrología`,
  `tarot`, `Sternzeichen`, `signe astrologique`) flags — never a bare sign name.
- Gambling **industry / regulation** news — a bare org name ("Lotería Nacional")
  is kept; only a result/number/draw signal flags.
- Weather "pronóstico" — betting patterns require an explicit betting context word
  (`apuestas`, `cuotas`, `tipster`, `pronósticos deportivos`), so
  "pronóstico del tiempo" is kept.
- Match previews / editorial predictions — kept (sports journalism).

EN + ES primary; FR/DE coverage for the European outlets.

## Verification

`scripts/test_content_filter.py` — 18 FLAG cases (real horoscope/lottery/betting
titles) all excluded, 12 KEEP cases (sign-name diseases/people, gambling-industry
news, weather forecasts, match previews) all clean. **0 false positives.** Promo
filter regression (`scripts/test_promo_filter.py`) still passes (35 checks).

Re-run both whenever patterns change.

## Consequences

- Horoscope/lottery/betting clusters no longer publish pages; the LLM call is
  skipped for majority-filler clusters (cost saving).
- Enrichment still runs on these articles (they're filtered at synthesis, not
  ingestion) — acceptable; a future optimisation could skip them at ENRICH.
- New filler patterns must keep the corpus test at ~0 false positives.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Extend `promo_filter.py` with these patterns | Semantically wrong — horoscopes aren't commerce; separate module keeps each filter's intent and corpus test clean |
| Drop at ENRICH (per-article) | More thorough but changes the ingestion hot path; the proven ADR-0020 synthesis-gate pattern is lower-risk. Revisit if enrichment cost on filler matters |
| Bare sign-name / keyword blocklist | Too many false positives (Cáncer, León, Virgo) — precision-first demands explicit astrology/lottery vocabulary |
