# ADR-R-0012 — PWA push notifications: "Daily Outlook ready"

> *Status: v1 · **DEPLOYED + verified live 2026-07-12** · Owner: Julian · Date: 2026-07-12*

## Context

Julian: let readers opt in to a notification when the day's Outlook columns are
published. The Reader is an installable PWA (manifest, `display: standalone`) but
had **no service worker and no push**.

The constraint that shapes the whole design: **on iOS, Web Push only works inside
an installed PWA** (iOS 16.4+) — `PushManager` doesn't exist in a Safari tab.
Permission must also be requested from a user gesture.

## Decision

**Curator owns push; the Reader drives the browser subscription; the Editorial
cron triggers the daily send.**

1. **Opt-in, capability-gated** (`components/notify-toggle.tsx`, on `/outlook`):
   keys off `serviceWorker`/`PushManager`/`Notification` presence — capable →
   the toggle; not capable (iOS tab) → "install to enable"; denied → "blocked
   in settings". `Notification.requestPermission()` runs on the tap, never load.
2. **Service worker** (`public/sw.js`): `push` + `notificationclick` **only** —
   deliberately no fetch/offline caching (the reader is `force-dynamic`,
   ADR-R-0005; a caching SW would fight it). Focuses an open tab or opens `/outlook`.
3. **Curator = push authority**: migration `022_push_subscriptions`;
   `services/push_service.py` (pywebpush, VAPID from env, no-op when unconfigured
   so the API stays up without keys); endpoints `GET /push/vapid`,
   `POST /push/subscribe`, `POST /push/unsubscribe`, and `POST /push/broadcast-outlook`
   (token-guarded, `BackgroundTasks` fan-out, prunes 404/410 dead subs).
4. **Reader proxy** (`app/api/push/route.ts`): the browser can't reach the
   internal Curator host, so subscribe/unsubscribe/vapid go through this
   server-side route. Curator-api has **no public Traefik route**, so
   `/push/broadcast-outlook` is only reachable inside the docker network —
   defence in depth on top of the token.
5. **Trigger**: `Editorial.generate_all()` pings `/push/broadcast-outlook` after
   a real batch (best-effort, token-guarded, `try/except` so push never affects
   generation). The daily cron therefore: generate → notify.
6. **VAPID + `PUSH_TRIGGER_SECRET`** live in `infra/.env` (never committed),
   passed to curator-api + the editorial run via compose/`run-editorial.sh`.

## Alternatives considered

| Option | Rejected because |
|---|---|
| next-pwa / Serwist (full offline SW) | We only need push; a caching SW conflicts with force-dynamic. A 40-line hand SW is clearer. |
| Editorial sends the push itself | Would duplicate VAPID + the subscriptions store across two services. Curator owns it; Editorial just triggers. |
| Show the toggle everywhere | On iOS it can't work in a tab; capability-gating avoids a dead button. |
| Store subscriptions in localStorage | Push subscriptions must live server-side to send to; localStorage is the *saved-columns* store, a different thing. |

## Consequences

- One opt-in, one send/user/day (latency-tolerant, cheap). Volume is trivial.
- Foundation for later triggers (breaking news, saved-topic updates) — add a
  `topics` value + a trigger; the store, SW, and sender are reused.
- iOS users must **install** the PWA first; Android/desktop Chrome work in-tab too.
- Not headless-testable end to end (real delivery needs a device granting
  permission); every server + client plumbing layer was verified on prod
  (subscribe→store→unsubscribe through the public proxy, token broadcast + prune,
  vapid served, sw.js served, migration applied).

## Bug caught in review

FastAPI treated the `/push/subscribe` body as a **query** param (422 "body
required") because `PushSubBody` was defined *inside* `build_app()` — a
locally-scoped Pydantic model isn't detected as a body model. Fixed by hoisting
the request models to module scope. (lessons-learned 2026-07-12)
