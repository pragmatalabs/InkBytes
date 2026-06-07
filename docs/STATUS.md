# InkBytes — Overall Status

> *Status: v0 live on Hostinger VPS · Owner: Julian · Last updated: 2026-06-07*
> *Pipeline proven end-to-end. 413 published pages. 22 active outlets. Continuous 4×/day cycle.*

---

## TL;DR

The full v0 pipeline runs end-to-end on real infrastructure:
**Messor (harvest) → RabbitMQ → Curator (enrich + cluster + synthesize) → Reader (pages)**.

- **Reader:** https://inkbytes.galvanic.cloud
- **Backoffice:** https://admin.inkbytes.galvanic.cloud
- **Server:** Hostinger VPS `82.112.250.139` · 15 GB RAM · Docker + Traefik

---

## Live pipeline numbers (2026-06-07)

| Metric | Value |
|---|---|
| Total articles | 7,591 |
| Enriched | 7,078 (93%) |
| Events | 413 |
| Published pages | 413 |
| Active outlets | 22 of 34 |
| LLM — enrich | DeepSeek `deepseek-chat` |
| LLM — synthesize | DeepSeek `deepseek-reasoner` |
| Embeddings | Ollama `bge-m3` (1024-dim) |
| Cost projection | ~$5–10 / 1000 articles |
| Scraping schedule | 4×/day (~360 min interval) |

---

## Service state (production — Hostinger VPS)

| Service | Container | URL / Port | State |
|---|---|---|---|
| Reader (Next.js) | `inkbytes-reader` | `:18050` → `inkbytes.galvanic.cloud` | ✅ healthy |
| Backoffice (nginx+php-fpm) | `inkbytes-backoffice` | `:18051` → `admin.inkbytes.galvanic.cloud` | ✅ up |
| Curator API | `inkbytes-curator-api` | `:8060` (internal) | ✅ healthy |
| Curator Worker | `inkbytes-curator-worker` | internal | ✅ healthy |
| Messor harvester | `inkbytes-messor` | `:8050` (internal) | ✅ running |
| Postgres + pgvector | `inkbytes-postgres` | `:5432` (internal) | ✅ healthy |
| RabbitMQ | `inkbytes-rabbitmq` | `:5672` / mgmt `:15683` | ✅ healthy |
| MinIO (S3 stand-in) | `inkbytes-minio` | `:9000` / console `:9030` | ✅ healthy |
| Ollama (shared host) | `ollama` | `:11434` (host-network) | ✅ bge-m3 loaded |
| Traefik | host-network | `:80/:443` | ✅ TLS via Let's Encrypt |

### Memory limits (infra/docker-compose.prod.yml)

| Container | Limit | Typical usage |
|---|---|---|
| `inkbytes-messor` | 6 GB | 2–3 GB mid-scrape, ~150 MB idle |
| `inkbytes-curator-worker` | 1 GB | ~130 MB |
| `inkbytes-reader` | 512 MB | ~65 MB |
| `inkbytes-backoffice` | 512 MB | ~115 MB |
| `inkbytes-curator-api` | 512 MB | ~110 MB |
| `ollama` | 3 GB | ~1.6 GB (bge-m3) |

---

## Active outlets (22)

`apnews · clarin · cnbc · cnn · diariolibree · elcaribedr · elespectador · elfinancierolatam · eltiempoco · eluniversalmx · gizmodo · ground-news · infobae · lanacionar · latimes · listindiario · mileniomx · npr · semana · techcrunch · theguardian · acentodr`

### Disabled outlets (12) — reason

