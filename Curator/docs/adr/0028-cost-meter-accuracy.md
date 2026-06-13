# Curator ADR-0028 — Cost-meter accuracy: real v4-flash rates + cache-hit split

> *Status: accepted · Owner: Julian · Date: 2026-06-12*

## Context

The Backoffice cost dashboard and every `COST` log line overstated spend by
**~15×**. Reconciling against the actual DeepSeek invoice (2026-06):

| | Backoffice estimate | Real invoice |
|---|---|---|
| 2026-06-12 (catch-up day) | ~$70 | **$4.65** |
| 7-day average | — | ~$3.5/day |

Two root causes in `CostMeter` / `LlmCfg`:

1. **Wrong list prices.** Config defaulted to `price_in=1.0`, `price_out=5.0`
   (Claude Haiku 4.5 rates). Production actually runs **`deepseek-v4-flash`**:
   `$0.14/M` input (cache-miss), `$0.28/M` output. Output alone was 18× over.

2. **No cache-hit accounting.** DeepSeek bills cached input tokens at
   **`$0.0028/M`** — ~50× cheaper than uncached. Production runs ~45–50% cache
   hits (the reused system prompt / prefix). The meter charged every input
   token at the full rate, ignoring `prompt_cache_hit_tokens` entirely. On
   06-12 that mis-billed 14.8M cached tokens at $1.0/M (~$15) instead of
   $0.0028/M (~$0.04).

## Decision

1. **`LlmCfg` prices → v4-flash, with a cache-hit rate added:**
   ```
   price_in_per_mtok        = 0.14     # cache-MISS input
   price_cache_hit_per_mtok = 0.0028   # cache-HIT input
   price_out_per_mtok       = 0.28     # output
   ```
2. **`CostMeter` splits input by cache hits.** `record(...)` gains a
   `cache_hit_tokens` kwarg; cost = `miss·in_price + hit·hit_price +
   out·out_price` (where `miss = input_tokens − cache_hit_tokens`). The COST
   log line now prints `cache_hit=`, and `snapshot()`/`model_usage` carry the
   accurate `cost_usd`. When no cache-hit rate is configured the meter falls
   back to the full input rate — i.e. identical to the old behaviour, so
   non-DeepSeek providers are unaffected.
3. **`LlmService` extracts the cache-hit count** from the completion usage,
   provider-agnostic: DeepSeek `prompt_cache_hit_tokens` → OpenAI-compat
   `prompt_tokens_details.cached_tokens` → Anthropic `cache_read_input_tokens`
   → `0`.

## Verification

Fed the meter 06-12's exact invoice token counts (7.73M output, 17.45M
cache-miss input, 14.77M cache-hit input): meter computes **$4.6487** vs the
invoice's **$4.6487** — exact. The pre-fix meter computes $70.86 (15× over).

## Consequences

- Backoffice cost dashboard now matches the DeepSeek invoice.
- Real steady-state spend is **~$3–4/day (~$100/mo)** at current volume, not
  the ~$25–35/day previously (mis)reported.
- Prices live in config/env — switching models or providers means updating
  three numbers, not code.
- **Schema note:** `model_usage` stores accurate `cost_usd` now but has no
  column for the hit/miss split; only the derived cost is persisted. Add a
  `cache_hit_tokens` column later if per-token cache analytics are wanted.
- Follow-up (separate): the `Inkbytes_Beta` API key bills dev/local testing to
  the same paid account as prod (`inkbytes-prod3`); worth isolating dev spend.
