# Reader traffic analytics — Backoffice "Reader Hits" (design note, build later)

> *Status: v0 design note · Owner: Julian · Last updated: 2026-06-11 · NOT built*

Future feature requested 2026-06-11: surface **per-request hits to the Reader**
(`inkbytes.org`) in the Backoffice, so we can see traffic — which event pages
get read, how often, from where — without bolting on a third-party analytics
SaaS.

This is a design stub to capture the idea and its constraints. No code yet.

## ⚠️ Privacy first — IP is PII

A raw visitor IP is personal data under GDPR and most LATAM data-protection
laws (e.g. Brazil LGPD, the regions InkBytes targets). For a *paid* product
this matters legally and reputationally. The design must:

- **Not store raw IPs long-term.** Store a salted hash (`sha256(ip + daily_salt)`)
  for unique-visitor counting, or truncate to /24 (v4) / /48 (v6). Rotate the
  salt daily so hashes can't be correlated across days into a tracking profile.
- **Derive, don't retain.** Keep the *derived* dimensions we actually want
  (country/region via GeoIP, event_id, timestamp bucket) and drop the IP.
- **Honor DNT / cookieless.** This is server-side request logging, not a
  browser tracker — no cookies, no consent banner needed *if* we never persist
  raw IPs. The moment we'd store raw IPs, a consent/privacy-policy update is
  required.

## What to capture per hit

| Field | Notes |
|---|---|
| `event_id` | which page (null for home/feed/search) |
| `path` | normalized route |
| `country` / `region` | GeoIP lookup, raw IP discarded immediately after |
| `ip_hash` | salted daily hash — unique-visitor counting only |
| `referer` | domain only (strip query) |
| `ua_class` | bucketed (mobile / desktop / bot), not the raw UA string |
| `ts` | truncated to the hour for aggregation |

## Architecture options (decide at build time)

1. **Reader middleware → RabbitMQ → Curator → Postgres.** Next.js middleware
   (or an API route) emits a `reader.hit.v1` event on the existing bus;
   Curator (or a tiny consumer) writes aggregates to a `reader_hits` table the
   Backoffice reads. Fits the existing event-driven shape; async, never blocks
   the page render. **Leading candidate.**
2. **Traefik access logs → parser.** Traefik already terminates TLS for the
   Reader; ship its access log to a parser that aggregates into Postgres. Zero
   Reader code, but couples us to Traefik log format and loses `event_id`
   semantics (only sees the URL path).
3. **Postgres direct from a Next.js route handler.** Simplest, but adds a DB
   write to the request path and a Reader→Postgres dependency the Reader
   doesn't currently have. Rejected unless batched.

Aggregate, don't log-per-row at scale: roll up to hourly `(event_id, country,
hour)` counts so the table stays small and queries are cheap.

## Backoffice surface (Laravel, `Messor/apps/platform`)

A "Reader Traffic" page: top events by hits (today / 7d / 30d), hits by
country, hits over time. Reads the aggregate table via the Curator API or a
direct read-only query, same pattern as the existing Scrape Results page.

## Open decisions for build time

- Retention window for aggregates (90d? 1y?).
- Bot filtering — exclude known crawlers from "reads" or show separately.
- Whether to tie hits to authenticated subscribers (post-Stripe) for
  per-user reading history — a bigger, separate privacy conversation.
- GeoIP source (MaxMind GeoLite2 free DB vs a paid API).

## Why not just Plausible / Umami / GA?

Worth reconsidering at build time: a self-hosted Plausible/Umami instance is
privacy-friendly, cookieless, and free of build effort — but it lives outside
the Backoffice (separate dashboard) and can't natively join hits to our
`events`/`pages` semantics. The event-bus option above keeps everything in one
admin surface and one data model. Decide based on how much the Backoffice
integration is worth vs. the maintenance of a custom pipeline.
