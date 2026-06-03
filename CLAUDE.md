# InkBytes — Repo Briefing (Claude Code handoff)

> *If you're a fresh Claude Code session, read this top-to-bottom before doing anything. ~3 min.*
> *Last updated: 2026-06-02 (evening — pipeline proven end-to-end)*

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

**v0 collapses Entopics+Synochi+Unitas into a single LLM-powered service called `Curator`.** As of 2026-06-02 the full v0 loop (Messor → RabbitMQ → Curator → Reader) is **proven end-to-end on real infra**: a 3-outlet harvest produced 29 multi-source event pages rendering in the Reader. Remaining for v0: DigitalOcean deploy (D6) + 24h soak / first paying user (D7).

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
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
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

✅ **Reader (D4)**: Next.js `apps/web` scaffolded and running at `localhost:3000`, rendering the published pages.

🔴 **Deploy (D6)**: nothing on DigitalOcean yet — needs `.do/app.yaml` / prod compose.

🟡 **Soak (D7)**: pages so far came from manual runs + one recluster; wire `--schedule` for continuous cycles, then invite first paying user.

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

1. **Deploy (D6):** author `.do/app.yaml` / prod compose; stand up the DO Droplet at `inkbytes.app`.
2. **Continuous cycle (D7):** run Messor `--schedule` so pages come from real 60-min cycles, not manual runs + recluster.
3. **Outlet coverage:** harvest the LATAM/ES outlets in `outlets.json` (only CNN/NPR/AP exercised so far).
4. **Reader polish (D5):** typography, mobile, freshness ribbon, evidence rail; minimal `/admin`.
5. **Cleanup debt:** retire the legacy Messor GitLab remote (diverged from GitHub monorepo); review `Trashx/` repos with unpushed work before deleting.

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

## What "done" looks like for v0 (Sunday 2026-06-07)

Six boxes from [`docs/mvp-plan.md`](./docs/mvp-plan.md) §7 (mirror of `docs/STATUS.md`):

- [x] Curator runs end-to-end on real LLM (proved 2026-06-02)
- [x] At least one outlet returned ≥ 5 articles via Messor (3 outlets, ~319 articles)
- [x] First event pages in `pages` table (29 multi-source pages, hand-checkable)
- [x] Reader renders events at `localhost:3000`
- [ ] DO Droplet running docker-compose.prod.yaml at `inkbytes.app` (or alt domain)
- [ ] 24h of green scheduled cycles + first paying user invited
