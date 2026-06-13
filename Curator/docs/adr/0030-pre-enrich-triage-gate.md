# Curator ADR-0030 — Pre-enrich triage gate (local model)

> *Status: accepted (shadow) · Owner: Julian · Date: 2026-06-13*

## Context

DeepSeek spend is dominated by **enrich** — ~6,800 calls/day, ~$15/day (synth
is fewer calls at ~$6/day). A meaningful share of harvested articles are
filler that should never reach the paid enrich call: horoscopes, lottery
results, sports-betting tips, pure deals/affiliate roundups, bare
fixture/TV-schedule listings, and dead pages (paywall/login/error/captcha).
Today the promo/noise filters (ADR-0020/0021) are deterministic regex that run
at *synthesis* — i.e. **after** the article has already been enriched, so the
enrich cost on junk is already spent.

The Hostinger Ollama box (`82.112.250.139`, 4 vCPU / 16 GB, CPU-only) sits
mostly idle (load ~0.05) between embedding bursts. It can run **short-output**
work across the full article volume; it cannot run long-output generation
(full enrich, synthesis) at volume (throughput wall, ADR-0026 addendum).

## Decision

A **pre-enrich triage gate**: a small local model (`qwen2.5:3b` on Hostinger)
classifies each *to-be-enriched* article as `keep | junk` from its title +
lede, before the DeepSeek enrich. `junk` is dropped (no enrich/cluster/synth);
the raw article is still stored.

- **Placement** (`application._handle_event`): *after* the dedup fast-path SKIP
  (so it only runs on articles that would actually be enriched) and *before*
  `enrich.run`. Exactly the calls we want to gate.
- **Stateless, junk-only.** Near-duplicate detection is NOT here — that needs
  corpus context and is already handled by the content-hash fast-path
  (ADR-0015/0018) + embedding clustering. The gate judges single-article filler.
- **Fail OPEN.** Any error, timeout, or unparseable reply → `keep`. The gate
  must never drop a real article because the local model hiccuped. Timeout 12s
  (warm classify ~1-3s; cold model load ~20s → times out → keep).
- **Bounded concurrency** (`_triage_sem`, default 2): don't hit the 4-CPU box
  with `max_concurrent_articles` parallel generations (same lesson as
  `_embed_sem`).
- **Precision-first prompt** (`prompts/triage.md`): when in doubt, keep. Only
  clear filler is `junk`. News *about* betting/lottery, or a product launch as
  a news event, stays `keep`.

### Shadow mode first

`triage.shadow = True` (default): the gate runs and **logs** its verdict
(`TRIAGE shadow-DROP …`) but does NOT drop — so we measure the drop rate and
eyeball false positives against real enrich for a day before enforcing. Flip
`TRIAGE_SHADOW=false` to enforce once the verdicts look clean.

### Config (env-overridable)

```
triage.enabled  (TRIAGE_ENABLED)   default False — master switch
triage.shadow   (TRIAGE_SHADOW)    default True  — log-only
triage.base_url (TRIAGE_BASE_URL)  default localhost:11434/v1 → Hostinger in prod
triage.model    (TRIAGE_MODEL)     default qwen2.5:3b
triage.timeout_s 12 · triage.max_concurrent 2
```

Prod (infra/.env on the droplet): `TRIAGE_ENABLED=true`, `TRIAGE_SHADOW=true`,
`TRIAGE_BASE_URL=http://82.112.250.139:32768/v1`, `TRIAGE_MODEL=qwen2.5:3b`.

## Verification (local, llama3.2:3b)

6 samples: real news → keep; horoscope/lottery/deals → junk; betting-fraud
*investigation* → keep (the precision case); fixture listing → keep (errs to
the safe side). The prompt + parsing + fail-open all behave.

## Expected impact

If ~15-25% of the ~6,800 daily articles are filler, the gate cuts ~1,000-1,700
DeepSeek enrich calls/day (~$2-4/day) **and** keeps junk out of clustering.
Shadow mode measures the real rate + precision before any article is dropped.

## Watch-items (measured in shadow)

- **Throughput**: triage adds an inline call before enrich. Bounded to 2
  concurrent + 12s fail-open, but watch the enrich rate and `TRIAGE error`
  (timeout) frequency — if the box thrashes (qwen2.5:3b vs bge-m3 model
  swapping), errors rise (still safe: fail-open). Mitigation if needed: pin
  `OLLAMA_MAX_LOADED_MODELS`/`keep_alive` on the box, or a smaller model.
- **Precision**: `TRIAGE shadow-DROP` lines are the audit log — confirm no real
  stories before flipping `shadow=false`.

## Addendum — first shadow batch (2026-06-13)

The first live cycle exposed two things, exactly what shadow mode is for:

1. **Wrong model shipped.** The model validated locally (6/6) was `llama3.2:3b`,
   but `qwen2.5:3b` was deployed. qwen produced 2/2 **false** drops on its first
   two verdicts — "King Charles birthday" → *horoscope*, a World-Cup **preview**
   → *betting tips*. Switched the default to **`llama3.2:3b`** (warm ~0.7 s on
   the box; fixes the birthday nonsense).
2. **3B can't resolve sports-preview vs betting-tip.** Both 3B models flag
   "¿cómo jugará Brasil…?" as betting. That boundary is too fine for a 3B model,
   so the **sports-betting and bare-fixture categories were removed from the
   triage prompt** — the prompt now says *sports is ALWAYS keep*. No coverage
   lost: betting/noise filler is still gated deterministically at synthesis
   (`content_filter`, ADR-0021). Triage now only judges the categories 3B nails:
   horoscopes, lottery, shopping/deals, dead pages.

**Bigger models are not viable here** (measured on the box): `mistral:7b` ~81 s,
`gemma4:12b` HTTP 500 @ 37 s — both blow the 12 s timeout → fail-open no-op. The
CPU box's ceiling for an inline pre-enrich gate is the 3B class.

**Thrash watch:** the first batch showed **0 `TRIAGE error`** and `ollama ps`
showed no eviction storm — `OLLAMA_MAX_LOADED_MODELS` (unset → 1 on CPU) has not
bitten yet. If the error rate climbs once volume rises, set
`OLLAMA_MAX_LOADED_MODELS=2` on `ollama-ifkx-ollama-1` so bge-m3 + the triage
model stay co-resident (~3 GB combined, 13 GB free).
