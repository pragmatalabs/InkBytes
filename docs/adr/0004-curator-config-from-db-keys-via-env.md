# ADR-0004 (system) — Curator settings come from the DB; API keys stay in env

* **Status**: Accepted
* **Date**: 2026-06-03
* **Deciders**: Julián de la Rosa
* **Scope**: System-wide (Phase 2.1 of the backend consolidation)
* **Relates to**: [ADR-0001](./0001-consolidate-backend-into-laravel-backoffice.md) (Laravel Backoffice consolidation), [ADR-0003](./0003-backoffice-schema-isolation.md) (schema isolation), [backend-architecture.md](../backend-architecture.md) §6, [backend-handoff.md](../backend-handoff.md) Tab C

## Context

ADR-0001/§6 of `backend-architecture.md` say Curator should stop being
self-configured: its models, thresholds, and API keys should live in DB rows
the Backoffice edits, so an admin can change a model without a redeploy.

Two kinds of config are in play, and they are not the same risk:

1. **Tunables** — enrich/synthesize model, token caps, temperature, clustering
   thresholds. Non-secret; changing them changes pipeline behaviour. The
   Backoffice owns these in `backoffice.curator_settings` (Laravel migration,
   ADR-0003).
2. **Provider API keys** — the real `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`.
   Secret. The Backoffice wants to store/rotate/mask/test them, encrypted at
   rest with Laravel's `encrypted` cast (AES-256-GCM keyed by Laravel's
   `APP_KEY`).

The complication: **Curator is Python; the `encrypted` cast is Laravel/PHP
crypto.** For Curator to *use* keys from `backoffice.api_keys` it would have to
re-implement Laravel's AES payload format (IV + MAC + base64 envelope) and
share `APP_KEY` across two languages — fragile cross-language crypto for no
real v0 benefit, since the keys are already present in Curator's environment.

## Decision

**Env-keys with DB-for-management.**

1. **Settings from the DB.** `core/config.py` loads the
   **`backoffice.curator_settings`** row (schema-qualified — Curator's
   connection search_path is `public`) and overlays it onto the env/YAML
   config. The overlay mutates the live `LlmCfg` / `ClusterCfg` objects in
   place, which the skills and orchestrator hold by reference, so a change is
   visible on the next event.
2. **Refresh without redeploy.** The consumer runs a lightweight periodic
   re-read (`application.config_refresh_seconds`, default 30s). A change saved
   in the Backoffice takes effect within that interval — no restart.
3. **Env/YAML stays the fallback.** When the table or row is absent
   (fresh DB, Backoffice migrations not yet run) or unreadable, Curator keeps
   its env/YAML values. Fail-fast on a totally empty/unreachable *base* config
   is unchanged (`validate_secrets`).
4. **API keys are loaded from ENV ONLY.** Curator's key-loading
   (`_overlay_env` → `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) is **unchanged**.
   **Curator never reads or decrypts `backoffice.api_keys`.** That table exists
   purely so the Backoffice can store, rotate, mask (last-4) and *test* keys;
   values are encrypted at rest via the model's `encrypted` cast and never
   logged or returned unmasked.
5. **Full keys-from-DB is deferred.** When there is a real need (e.g. rotating
   a key without touching the host env), the cleanest path is the Backoffice
   *pushing* the active key into Curator's runtime over the existing control
   channel, or a shared secret store — not Python re-implementing Laravel's AES
   cast.

## Consequences

**Positive**

- Admin can change models/thresholds and Curator picks it up live — the §6
  goal, met for the non-secret config.
- No cross-language crypto: zero risk of a Python/PHP AES mismatch leaking or
  corrupting keys.
- Keys keep their existing, working bootstrap (env) — nothing regresses.
- `api_keys` is still a real, encrypted, testable vault in the admin.

**Negative / trade-offs**

- Rotating a provider key still requires updating the host env + a Curator
  restart; the admin vault does not yet feed Curator. Documented as deferred
  (decision §5).
- Two places hold key material conceptually (env for use, DB for management);
  they are not auto-synced in v0. The "test key" action mitigates drift by
  letting an admin verify the stored key independently.

## Alternatives considered

- **Curator decrypts `api_keys` directly.** Rejected: re-implementing Laravel's
  `encrypted` cast in Python + sharing `APP_KEY` is fragile cross-language
  crypto for no v0 benefit (keys are already in env).
- **Store keys in `curator_settings` in plaintext.** Rejected: violates the
  handoff's "encrypted at rest, never logged" rule.
- **RabbitMQ `curator.config.changed` push instead of polling.** Reasonable,
  but Laravel has no AMQP client installed (only a Monolog suggestion in the
  lock file) and adding one is out of scope for 2.1. A 30s poll meets
  "without redeploy" with zero new dependencies; the push can replace it later
  without changing the read path.
