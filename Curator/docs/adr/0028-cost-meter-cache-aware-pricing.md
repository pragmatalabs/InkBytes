# Curator ADR-0028 — Cache-aware cost metering at real v4-flash rates

> *Status: accepted · Owner: Julian · Date: 2026-06-12*

## Context

The `CostMeter` (and the `backoffice.model_usage` rows + `COST` log lines it
writes) overstated LLM spend by ~15×. On 2026-06-12 it reported ~$62/day while
the actual DeepSeek invoice was **$4.65**. Two compounding errors:

1. **Wrong prices.** Config defaulted to `price_in=$1.0/M`, `price_out=$5.0/M`
   (Claude-Haiku-era list prices). Production runs **`deepseek-v4-flash`**:
   `$0.14/M` input (cache-miss), `$0.28/M` output → output alone was ~18× over.
2. **No cache accounting.** DeepSeek bills *cached* input tokens at **$0.0028/M**
   — ~50× cheaper than uncached. Roughly half of production input is cache
   hits (the reused system prompt/prefix). The meter charged every input token
   at the full rate, missing the single biggest discount.

## Decision

Price input in two tiers and use the real v4-flash rates (LlmCfg defaults):

| field | rate | meaning |
|---|---|---|
| `price_in_per_mtok` | `0.14` | cache-**miss** input ($/Mtok) |
| `price_cache_hit_per_mtok` | `0.0028` | cache-**hit** input ($/Mtok) |
| `price_out_per_mtok` | `0.28` | output ($/Mtok) |

`CostMeter` now takes the cache-hit rate and computes
`cost = miss·in + hit·cache_hit + out·out`, where `miss = input − hit`. The
cache-hit token count comes from the provider usage object, extracted in
`LlmService` across all shapes:

- DeepSeek native: `usage.prompt_cache_hit_tokens`
- OpenAI-compat: `usage.prompt_tokens_details.cached_tokens`
- Anthropic: `usage.cache_read_input_tokens`
- none present → `0` (falls back to charging all input at the miss rate)

`cache_hit_tokens` threads through `record()` → `_Bucket` → `_call_cost` →
the DB sink's `cost_usd`. When no cache-hit rate is supplied the meter
collapses to the old single-rate behaviour (backward-compatible).

Prices are NOT in `_DB_SETTINGS_MAP`, env, or prod `.env`, so these defaults
are authoritative in production with no further config.

## Verification

Fed the meter the real 06-12 token totals from the DeepSeek usage export
(out 7.73M, cache-hit 14.77M, cache-miss 17.45M):

- new meter → **$4.6487**, matching the invoice ($4.6486508) to the cent
- old meter (flat $1/$5, no cache) → $70.86 (15.2× over)
- extraction unit-tested against DeepSeek / OpenAI / Anthropic / no-cache usage

## Consequences

- The Backoffice cost dashboard and `COST` log lines now match the invoice.
- Real steady-state is **~$3–4/day (~$100/mo)** at current volume, not the
  ~$25–35/day previously (wrongly) reported.
- The `COST` log line gains a `cache_hit=` field; `model_usage.cost_usd` is now
  accurate (no schema change — `model_usage` has no cache column; the discount
  is folded into `cost_usd`).
- Note: the `Inkbytes_Beta` API key bills dev/local testing to the same paid
  account (~$1–2/day) — separate dev billing is a follow-up, not part of this ADR.
