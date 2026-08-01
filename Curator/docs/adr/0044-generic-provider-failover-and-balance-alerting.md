# ADR-0044 — Generic LLM provider failover + proactive balance alerting

> *Status: v1 · Owner: Curator · Last updated: 2026-08-01*

## Context

On 2026-08-01 the production feed froze for ~14 h. Root cause: the active LLM
provider was direct `deepseek`, its prepaid balance hit **$0**, and every
enrich/synth call returned `402 Insufficient Balance`. Curator's
`LlmService.structured()` classified that as a quota wall and raised
`LlmQuotaError` → the worker requeued the article (no loss) and **halted** →
no new pages until a human topped up. Two independent failures made it a 14 h
outage rather than a blip:

1. **No failover on the direct-provider path.** ADR-0041 added an OpenRouter→
   direct-DeepSeek fallback, but it *only* fired when `provider == "openrouter"`.
   With `provider == "deepseek"`, a 402 had nowhere to go.
2. **No alert.** The only notifier in the system is end-user web-push (ADR-R-0012);
   there was no ops channel, so nobody knew the balance was low until the feed
   was visibly stale.

Auto-recharge is deliberately **out of scope** — executing a top-up is a
financial action; it belongs in the DeepSeek account's own auto-recharge
setting, not in Curator.

## Decision

### 1. Generic provider failover (`services/llm_service.py`)

Generalize the one-directional ADR-0041 fallback into a provider-agnostic one:
when the **active** provider hits a credit/quota wall, transparently retry the
**same** structured call on a configured `fallback_provider` that uses a
**different account/balance**.

- `LlmCfg.fallback_provider` (`"" | openrouter | deepseek | anthropic | openai`)
  and optional `fallback_model`. **Env-only** (`LLM_FALLBACK_PROVIDER`,
  `LLM_FALLBACK_MODEL`) — intentionally *not* in `_DB_SETTINGS_MAP`, so the
  periodic Backoffice `curator_settings` overlay can never clobber it.
- `_resolve_fallback(model)` → `(client, provider, model)`:
  - generic path: build a provider-swapped `cfg.model_copy` and reuse
    `_build_client` (clearing `base_url`, which is the primary's endpoint);
  - legacy path preserved: `openrouter` primary → direct DeepSeek (ADR-0041).
- `_fallback_model()` translates the active model to the fallback's namespace
  (`deepseek-chat` → `deepseek/deepseek-chat` for OpenRouter; strip for
  DeepSeek/OpenAI; a Haiku default for Anthropic). Explicit `fallback_model` wins.
- `_build_call_kwargs()` builds **provider-correct** kwargs for BOTH the primary
  and the failover call (Anthropic `system=` vs OpenAI-compat system message;
  OpenRouter `models[]` chain), so a cross-provider failover is wire-correct.
- Only if the fallback ALSO returns a quota error is `LlmQuotaError` raised
  (`"'X' primary AND 'Y' fallback BOTH quota-exhausted"`) → worker halts as before.

**Prod config:** `LLM_FALLBACK_PROVIDER=openrouter` (chosen 2026-08-01). Requires
`OPENROUTER_API_KEY` set **and the OpenRouter account funded** — the fallback is
only as good as its own balance.

### 2. Proactive balance alerting (`services/balance_monitor.py`, `services/ops_alert.py`)

- **`OpsAlerter`** — a dependency-free, best-effort webhook pager. Env:
  `OPS_ALERT_WEBHOOK_URL` (Slack incoming webhook / Telegram sendMessage URL /
  any `{"text":…}` sink), `OPS_ALERT_WEBHOOK_KIND` (`slack`|`telegram`|`generic`),
  `OPS_ALERT_TELEGRAM_CHAT_ID`, `OPS_ALERT_COOLDOWN_SECONDS` (default 3 h per key).
  Inert (logs only) with no URL; any send failure is swallowed.
- **Balance monitor** — polls DeepSeek `GET /user/balance` every
  `OPS_BALANCE_POLL_SECONDS` (default 30 min) and pages when the USD balance is
  below `DEEPSEEK_LOW_BALANCE_USD` (default $2) or `is_available` is false — i.e.
  *before* the freeze. Started **only from the `--api-only` container** (the
  single instance) so it polls/pages once, not once per worker replica.
- **Reactive alert** — the worker's `on_quota_exhausted` (reached only when the
  primary AND fallback are both exhausted, or no fallback is set) also pages,
  cooldown-throttled.

## Consequences

- A dead primary balance degrades to the fallback provider instead of freezing
  the feed. A true freeze now requires BOTH accounts to be exhausted.
- A human is paged *before* (low balance) and *at* (both exhausted) a freeze.
- One cheap balance GET every 30 min from a single container. Failover adds
  latency only on a quota error (rare), and the fallback provider's per-token
  price applies only while the primary is down.
- The failover is **only as resilient as the fallback account's balance** — keep
  OpenRouter funded; the low-balance monitor watches DeepSeek (the primary).

## Required env (droplet `infra/.env`) to activate

```
LLM_FALLBACK_PROVIDER=openrouter          # OPENROUTER_API_KEY must be set + funded
OPS_ALERT_WEBHOOK_URL=<slack-or-telegram-webhook>
OPS_ALERT_WEBHOOK_KIND=slack              # or telegram (needs OPS_ALERT_TELEGRAM_CHAT_ID)
# optional: DEEPSEEK_LOW_BALANCE_USD=2  OPS_BALANCE_POLL_SECONDS=1800  OPS_ALERT_COOLDOWN_SECONDS=10800
```

With no env set, all of this is inert — behaviour is identical to today (no
failover, log-only alerts), so the code is safe to ship before the env is wired.

## Testing

Offline unit tests (`scratchpad/test_resilience.py`) cover: primary 402 →
OpenRouter failover with model translation; no-fallback → `LlmQuotaError`; both
dead → `LlmQuotaError`; model translation (openrouter/anthropic/deepseek);
provider-correct kwargs; alerter cooldown + no-webhook safety; balance-JSON
parse. A live end-to-end failover needs a real 402, exercised on next deploy.

## Rollback

Unset `LLM_FALLBACK_PROVIDER` (failover off) and `OPS_ALERT_WEBHOOK_URL` (alerts
log-only) — no redeploy needed; both are read live from env at process start.
Code revert: the new `services/ops_alert.py` + `services/balance_monitor.py`, the
`structured()`/`_resolve_fallback` refactor, and the two `LlmCfg` fields.
