# InkBytes — One-Week MVP Plan

> *Status: Proposal · Owner: Julián de la Rosa · Drafted: 2026-06-02*
> *Target: Ship a paying-customer-ready v0 by Sunday 2026-06-07.*

## 0. The principle for this week

> *Compress the pipeline. Defer everything that doesn't appear on the
> reader's screen.*

The 4-stage architecture (Messor → Entopics → Synochi → Unitas) is the
*long-term* shape. For the **first paying user**, we collapse the three
middle stages into a single LLM-powered service and skip everything that
doesn't move the needle on "user opens a one-pager and reads it."

If you can't see it on the reader, it's not in v0.

## 1. What we're shipping

> A paid, ad-free reader where each newsworthy *event* is a single
> elegant page — multi-source, with entity context and source diversity
> — refreshed every hour.

Concretely, the v0 demo loop:

1. Subscriber opens `inkbytes.app`.
2. Sees today's top ~20 events, ordered by freshness × source-count.
3. Clicks one → reads a one-pager: headline, 200-word synthesis, entity
   chips, source rail with quoted snippets, freshness timestamp.
4. Closes the tab. Comes back tomorrow. Same.

That's it for v0. No comments, no profiles, no saves, no notifications,
no app, no API.

## 2. The honest v0 architecture

```text
   Outlet sources (RSS, HTML)
            │
            ▼
   ┌────────────────────┐   apps/scraper            (Python, exists)
   │      MESSOR        │   schedule → fetch → dedup
   │   the harvester    │   writes JSON + RabbitMQ event + DO Spaces
   └─────────┬──────────┘
             │ event "articles-scraped" + S3 object key
             ▼
   ┌────────────────────┐   apps/curator            (Python, NEW)
   │     CURATOR        │   LLM-powered, single-service collapse of
   │  (E+S+U in one)    │   Entopics + Synochi + Unitas for v0:
   │                    │   1. enrich article (entities, topic, lang)
   │                    │   2. embed → ANN / cosine cluster
   │                    │   3. when cluster ≥ 2 sources, synthesize page
   │                    │   4. persist to Postgres
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐   apps/web                (Next.js, NEW)
   │      READER        │   Public list + /event/[id] page
   │   (winston-r)      │   Single shared password gate for v0
   └────────────────────┘

   Datastores (shared):
     - Postgres (managed DO)   — system of record: events, articles, entities, users
     - DO Spaces (S3)          — raw + staged artifacts
     - RabbitMQ                — events between Messor and Curator
```

Three runnable services. Two datastores. One MQ. **That's the whole v0.**

## 3. Repository / monorepo layout

Honoring "each layer = its own monorepo," but with the v0 collapse:

```text
/Volumes/Pragmata/Projects/InkBytes/                  ← parent (GitHub: pragmatalabs/InkBytes)
├── docs/                                             ← system-wide docs (THIS doc lives here)
│   ├── README.md
│   ├── mvp-plan.md                                  ← this file
│   └── architecture.md
│
├── orchestrator/                                     ← parent-level dev/prod compose + scripts
│   ├── docker-compose.dev.yaml                       ← all services up locally
│   ├── docker-compose.prod.yaml                      ← prod overrides
│   └── scripts/up.sh, down.sh, reset.sh
│
├── Messor/                                           ← STAGE 1 monorepo (exists, polished)
│   ├── apps/scraper/        Python harvester        ✅ done
│   ├── apps/platform/       Laravel (deferred v0)   🟡 v1+
│   ├── packages/inkbytes/   Shared kernel           ✅ done
│   └── docs/, infra/, scripts/
│
├── Curator/                                          ← NEW monorepo (collapses E + S + U)
│   ├── apps/curator/        Python LLM service
│   ├── packages/contracts/  Shared schemas (event, article, page)
│   └── docs/, infra/
│
├── Reader/                                           ← NEW monorepo (UI/UX)
│   ├── apps/web/            Next.js public reader
│   ├── apps/admin/          Next.js admin (events, outlets, force-rerun)
│   ├── packages/ui/         Shared design system (Tailwind tokens)
│   └── docs/, infra/
│
├── Entopics/                                         ← exists; PARKED in v0
├── Synochi/                                          ← exists; PARKED in v0
├── Unitas/                                           ← exists; PARKED in v0
└── (everything else from the existing repo)         ← legacy, frozen
```

