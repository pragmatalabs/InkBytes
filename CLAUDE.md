# InkBytes — Repo Briefing (Claude Code handoff)

> *If you're a fresh Claude Code session, read this top-to-bottom before doing anything. ~3 min.*
> *Last updated: 2026-06-07*

## Single source of truth (read this first)

InkBytes docs split by layer. Don't duplicate across the boundary:

- **Engineering + current state → this repo's `docs/`.** Live status is
  [`docs/STATUS.md`](./docs/STATUS.md) (authoritative, dated). The week plan is
  [`docs/mvp-plan.md`](./docs/mvp-plan.md). Product/business framing is
  [`docs/product.md`](./docs/product.md).
- **Product / business / strategy → Notion hub**
  ([InkBytes](https://www.notion.so/373eca56ed94818da548f66ca288593a)). The Notion
  architecture/status sections *mirror* this repo — when they disagree, the repo wins.

If you only update one status, update `docs/STATUS.md`, then reconcile this file.

## What this repo is

InkBytes is a paid, ad-free news reader: one elegant page per *event*, synthesized from multiple sources. The reader pays to skip the noise.

Long-term pipeline: **Messor (harvester) → Entopics (NER+topics) → Synochi (synthesis) → Unitas (clustering+QA) → Reader**.

**v0 collapses Entopics+Synochi+Unitas into a single LLM-powered service called `Curator`.** As of 2026-06-07 the full v0 loop is **live in production on DigitalOcean** (`inkbytes.org`): 413 published pages, 22 active outlets, continuous 4×/day harvest cycle. Remaining: 24h green soak + first paying user (D7).

## Monorepo map

```
InkBytes/                              ← repo root
├── docs/                              ← system-wide docs
│   ├── README.md
│   └── mvp-plan.md                    ← THE plan for this week, read this first
│
├── orchestrator/                      ← parent-level dev/prod compose + scripts
│   ├── docker-compose.dev.yaml        ← Postgres + RabbitMQ + MinIO
│   └── scripts/up.sh, down.sh
│
├── Messor/                            ← STAGE 1, status: harvester live (publishes to RabbitMQ)
│   ├── apps/scraper/                  ← Python harvester (FastAPI, newspaper3k)
│   ├── packages/inkbytes/             ← shared kernel (pydantic v1)
│   ├── docs/                          ← incl. contracts.md, ADRs
│   └── CLAUDE.md                      ← Messor-specific briefing
│
├── Curator/                           ← STAGES 2+3+4 collapsed, status: end-to-end proven (29 pages)
│   ├── apps/curator/                  ← Python LLM service (pydantic v2)
│   ├── docs/                          ← incl. architecture.md, ADR-0001
│   └── CLAUDE.md                      ← Curator-specific briefing ← read this if working here
│
├── Reader/                            ← v0 frontend, status: Next.js scaffolded, runs at :3000
│   └── apps/web/                      ← Next.js public reader (reads Curator pages)
│
├── Entopics/  Synochi/  Unitas/       ← legacy folders, PARKED for v0
└── (other folders are legacy / pre-MVP — ignore unless asked)
```

## Locked decisions (2026-06-02)

| Decision | Choice |
|---|---|
| LLM (enrich + synthesize) | **Anthropic Claude Haiku 4.5** |
| Embeddings | **Local Ollama `bge-m3` (1024-dim, multilingual)** — Curator ADR-0003; OpenAI `text-embedding-3-small` is the fallback provider |
| Local model runtime | **Ollama** — deployed service (dev `full` profile + prod compose); serves bge-m3 over an OpenAI-compatible `/v1` endpoint |
| Outlet vertical | LATAM bilingual (DR/MX/CO/AR) + global EN business/tech |
| Deploy target | Single DigitalOcean Droplet |
| Database | Postgres + pgvector |
| Event bus | RabbitMQ |
| Object store (prod) | DigitalOcean Spaces (S3) |
| Object store (dev) | MinIO via docker-compose |
| Reader exchange name | renamed `hermes` → `messor.logs` (ADR-0004) |
| Pydantic | v1 in Messor (legacy), v2 in Curator (new) — boundary is RabbitMQ JSON |

## State of the world right now

**Live status lives in [`docs/STATUS.md`](./docs/STATUS.md)** — keep the numbers there, not here. Summary as of 2026-06-02 evening:

✅ **Messor**: harvester live; publishes per-article `event.article.scraped` on the `messor` exchange. 3 outlets exercised (CNN/NPR/AP, ~319 articles). LATAM/ES outlets configured but not yet harvested. Not yet deployed.

✅ **Curator**: consumes from RabbitMQ; ENRICH → CLUSTER → SYNTHESIZE all live on real Haiku 4.5 + OpenAI embeddings + Postgres/pgvector. DB shows 309 enriched articles, 220 events, **29 published pages** (7 three-source, 22 two-source).

✅ **Reader (D4/D5)**: Next.js `apps/web` running in production at `inkbytes.org`. PWA manifest, bottom nav (4 tabs), share button on event pages. Lead images on cards and event hero.

✅ **Deploy (D6)**: DigitalOcean Droplet `67.205.136.61` running `docker-compose.prod.yml` at `inkbytes.org`. **Hostinger is retired — DO is the sole deploy target.**

🟡 **Soak (D7)**: 4×/day cycle is live; needs 24h of green cycles + first paying user invited.

## Where to point pwd depending on what you're doing

| Task | `cd` into | Then run `claude` |
|---|---|---|
| Anything spanning multiple services / system docs / orchestration | `/Volumes/Pragmata/Projects/InkBytes/` | reads this file (`CLAUDE.md`) |
| Curator dev | `/Volumes/Pragmata/Projects/InkBytes/Curator/apps/curator/` | reads `Curator/CLAUDE.md` |
| Messor dev | `/Volumes/Pragmata/Projects/InkBytes/Messor/apps/scraper/` | reads `Messor/CLAUDE.md` |
| Reader dev (D4, current focus) | `/Volumes/Pragmata/Projects/InkBytes/Reader/apps/web/` | reads `Reader/apps/web/CLAUDE.md` |

## Required env vars (host shell, never commit)

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
export OPENAI_API_KEY='sk-...'
# Postgres + RabbitMQ + MinIO defaults are already in env.local.yaml
```

If you're picking up cold and need to set these, add them to `~/.zshrc` (macOS default) or use 1Password CLI / Doppler.

## Bring everything up (one shot)

```bash
cd /Volumes/Pragmata/Projects/InkBytes
bash orchestrator/scripts/up.sh
# → Postgres :5432, RabbitMQ :5672 (UI :15672), MinIO :9000 (console :9001)
```

Tear down:

```bash
bash orchestrator/scripts/down.sh         # keep volumes
bash orchestrator/scripts/down.sh --nuke  # delete volumes too
```

## Read order if you have 10 minutes

1. [`docs/STATUS.md`](./docs/STATUS.md) — live end-to-end state, the current truth
2. [`docs/mvp-plan.md`](./docs/mvp-plan.md) — week-of plan / roadmap
3. [`docs/product.md`](./docs/product.md) — mission, audience, differentiation (business layer)
4. [`Curator/docs/architecture.md`](./Curator/docs/architecture.md) — what we built
5. [`Curator/docs/adr/0001-curator-collapses-pipeline.md`](./Curator/docs/adr/0001-curator-collapses-pipeline.md) — why one service instead of three
6. [`Messor/docs/contracts.md`](./Messor/docs/contracts.md) — the event Curator consumes
7. [`Messor/docs/adr/0005-messor-curator-responsibility-split.md`](./Messor/docs/adr/0005-messor-curator-responsibility-split.md) — the boundary

## Open immediate todos

(see [`docs/STATUS.md`](./docs/STATUS.md) §"Open items" for the live list)

1. **Soak (D7):** let 4 scheduled cycles complete; verify outlets at >80% parse success; invite first paying user.
2. **`inkbytes.news` domain:** add A records → `67.205.136.61`; update `READER_DOMAIN`/`ADMIN_DOMAIN` on DO server.
3. **PNG app icons:** generate `/public/icon-192.png` and `/public/icon-512.png` from `icon.svg` for Android PWA install banner.
4. **Outlet coverage:** harvest the remaining LATAM/ES outlets; RSS/Atom-first harvesting in roadmap.
5. **Cleanup debt:** retire the legacy Messor GitLab remote; review `Trashx/` repos before deleting.

## Conventions to keep using

- **Prompts as `.md` files** in `Curator/apps/curator/prompts/` — diffable, reviewable. See `Curator/docs/prompts.md` for the versioning policy.
- **Pydantic v2 in Curator** (don't downgrade). Pydantic v1 in Messor (don't upgrade until INK-Sprint-2).
- **ADRs** for any non-trivial decision. Sequential numbering per service.
- **Status banner** at the top of every doc: `> *Status: vN · Owner: ... · Last updated: YYYY-MM-DD*`.
- **`__SET_VIA_ENV__`** placeholders in committed YAML; real secrets come from env vars.
- **Never paste API keys in chat.** Set via shell. See `Messor/docs/security.md`.

## Anti-patterns to avoid

- Re-adding `topics_extracted` / `clusters_path` / `openai:` config to Messor — that's Curator's territory (ADR-0005).
- Calling `newspaper3k.Article.nlp()` in Messor — heuristic NLP belongs to Curator (ADR-0005).
- Mixing pydantic v1 imports into Curator code, or v2 imports into Messor code.
- Using a multi-agent framework (LangGraph / CrewAI / AutoGen) for Curator's three skills. ADR-0001 §"Alternatives considered" rejected it explicitly.
- Adding new schemas to the `inkbytes` shared package without a version bump.
- Writing prompts as inline Python strings instead of `.md` files in `prompts/`.
- **`export const revalidate = N` on Reader pages that call internal Docker services** (`inkbytes-curator-api` etc.). ISR pre-renders during `docker build` when the internal hostname doesn't exist → bakes the error state permanently. Use `export const dynamic = "force-dynamic"` instead (ADR-R-0005).
- **Accessing asyncpg JSONB columns without `_decode_json_col()`**. asyncpg returns plain `JSONB` columns as Python strings without explicit codec registration. Every JSONB column in the `/events/{id}` response must pass through `_decode_json_col()`. In the Reader, guard defensively: `Array.isArray(v) ? v : JSON.parse(v)` (ADR-R-0004).
- **`IllustrateSkill` without a concurrency gate**. Each run opens 2 Chromium instances (~400 MB). During batch synthesis N events fire N concurrent tasks → OOM. Always wrap the call in `_illustrate_sem` (`Semaphore(1)`) (ADR-0011).
- **Chromium in Docker without `seccomp:unconfined`**. Docker's default seccomp profile blocks the `clone()` flags Chromium needs → `SIGTRAP` crash on DO even with `--no-sandbox`. `inkbytes-curator-worker` in `infra/docker-compose.do.yml` must carry `shm_size: '256m'` and `security_opt: [seccomp:unconfined]` (ADR-0011).
- **Scrapling `StealthyFetcher`/`DynamicFetcher` in Docker containers**. Both wrappers inject `channel='chromium'` into Playwright's browser launch options. On Docker/Linux, `channel='chromium'` triggers a channel-based binary lookup that SIGTRAP-crashes even with `seccomp:unconfined`. Use `patchright.async_api.async_playwright` / `playwright.async_api.async_playwright` directly with no `channel` argument (ADR-0011).

## What "done" looks like for v0 (Sunday 2026-06-07)

Six boxes from [`docs/mvp-plan.md`](./docs/mvp-plan.md) §7 (mirror of `docs/STATUS.md`):

- [x] Curator runs end-to-end on real LLM
- [x] At least one outlet returned ≥ 5 articles via Messor (22 outlets, 7,591 articles)
- [x] First event pages in `pages` table (413 published pages)
- [x] Reader renders events at `inkbytes.org` (production)
- [x] DO Droplet running docker-compose.prod.yaml at `inkbytes.org`
- [x] IllustrateSkill Phase 2 — media rail in production (Scrapling, Patchright, ADR-0011)
- [x] Reader v2 — force graph on mobile, media drawer in action bar, brand logo (ADR-R-0003/0004/0005)
- [ ] 24h of green scheduled cycles + first paying user invited
