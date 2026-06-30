# Curator ADR-0038 — Adapt to DeepSeek peak-valley pricing

> *Status: **accepted** — implemented 2026-06-28 (committed, NOT deployed) · Owner: Julian · Date: 2026-06-28*

## Context

DeepSeek adopts **peak-valley pricing from mid-July 2026**: peak-hour prices are
**2× the regular rate, all billing items**. Peak windows (UTC): **01:00–04:00 +
06:00–10:00** (= 7 h/day; UTC+8 09:00–12:00 + 14:00–18:00).

InkBytes bills DeepSeek for **both** ENRICH (`deepseek-chat`) and SYNTHESIZE
(`deepseek-reasoner`) — the whole pipeline + `/ask`. If usage were uniform, doing
nothing ≈ **+29% on the DeepSeek line** (`(17·1 + 7·2)/24`). On ~$3–4/day that's
~$30/mo. Modest, but free to avoid.

Key constraint: most DeepSeek cost is **live news processing**, and freshness is
the product — so "stop processing during peak" is the wrong trade. The peak UTC
window (01–10) is, however, **overnight in the Americas** (the LATAM-primary
audience), where routine news volume is low.

## Decision — valley-phase the harvest + peak-aware cost meter (freshness-neutral)

1. **Messor: anchor the scheduled harvest to valley UTC hours.** New config
   `scraping.harvest_anchors_utc` (env `MESSOR_HARVEST_ANCHORS_UTC`); when set, the
   scheduler sleeps to the next anchor hour instead of a flat interval. Prod set to
   `0,4,5,10,12,14,16,18,20,22` — ~10×/day, **all outside the peak windows**, so the
   bulk of enrich/synthesize bills at the regular rate. The routine sweep pauses
   during the overnight-Americas peak; the **pulse lane (breaking news) still runs**,
   and breaking *should* process immediately regardless of cost. Empty/unset →
   legacy interval mode (backward compatible).
2. **Curator: peak-aware cost meter.** `cost_meter.py` now **accumulates cost
   per-call**, applying a 2× multiplier when the call lands in a peak UTC hour
   ({1,2,3,6,7,8,9}) — frozen at record time so the running total stays correct as
   the rate changes through the day (previously cost was re-derived from token
   totals, which would have mis-priced once the rate varied). Gated by
   `llm.deepseek_peak_pricing` (env `DEEPSEEK_PEAK_PRICING`, default **off** — flip
   to true when the policy goes live). Accurate `model_usage` records + a `PEAK`
   marker in the COST log.

Rejected (for now): a **peak-deferral gate** (requeue non-urgent enrich during peak,
process in valley) — more savings but delays news; bad trade for ~$1/day. Revisit
if the measured peak exposure is large.

## Consequences

- Most LLM spend shifts to the regular rate with no daytime-Americas freshness loss.
- Cost reporting stays accurate once peak pricing is live (flip the flag mid-July).
- The anchor set is config — tune density/spacing without code. Breaking news
  unaffected (pulse lane + the on-demand Breaking Desk bypass the schedule).
- Activation: deploy; set `MESSOR_HARVEST_ANCHORS_UTC` (already in `env.yaml`) and,
  mid-July, `DEEPSEEK_PEAK_PRICING=true` in `infra/.env`.
