# ADR-0041 — OpenRouter provider: per-task routing, fallback chains, provider-level DeepSeek fallback, per-model cost, Backoffice-managed

> *Status: v1 · Owner: Julian · Date: 2026-07-28 · **Curator DEPLOYED (provider + routing + fallback chains + per-model cost + base_url-signature fix, droplet HEAD `7e9915d`-lineage); provider-level DeepSeek fallback + Backoffice UI committed, Backoffice migration/UI pending local test + deploy***

## Context

Curator's LLM backend was **direct DeepSeek** (`deepseek-v4-flash`, OpenAI-compatible
`api.deepseek.com`). A DeepSeek quota/rename wall (`deepseek-chat` retired) had
already stalled the enrichment pipeline for ~20h once. We wanted:

1. **Quota resilience** — a second account/route so a provider quota wall degrades
   instead of stalling the whole pipeline.
2. **Per-task cost/quality control** — cheap model for the high-volume enrich path,
   a better model for reader-facing synthesis, without running two providers.
3. **No-SSH operation** — flip provider/models/fallbacks from the Backoffice with
   hot-reload (ADR-0004), not env edits + redeploys.

[OpenRouter](https://openrouter.ai) is an OpenAI-compatible **aggregator**: one
account + key + endpoint reaches DeepSeek, OpenAI (gpt-oss), Google (Gemini),
Meta (Llama), Qwen, Anthropic, … with namespaced slugs (`deepseek/deepseek-v4-flash`).

## Decision

### 1. OpenRouter as a first-class provider (Curator)
`provider=openrouter` on the existing OpenAI-compatible path in `llm_service.py`
(`base_url` default `https://openrouter.ai/api/v1`, **JSON mode** — DeepSeek-family
models reject `tool_choice`). Key: `openrouter_api_key` (env `OPENROUTER_API_KEY`
or the Backoffice DB column). Additive — the `anthropic`/`openai`/`deepseek`
branches are untouched.

### 2. Per-task model map (no code — existing knobs)
Curator already splits `enrich_model` vs `synthesize_model`; through one OpenRouter
account they can be different slugs. Settled config (cost-driven, after a live
bake-off): **both** `deepseek/deepseek-v4-flash` (cheapest — non-reasoning/concise
output + prompt-cache hits; qwen/gpt-oss are reasoning models → ~1.8–5k output
tokens/call → dearer; gemini-2.5-flash best prose but $2.50/M output ≈ 5–9× others).

### 3. Two-layer fallback
- **Model-array (within OpenRouter):** `structured()` passes an ordered
  `extra_body.models` array (primary + per-task `enrich_fallbacks` /
  `synthesize_fallbacks`). If the primary model errors/rate-limits, OpenRouter
  tries the next. Covers a single model being down — **not** the whole account.
- **Provider-level (OpenRouter → direct DeepSeek):** on a quota/credit error
  (`402` / "insufficient credits" / "insufficient_quota"), retry the SAME call on
  the **direct** `api.deepseek.com` endpoint (`deepseek_api_key`), stripping the
  OpenRouter-only `extra_body` and translating the slug
  (`deepseek/deepseek-v4-flash`→`deepseek-v4-flash`; non-DeepSeek → configured
  default). Both exhausted → `LlmQuotaError`. Gated by
  `openrouter_deepseek_fallback` (default on) + a DeepSeek key. This is the real
  cure for the whole OpenRouter account running out of credits.

### 4. Per-model cost accounting
The cost meter took a single price pair, inaccurate once enrich/synth run different
models. Added `llm.model_prices` (slug→{in,out[,cache_hit]}); `CostMeter._call_cost`
resolves the per-call model, falling back to the pair for unknown slugs.

### 5. `base_url` in the client-rebuild signature (bug fix)
`_signature()` omitted `base_url`, which is baked into the client at build time. A
live provider flip that changed only the endpoint kept the OLD endpoint until a
container restart — on the cutover this sent OpenRouter requests to
`api.deepseek.com` → 401. Adding `base_url` to the signature makes an endpoint
change force a rebuild on hot-reload. (Also: `apply_db_settings` SKIPS NULL columns,
so set `llm_base_url` **explicitly** per provider — never rely on NULL to "clear" it.)

### 6. Backoffice-managed, hot-reloaded (this is the "no-SSH" goal)
New `backoffice.curator_settings` columns, wired into Curator's `_DB_SETTINGS_MAP`
so they hot-reload (Curator reads `SELECT *`, so adding columns is safe/ordered-
independent): `openrouter_api_key` (masked in UI + `_API_KEY_COLUMNS` empty-skip),
`llm_enrich_fallbacks` / `llm_synth_fallbacks` (comma-separated TEXT →
`apply_db_settings` now splits list-typed fields; empty = keep env), and
`openrouter_deepseek_fallback` (bool). Backoffice (Laravel + Inertia/React):
migration + `config/curator.php` allowlist (`openrouter` provider + namespaced
model suggestions) + `CuratorSetting` fillable/casts + `CuratorSettingController`
edit/validate/mask + a "OpenRouter routing" section on `Settings/Index.jsx`
(fallback-chain text fields + a Switch, shown when provider=openrouter).

## Alternatives considered

| Option | Rejected because |
|---|---|
| OpenRouter `openrouter/auto` meta-router | Unpredictable cost + model; hard to debug clustering when the model changes under you. A fixed per-task map is forecastable. |
| Keep direct DeepSeek only | A single quota wall stalls the whole pipeline (already happened once). No second route. |
| Provider fallback via a config flag only (env) | The whole point was Backoffice hot-reload; env-only means SSH + redeploy to change routing. |
| Read OpenRouter's per-call `usage.cost` for accounting | More accurate but provider-specific + invasive; a static `model_prices` map is good enough for "accounting only". Noted as a future upgrade. |

## Consequences

- Quota resilience in depth: model-array fallback for a single model, provider
  fallback to direct DeepSeek for the whole account. Both verified against the
  live API (a 404/402 primary routes to the next; the fallback retry unit-tested).
- Model routing + fallbacks + the OpenRouter key are now Backoffice knobs
  (hot-reload ~30s), no SSH/env edit or redeploy for a model swap.
- **Account restriction learned:** Google + Anthropic models 404 "No allowed
  providers" unless the OpenRouter account's Privacy/data-policy allows those
  upstreams. Working on this key: gpt-oss-120b, deepseek-v4-flash, llama-3.3-70b,
  qwen3.7-flash/qwen3-max, and (after the user unblocked it) gemini-2.5-flash(+lite).
- **Reasoning-model verbosity:** qwen3.7-flash / gpt-oss-120b emit 1.8–5k output
  tokens/enrich, so cheap per-token rates don't make them cheapest; deepseek-v4-flash
  wins enrich on concise output + cache hits.
- Rollback to direct DeepSeek is one Backoffice/DB change (provider=deepseek,
  models=deepseek-v4-flash, llm_base_url=api.deepseek.com) — no code path removed.
- Commits: `1fd7741` (provider), `0fe3682` (per-task routing + model-array fallbacks),
  `fbdb235` (base_url signature + doc fix), `7001f69` (per-model cost),
  `7e9915d` (provider-level DeepSeek fallback + DB-driven routing knobs); Backoffice
  migration/config/model/controller/React pending local verification + deploy.

## Security / compliance note

The OpenRouter key is stored plaintext in `backoffice.curator_settings` (same
boundary + UI masking + audit-mask as the other `*_api_key` columns) with an env
fallback; never echoed to the UI. All code here is AI-generated and must pass the
organization's approved SAST scan + a documented human review before production,
per bank policy; keys must never be committed to git or pasted in chat (the
OpenRouter key used during the cutover was pasted in chat and should be rotated).