| Outlet | Reason |
|---|---|
| bbc | Geo-blocked on Hostinger IP; redirect loop (`Exceeded 30 redirects`) |
| aljazeera | Rate-limited; parse success dropped to 1.4% on back-to-back runs |
| bloomberg | Hard paywall — 0 articles harvested |
| wsj | Hard paywall — 0 articles harvested |
| reuters | Geo-blocked — 0 articles harvested |
| theeconomist | Hard paywall — 0 articles harvested |
| financialtimes | Soft paywall — 0 articles saved |
| wired | JS-rendered / soft paywall — 0 articles saved |
| foxbusiness | Broken newspaper3k parsing — 0.7% parse success |
| polifact | Broken parsing — 0% parse success |
| animalpolitico | Broken parsing — 0% parse success |
| eldinerodr | Broken parsing — 3.4% parse success |

---

## v0 Definition of Done

- [x] Curator runs end-to-end on real LLM
- [x] At least one outlet returned ≥ 5 articles via Messor
- [x] First event pages in `pages` table (413 multi-source pages)
- [x] Reader renders events at production URL
- [x] Server running docker-compose.prod.yaml at `inkbytes.galvanic.cloud`
- [x] Continuous 4×/day scheduled cycles with per-outlet session tracking
- [ ] 24h of green scheduled cycles + first paying user invited
- [ ] Switch to `inkbytes.news` domain (DNS A records → `82.112.250.139`)
- [ ] GitHub Actions CI/CD (secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`)

---

## Monitoring commands (from repo root)

```bash
make status           # snapshot: all containers + memory table
make watch            # live stats every 5s
make logs             # follow ALL service logs
make logs-messor      # follow Messor (scraping progress)
make logs-curator     # follow Curator worker (enrich/cluster/synth)
make logs-backoffice  # follow Backoffice (Laravel)
make health           # HTTP status of reader + admin
make shell            # SSH into server
make shell-db         # psql on production Postgres
make shell-curator    # bash in curator-api container
```

---

## Open items / next steps

### P0 — Blocking on first paying user

1. **`inkbytes.news` domain** — add A records → `82.112.250.139`; update `READER_DOMAIN`/`ADMIN_DOMAIN` in `infra/.env`; update Traefik config (`/docker/traefik/config/inkbytes.yml`).
2. **Ollama reconnect on reboot** — `docker network connect inkbytes_inkbytes-internal ollama` is currently manual after server reboot. Add a systemd unit or cron.
3. **Phase 3 / Stripe** — subscriber gating blocked on pricing decisions. See `docs/product.md`.
4. **24h green soak** — let 4 scheduled cycles complete; verify Scrape Results shows outlets at >80% parse success.

### P1 — Scraping quality

5. **RSS/Atom-first harvesting** — designed in `docs/roadmap.md`, not yet implemented. feedparser + trafilatura replaces newspaper3k homepage crawl. Expected: cycle time 28 min → 4-6 min.
6. **Per-outlet `feed_url` in DB** — `ALTER TABLE public.outlets ADD COLUMN feed_url text;` — prerequisite for RSS-first.
7. **trafilatura fallback parser** — when newspaper3k fails, try trafilatura. Better for modern JS sites.
8. **Per-outlet config** — custom headers (Referer, Accept-Language) and rate-limit delays per outlet.

### P2 — Reader

9. **Reader R4** — global perf/SEO pass. Lighthouse score, og:image, sitemap.xml.
10. **Language filter on feed** — Spanish content stays in Spanish; Reader shows language badge.

### P3 — Infrastructure

11. **GitHub Actions CI/CD** — auto-build and deploy on `git push master`. Set secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`.
12. **Curator config default** — change `embeddings_base_url` default to `http://ollama:11434/v1` (currently `localhost:11434` breaks after `migrate:fresh`).
13. **Approach B entity embeddings** — event-level pgvector for related-events at >1000 events scale.

---

## Repository

- **Canonical remote:** https://github.com/pragmatalabs/InkBytes (`master`)
- **Registry:** GitHub Container Registry `ghcr.io/pragmatalabs` (free; replaced DO registry)
- **Secrets:** never committed — set via `infra/.env` on server (see `docs/deployment-secrets.md`)
