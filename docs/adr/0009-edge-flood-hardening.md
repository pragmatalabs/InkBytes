# ADR-0009 — Edge + app-level flood / DDoS hardening (single droplet)

> *Status: **accepted** — layers #2 + #3 implemented 2026-06-16 (committed, not yet deployed) · Owner: Julian · Date: 2026-06-16*

## Context

InkBytes runs on a single DigitalOcean droplet (`pragmata-001`, 7.8 GB) behind a
shared Traefik. Pre-hardening posture (audited 2026-06-16): **no rate limiting
anywhere** (Traefik / Curator API / Reader / Backoffice), **no CDN/edge** (origin
IP exposed, Let's Encrypt direct). Public attack surface = `inkbytes.org` (Reader)
+ `admin.inkbytes.org` (Backoffice); Curator API / Postgres / RabbitMQ are
internal-only.

The sharpest risk is **`POST /api/ask`** (Reader → Curator `/ask` → DeepSeek): a
public, unauthenticated, **LLM-backed** endpoint with no rate limit. A flood there
is simultaneously a denial-of-service *and* a cost-amplification attack (every
call spends LLM tokens + worker CPU). The Backoffice login is a brute-force
target (Breeze's `LoginRequest` already locks out 5 failed attempts per
email+IP, but a flood with *varying* emails from one IP bypasses that key).

A four-layer plan was proposed (#1 Cloudflare, #2 Traefik middleware, #3 app
throttle, #4 fail2ban/firewall). The owner selected **#2 + #3** for now;
**#1 (Cloudflare) and #4 (fail2ban) are deferred** (Cloudflare needs a DNS
migration + dashboard work and is the bigger anti-volumetric win — revisit).

## Decision

### Layer #2 — Traefik per-IP middleware (`infra/docker-compose.do.yml` labels)
Per-router `rateLimit` + `inFlightReq`, limiting by client IP (default
`RemoteAddr` — Traefik is the edge, no upstream proxy, so this is
spoof-resistant; no `X-Forwarded-For` trust). Middleware names are
`inkbytes-`-prefixed so they don't collide with the other apps on the shared
Traefik.
- **Reader**: `ratelimit average=100 burst=200` (req/s/IP) + `inflightreq amount=100`.
  Generous for a human (lead images are cross-origin from outlet CDNs, so a page
  load hits this origin only ~5–15×); brutal for a flood (thousands/s).
- **Backoffice**: `ratelimit average=30 burst=60` + `inflightreq amount=40`
  (single-user admin → tighter; also caps login-POST flooding at the edge).

### Layer #3 — application throttles
- **`/api/ask`** (`Reader/apps/web/app/api/ask/route.ts`): an in-memory limiter
  runs **before** the LLM call — per-IP `8 / 60s` + a global `40 / 60s` ceiling
  (hard cap on total LLM spend even under a *distributed* flood; degraded chat
  beats a runaway bill) → `429` + `Retry-After`. State is module-level and
  relies on the Node.js runtime (pinned `export const runtime = "nodejs"`); the
  Reader self-hosts as a single long-lived `next start` process so counters are
  shared. Client IP from `X-Forwarded-For` (set by Traefik). If the Reader is
  ever scaled horizontally, move to a shared store (Redis); Traefik #2 is the
  defence-in-depth layer.
- **Backoffice login** (`routes/auth.php`): added `throttle:10,1` (10 POST/min/IP)
  on the login POST — a flood cap on top of Breeze's per-credential lockout.

## Consequences

- A single abuser is capped per-IP at both the edge and the app; the global
  `/ask` ceiling bounds worst-case LLM cost under a distributed flood.
- **Not** protected: volumetric (L3/L4) floods that saturate the droplet's
  uplink, and origin-IP-direct attacks — those need **#1 Cloudflare** (proxy +
  origin firewall lock-down) and DO network-level protection. Documented as the
  recommended next step.
- Rate-limit values are tuning knobs; watch for false `429`s in Traefik/Reader
  logs and loosen `average`/`burst`/`PER_IP_MAX` if legitimate traffic trips them.
- The Traefik middleware lives in the `do` override only — local dev (no Traefik
  labels) is unaffected.

## Alternatives considered

| Option | Why not (now) |
|---|---|
| Cloudflare proxy (#1) | Biggest anti-volumetric win, but needs a DNS migration + dashboard config (owner action) + origin firewall lock to CF IPs. Deferred, recommended next. |
| fail2ban + ufw/DO firewall (#4) | Useful for SSH + repeat offenders; deferred with #1 (firewall pairs with the CF IP allowlist). |
| Redis-backed distributed limiter | Overkill for a single Reader container; revisit only if the Reader scales out. |
| Rate-limit Curator `/ask` directly | `/ask` is internal (only the Reader reaches it); the public Reader-side limit + Traefik cover the vector. Optional defence-in-depth later. |