**Why park Entopics/Synochi/Unitas?** They exist as historical Python
work but each is half-finished. Building three production services in
five days is not happening. The `Curator` service replaces all three
with one LLM call per article + one LLM call per event cluster.

**Post-MVP migration path:** when Curator starts to feel constrained
(volume, latency, quality), split it back into its three stages —
Entopics for the NLP pre-processing, Synochi for cross-entity
synthesis, Unitas for clustering at scale. The contract between Messor
and the curation layer stays the same RabbitMQ event, so the swap is
non-breaking.

## 4. LLM compression — what each stage becomes

| Original stage | What it did | v0 replacement (in Curator) |
|---|---|---|
| **Entopics** | Topic modeling, NER, sentiment, factuality, entity linking | One Haiku/Flash call per article → JSON: `{entities[], topic, lang, sentiment, factuality_score, summary_50w}` |
| **Synochi** | Entity-relation synthesis, multi-source enhancement | When cluster ≥ 2 sources, one Haiku call → `{headline, synthesis_200w, evidence_rail[]}` |
| **Unitas** | Clustering + similarity + QA + persist | `text-embedding-3-small` → cosine similarity → group articles with ≥ 0.78 sim and overlapping entities. Persist to Postgres. |

**Token budget per pipeline run** (rough):

- Enrich one article (1k tokens in / 200 out): ~$0.0003 with Haiku, ~$0.0001 with Gemini Flash, ~free with Groq Llama-3.3.
- Synthesize one event from 4 articles (4k in / 400 out): ~$0.002 with Haiku.

At 5,000 articles/day producing ~500 events/day: ~**$2.50/day in LLM**.

## 5. Agentic AI design — three roles, one service

