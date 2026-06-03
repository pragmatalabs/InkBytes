# InkBytes — Repo Briefing (Claude Code handoff)

> *If you're a fresh Claude Code session, read this top-to-bottom before doing anything. ~3 min.*
> *Last updated: 2026-06-02*

## What this repo is

InkBytes is a paid, ad-free news reader: one elegant page per *event*, synthesized from multiple sources. The reader pays to skip the noise.

Long-term pipeline: **Messor (harvester) → Entopics (NER+topics) → Synochi (synthesis) → Unitas (clustering+QA) → Reader**.

**v0 (this week) collapses Entopics+Synochi+Unitas into a single LLM-powered service called `Curator`.** That's the active work.

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
├── Messor/                            ← STAGE 1, status: scaffolded + cleaned
│   ├── apps/scraper/                  ← Python harvester (FastAPI, newspaper3k)
│   ├── packages/inkbytes/             ← shared kernel (pydantic v1)
│   ├── docs/                          ← incl. contracts.md, ADRs
│   └── CLAUDE.md                      ← Messor-specific briefing
│
├── Curator/                           ← STAGES 2+3+4 collapsed, status: D2 done, D3 in progress
│   ├── apps/curator/                  ← Python LLM service (pydantic v2)
│   ├── docs/                          ← incl. architecture.md, ADR-0001
│   └── CLAUDE.md                      ← Curator-specific briefing ← read this if working here
│
├── Reader/                            ← v0 frontend, NOT YET SCAFFOLDED (D4)
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

✅ **Messor**: monorepo cleaned (INK-1, INK-2, INK-5, INK-11). Real harvester, JSON staging, RabbitMQ publisher, `articles-scraped` event. Sandbox-tested. Not yet deployed.

✅ **Curator scaffold (D2)**: complete and verified. `apps/curator/` runs end-to-end on a fixture against real Haiku + real OpenAI embeddings + Postgres + pgvector. ENRICH → CLUSTER works. Auto-migration on startup.

🟡 **Curator D3** (current focus): need a second fixture to trigger SYNTHESIZE (Skill 3) so we see a real one-pager in `pages` table. Then wire to actual Messor output.

🔴 **Reader (D4)**: Next.js scaffold not started. Will read from Curator's `GET /events` and `/events/{id}` endpoints.

🔴 **Deploy (D6)**: nothing on DO yet.

## Where to point pwd depending on what you're doing

| Task | `cd` into | Then run `claude` |
|---|---|---|
| Anything spanning multiple services / system docs / orchestration | `/Volumes/Pragmata/Projects/InkBytes/` | reads this file (`CLAUDE.md`) |
| Curator dev (current focus) | `/Volumes/Pragmata/Projects/InkBytes/Curator/apps/curator/` | reads `Curator/CLAUDE.md` |
| Messor dev | `/Volumes/Pragmata/Projects/InkBytes/Messor/apps/scraper/` | reads `Messor/CLAUDE.md` |
| Reader scaffold (D4) | `/Volumes/Pragmata/Projects/InkBytes/Reader/` (create it) | new |

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

1. [`docs/mvp-plan.md`](./docs/mvp-plan.md) — week-of plan, the only roadmap that matters right now
2. [`Curator/docs/architecture.md`](./Curator/docs/architecture.md) — what we just built
3. [`Curator/docs/adr/0001-curator-collapses-pipeline.md`](./Curator/docs/adr/0001-curator-collapses-pipeline.md) — why one service instead of three
4. [`Messor/docs/contracts.md`](./Messor/docs/contracts.md) — the event Curator consumes
5. [`Messor/docs/adr/0005-messor-curator-responsibility-split.md`](./Messor/docs/adr/0005-messor-curator-responsibility-split.md) — the boundary

## Open immediate todos

1. Run Curator with `fixtures/sample_article_2.json` (Reuters) to trigger SYNTHESIZE. Existing fixture 1 (BBC) is already in DB.
2. Inspect the resulting `pages` row — eyeball the headline + synthesis quality.
3. Wire Messor to actually publish `articles-scraped` to RabbitMQ; Curator consumes from broker instead of fixtures.
4. Scaffold `Reader/` (Next.js, D4).
5. `.do/app.yaml` for autodeploy (D6).
6. Commit + push: the changes in this branch span many files; the index lock issue from earlier may still need a host-side `rm -f .git/index.lock`. See `Messor/scripts/commit-v1-docs.sh` for the prepared commit sequence.

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

Six boxes from [`docs/mvp-plan.md`](./docs/mvp-plan.md) §7:

- [x] Curator runs end-to-end on real LLM (proved 2026-06-02)
- [ ] At least one outlet returned ≥ 5 articles via Messor
- [ ] First 10 hand-checked event pages in `pages` table
- [ ] Reader renders top 10 events at `localhost:3000`
- [ ] DO Droplet running docker-compose.prod.yaml at `inkbytes.app` (or alt domain)
- [ ] 24h of green scheduled cycles + first paying user invited
