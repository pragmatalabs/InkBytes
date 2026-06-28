# InkBytes — Visitor & Content Analytics (self-hosted Umami)

> *Status: v1 · Owner: Julian · Added 2026-06-28*

## Why Umami, self-hosted

InkBytes is **ad-free and privacy-positioned**, the audience is **LATAM + Europe
(GDPR)**, and `docs/legal-risk.md` flags EU compliance. So analytics must be
**cookieless / consent-banner-free** and ideally keep visitor data on our own
infra. Chosen: **Umami** (open-source, cookieless, GDPR-friendly), **self-hosted**
on the droplet, storing data in a **separate `umami` database on the existing
Postgres** — so no visitor data leaves the box, no third party, no recurring fee.
(Plausible self-host was rejected: it needs ClickHouse — too heavy for the shared
7.8 GB droplet. Google Analytics was rejected: cookies + consent banner + ad-tech,
against the brand.)

## Architecture

```
visitor browser ──script.js──▶ analytics.inkbytes.org (Traefik → inkbytes-umami :3000)
                 ──/api/send──▶            │
                                           ▼
                              Postgres `umami` DB (same inkbytes-postgres instance)
```
- Service `inkbytes-umami` (`infra/docker-compose.prod.yml`), Traefik labels in
  `docker-compose.do.yml` → `${ANALYTICS_DOMAIN:-analytics.inkbytes.org}`.
- Reader loads the script via `components/analytics.tsx` (server component, reads
  `UMAMI_SRC` + `UMAMI_WEBSITE_ID` from runtime env → no rebuild to set the id).
- Content engagement via `components/read-tracker.tsx` on the event page.

## Custom events (content engagement)

| Event | When | Data |
|---|---|---|
| `event-read` | event page opened | `event_id`, `category`, `language` |
| `read-depth` | scroll passes 25/50/75/100% | `event_id`, `depth` |

Pageviews/visitors/referrers/geo/devices come for free from the base script.

## One-time setup (the manual steps)

1. **DNS** — add an A record `analytics.inkbytes.org → 67.205.136.61` (mirrors
   `admin.inkbytes.org`). Traefik auto-issues the LE cert once it resolves.
2. **Secret + DB** (on the droplet):
   ```bash
   cd /opt/inkbytes
   echo "UMAMI_APP_SECRET=$(openssl rand -hex 32)" >> infra/.env
   docker exec inkbytes-postgres psql -U "$POSTGRES_USER" -c 'CREATE DATABASE umami'
   ```
3. **Deploy umami** (surgical — does not touch other services):
   ```bash
   set -a; source infra/.env; set +a
   docker compose -f infra/docker-compose.prod.yml -f infra/docker-compose.do.yml \
     up -d --no-deps inkbytes-umami       # runs its own Prisma migrations on boot
   ```
4. **First-run** — open `https://analytics.inkbytes.org`, log in `admin` / `umami`,
   **change the password immediately**. Add a website → Name `InkBytes`, Domain
   `inkbytes.org`. Copy its **Website ID** (UUID).
5. **Wire the Reader** — set the id + src in `infra/.env`, then recreate the reader:
   ```bash
   printf 'UMAMI_SRC=https://analytics.inkbytes.org/script.js\nUMAMI_WEBSITE_ID=<uuid>\n' >> infra/.env
   set -a; source infra/.env; set +a
   docker compose -f infra/docker-compose.prod.yml -f infra/docker-compose.do.yml \
     up -d --no-deps inkbytes-reader
   ```
6. Verify: visit inkbytes.org, then the Umami dashboard shows the pageview in
   real-time; open an event and confirm `event-read` / `read-depth` events appear.

## Notes

- Reusing the prod Postgres is fine at current (pre-launch) traffic — one insert
  per pageview/event. If traffic grows, split Umami onto its own Postgres.
- The script is cross-origin from `analytics.inkbytes.org`; Umami serves it with
  the right CORS for `/api/send`. Self-hosted on our own subdomain → less likely
  blocked than a known third-party tracker, though some adblockers may still skip
  it (the tracker no-ops cleanly when that happens).