The Curator service runs a single agent loop with three "skills." All
three live in the same Python process for v0; they become independent
services in v1 if needed.

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Curator Agent (Python)                       │
│                                                                 │
│  consumes RabbitMQ event 'articles-scraped'                     │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────┐                                       │
│  │  Skill 1: ENRICH    │  LLM-powered                          │
│  │  - extract entities │  prompt: structured-extract-v1        │
│  │  - classify topic   │  model: configurable (Haiku/Flash)    │
│  │  - 50-word summary  │  output: validated JSON               │
│  └─────────┬───────────┘                                       │
│            │ enriched article                                  │
│            ▼                                                   │
│  ┌─────────────────────┐                                       │
│  │  Skill 2: CLUSTER   │  embedding + math                     │
│  │  - embed article    │  text-embedding-3-small  ($0.02/1M)   │
│  │  - find neighbours  │  cosine sim ≥ 0.78 + entity overlap   │
│  │  - assign event_id  │  pgvector index in Postgres           │
│  └─────────┬───────────┘                                       │
│            │ cluster identified                                │
│            ▼                                                   │
│  ┌─────────────────────┐                                       │
│  │  Skill 3: SYNTHESIZE│  LLM-powered                          │
│  │  - read all sources │  prompt: synthesize-event-v1          │
│  │  - write headline   │  fact-check: same model, second pass  │
│  │  - write 200-w body │  evidence-rail: pulled from source    │
│  │  - emit one-pager   │  output: validated JSON for Reader    │
│  └─────────────────────┘                                       │
│                                                                │
│  observability: every LLM call logged with prompt+response+cost │
└─────────────────────────────────────────────────────────────────┘
```

**Why not a multi-agent orchestrator framework** (LangGraph, CrewAI,
AutoGen) **for v0?** Because it's three sequential function calls. A
"framework" buys nothing here and adds two weeks of learning curve.
Plain Python + a thin LLM client wrapper.

**Tooling:** `instructor` (structured outputs) + `httpx` + `pgvector` +
`tenacity` (retries) + the existing `pika` for RabbitMQ. ~~300 LOC.

## 6. LLM provider choice — recommendation

| Provider | Model | $/1M in | $/1M out | Latency | Quality (news) | v0 fit |
|---|---|---|---|---|---|---|
| **Anthropic** | Claude Haiku 4.5 | $1.00 | $5.00 | ~1s | Excellent | ⭐ Recommended |
| Google | Gemini 2.0 Flash | $0.10 | $0.40 | <1s | Very good | Backup |
| OpenAI | gpt-4o-mini | $0.15 | $0.60 | ~1s | Very good | Backup |
| Groq | Llama-3.3-70b | ~free | ~free | <500ms | Good | For high-volume tasks |

**Recommendation:** Haiku 4.5 for both ENRICH and SYNTHESIZE skills.
The 5×–10× cost vs. Flash is worth the quality bump on synthesis (the
piece the reader actually sees). If costs become real (>$50/day),
demote ENRICH to Flash or Llama-3.3 and keep SYNTHESIZE on Haiku.

Embeddings: `text-embedding-3-small` (OpenAI) or `voyage-3-lite` (cheap
+ good for clustering). Both ~$0.02/1M tokens — negligible.

## 7. Day-by-day execution (T-5 → T-0)

> Day 1 = today. Day 7 = ship Sunday night.

| Day | Owner | Deliverable | Done-when |
|---|---|---|---|
| **D1 — Today** | Julián | Decisions locked: LLM provider, brand name, primary outlet vertical. Parent docs/ + orchestrator/ scaffolded. Messor commits pushed. | Notion + repo updated. Provider API key in 1Password. |
| **D2** | Pipeline | Curator scaffold: Python service with skills 1+2 stubbed. RabbitMQ consumer. Postgres schema (articles, events, sources). Local docker-compose up brings up Messor + Curator + Postgres + RabbitMQ. | Curator consumes one event from Messor and writes an enriched article row. |
| **D3** | Pipeline | Skill 3 (synthesize) live. End-to-end: scrape → enrich → cluster → synthesize → DB row in `events`. Manual review of 10 generated pages. | First 10 hand-checked event pages exist in DB. |
| **D4** | UI | Next.js `apps/web` scaffold. Pages: `/`, `/event/[id]`, `/about`. Tailwind, no auth, single shared password (env var). Pulls from Postgres via REST or Server Components. | Reader renders top 10 events from local DB. |
| **D5** | UI + Pipeline | Polish: typography, mobile, freshness ribbon, evidence rail. Admin minimal page (`/admin`) listing outlets + manual rerun button. | Reader looks ship-able on mobile. |
| **D6** | Infra | Deploy: DO Droplet (or App Platform) running docker-compose.prod.yaml. Domain `inkbytes.app` SSL via Let's Encrypt. CloudAMQP free tier for RabbitMQ. DO Managed Postgres. | URL is live and returns a real event page. |
| **D7** | All | Soak: scheduled scraping runs every 60 min for 24h. Manual QA of 20 random events. First paying customer invited. | 24h of green cycles + customer logged in once. |

**Buffer:** D8 (Monday) reserved for the inevitable D6 surprise.

## 8. Cost model (v0, monthly)

| Item | Where | Estimate |
|---|---|---|
| DO Droplet (basic-2gb, Messor + Curator + nginx) | DO | $24 |
| DO Managed Postgres (db-s-1vcpu-1gb + pgvector) | DO | $15 |
| DO Spaces (250 GB) | DO | $5 |
| CloudAMQP (Little Lemur free) or DO Managed RabbitMQ | external | $0–$19 |
| LLM calls (5k articles/day, ~500 events/day) | Anthropic | $75 |
| Embeddings | OpenAI | $5 |
| Vercel (Reader UI free tier) or DO | Vercel | $0–$20 |
| Domain + SSL | namecheap | $1 |
| Sentry / Better Stack free tier | external | $0 |
| **Total** | | **~$125 / month** |

At 100 paying users × $9/mo = $900 revenue → ~85% gross margin. Below
30 users it's a personal-project subsidy; above 50 it pays for itself.

## 9. Pricing & gating (v0)

- **Free:** see headlines + first 100 words.
- **Paid:** $9/month → full synthesis + evidence rail + entity links.
- **Auth:** Magic-link email via Resend or basic email/password. Stripe
  Checkout for billing. Both deferred from D5; v0 ships with a single
  shared password (gated demo for invited users only).

## 10. Out of scope for v0 (be ruthless)

- Mobile app — web works on phones.
- User accounts + saved lists.
- Notifications / email digest.
- Comments / community.
- Multi-language UI (content can be multi-lang already).
- RSS export, public API.
- Source intake form for editors.
- Outlet trust scoring.
- Real-time updates (15-min cycle is fine).
- A/B testing infrastructure.
- SEO beyond basic meta tags.
- Analytics beyond Plausible self-host.

Each of these is a v1+ milestone. The temptation to do any of them
this week is the single biggest risk.

## 11. Decisions locked (2026-06-02)

1. **LLM provider**: **Anthropic Claude Haiku 4.5** for both ENRICH and
   SYNTHESIZE skills. One vendor, one bill, one prompt style. If costs
   pass $100/day, demote ENRICH to Gemini Flash.
2. **Outlet vertical**: **LATAM bilingual** — Dominican Republic +
   Mexico + Colombia + Argentina Spanish-language outlets plus the
   existing global English business/tech set. This is the underserved
   wedge.
3. **Deploy target**: **Single DigitalOcean Droplet** running
   `docker-compose.prod.yaml`. Full control, ~$24/mo, fastest iteration.

Still open (decide before D6):

- Domain name — `inkbytes.app` or alternative; buy today.
- Brand voice — Bloomberg-terse vs. NPR-warm vs. Atlantic-essayistic.
  This is the synthesis prompt's personality.
- First 10 paying users — names + invite copy.
- Auth provider for D7+ — Resend magic links (preferred) or Clerk.

### Outlets seed list for v0 (LATAM + global EN)

**Dominican Republic** (target home market):
- Diario Libre · Listín Diario · Hoy · El Caribe · Acento · El Dinero

**Mexico**:
- El Universal · Reforma · Milenio · Animal Político · El Financiero

**Colombia**:
- El Tiempo · El Espectador · Semana · La República

**Argentina**:
- La Nación · Clarín · Infobae · Página/12

**Global EN (already in outlets file)**:
- FT · Bloomberg · WSJ · Reuters · AP · TechCrunch · The Economist · BBC

Total: ~25 outlets. Cycle every 60 min → ~5–10k articles/day → ~500
events/day after clustering.

## 12. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM hallucinates a "fact" in synthesis | High | High | Two-pass: synthesize, then second LLM call validates every claim cites a source. Drop unsourced sentences. |
| Outlet blocks our scraper | Medium | Medium | User-agent rotation; honor robots.txt; have 12 outlets so any 2 failing is fine. |
| Clustering produces 1-source "events" | High | Low | Hard rule: don't publish events with < 2 distinct sources. |
| Postgres pgvector cold-start slow | Low | Medium | Pre-warm common queries; cache rendered one-pagers in DO Spaces. |
| RabbitMQ free tier rate-limited | Medium | Low | Buffer events to local JSON when broker is slow. |
| DO Droplet OOMs under spike | Medium | Medium | Set memory limits; restart=always. Profile early. |
| Brand/legal — outlets complain about scraping | Low | High | Snippet-only display, link out to source. Keep raw HTML internal. |
| D6 deploy slips | High | High | Reserve D8 buffer. Soft launch to invited users only. |

## 13. What we keep building post-v0

Once v0 is live and ≥ 5 paying users have used it for ≥ 1 week:

1. **Re-split Curator** back into Entopics + Synochi + Unitas if quality
   bottlenecked, or scale demands it.
2. **Real auth + billing** (Stripe + magic links).
3. **Outlet intake UI** in Laravel platform (`apps/platform` already
   scaffolded under Messor).
4. **Per-claim provenance** with hover-to-show source snippets.
5. **Bias indicators** (left/center/right per source).
6. **Multi-language verticals** (start with es, then pt).
7. **Public API** for B2B (newsrooms, analysts).

## 14. Locked — direction confirmed

The make-or-break decisions are in §11. Direction:

- **Stack**: Messor → Curator (LLM-collapsed) → Reader.
- **LLM**: Anthropic Haiku 4.5 for everything LLM-shaped.
- **Vertical**: LATAM bilingual + global EN business/tech.
- **Deploy**: DO Droplet.

D2 begins: scaffold `Curator/` and `Reader/` monorepos. Messor already
has its house in order.

---

**Related**:
[Messor/docs/v1-scope.md](../Messor/docs/v1-scope.md) ·
[Messor/docs/dev-handoff.md](../Messor/docs/dev-handoff.md) ·
[Notion hub](https://www.notion.so/373eca56ed94818da548f66ca288593a)
