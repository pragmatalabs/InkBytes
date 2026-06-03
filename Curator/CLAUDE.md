# Curator — Service Briefing (Claude Code handoff)

> *Read this first if you're working on Curator.*
> *Status: D2 scaffold ✅ · D3 in progress · Last updated: 2026-06-02*

## What this service is

Curator is the LLM-powered pipeline between Messor (harvester) and the
Reader. For v0 it collapses Entopics + Synochi + Unitas into one Python
service with three skills:

| Skill | What it does | How |
|---|---|---|
| **ENRICH** | Per-article NER + topic + summary + sentiment + factuality | Anthropic Claude Haiku 4.5 via `instructor` (structured output) |
| **CLUSTER** | Group same-event articles | OpenAI `text-embedding-3-small` → pgvector cosine + entity overlap |
| **SYNTHESIZE** | When cluster ≥ 2 sources, write the one-pager | Claude Haiku 4.5 again |

See [`docs/adr/0001-curator-collapses-pipeline.md`](./docs/adr/0001-curator-collapses-pipeline.md) for the why.

## Layout

```
Curator/
├── apps/curator/                  ← THE service (cd here for code work)
│   ├── main.py                    ← CLI: --consume | --fixture | --dry-run | --api-only
│   ├── core/
│   │   ├── application.py         ← DI, lifecycle, pipeline orchestrator
│   │   ├── config.py              ← YAML + env-var overlay, fail-fast
│   │   └── api_server.py          ← FastAPI /healthz /readyz /status /events /events/{id}
│   ├── services/
│   │   ├── llm_service.py         ← Anthropic via instructor (async); stubs offline
│   │   ├── embedding_service.py   ← OpenAI; deterministic-hash stub offline
│   │   ├── database_service.py    ← asyncpg + pgvector; auto-applies migration
│   │   └── message_service.py     ← aio-pika consumer
│   ├── skills/
│   │   ├── enrich.py · cluster.py · synthesize.py
│   ├── contracts/                 ← Pydantic v2 schemas
│   │   ├── article_v1.py          ← inkbytes.article.v1 (Messor → Curator)
│   │   ├── enriched_v1.py         ← EnrichmentResult (Skill 1 output)
│   │   └── page_v1.py             ← PageV1 (Skill 3 output)
│   ├── prompts/                   ← .md files — version-controlled prompts
│   │   ├── enrich.md
│   │   └── synthesize.md
│   ├── db/migrations/
│   │   └── 001_initial_schema.sql ← events, articles, entities, pages + pgvector
│   ├── fixtures/
│   │   ├── sample_article.json    ← BBC central-bank story
│   │   └── sample_article_2.json  ← Reuters version, same story
│   ├── env.example.yaml           ← committed template
│   ├── env.local.yaml             ← gitignored dev override
│   ├── requirements.txt · pyproject.toml · Dockerfile
└── docs/                          ← README, architecture, configuration, prompts, ADRs
```

## Where to pwd

```bash
cd /Volumes/Pragmata/Projects/InkBytes/Curator/apps/curator
source .venv/bin/activate
```

## Required env vars (host shell, never commit)

```bash
export ANTHROPIC_API_KEY='sk-ant-...'   # required for real ENRICH + SYNTHESIZE
export OPENAI_API_KEY='sk-...'          # required for real embeddings
```

Without them, Curator drops into **stub mode** (deterministic offline outputs) — useful for prompt iteration and plumbing tests, useless for evaluating quality.

## Bring infra up (Postgres + RabbitMQ + MinIO)

From repo root:

```bash
cd /Volumes/Pragmata/Projects/InkBytes
bash orchestrator/scripts/up.sh
```

Curator auto-applies its DB migration on first connect. No need to `psql -f` manually.

## Run modes

```bash
# Offline ENRICH+embed only — no DB, no broker. Pure prompt iteration.
python main.py --config env.local.yaml --dry-run fixtures/sample_article.json

# Full pipeline on a fixture — needs Postgres up.
python main.py --config env.local.yaml --fixture fixtures/sample_article.json
python main.py --config env.local.yaml --fixture fixtures/sample_article_2.json
# ↑ second one should trigger SYNTHESIZE because event now has 2 sources

# Production loop — needs Postgres + RabbitMQ up, plus Messor publishing.
python main.py --config env.local.yaml --consume

# API only (no pipeline) — useful for the Reader (D4) to develop against.
python main.py --config env.local.yaml --api-only
```

## Inspect what's in the DB

```bash
docker exec -i inkbytes-dev-postgres psql -U inkbytes -d inkbytes -c "
  SELECT id, outlet_name, topic, sentiment, factuality, event_id
  FROM articles ORDER BY scraped_at DESC LIMIT 10;
"

docker exec -i inkbytes-dev-postgres psql -U inkbytes -d inkbytes -c "
  SELECT id, headline, length(synthesis_md) AS md_chars,
         jsonb_array_length(evidence_rail) AS n_sources, published_at
  FROM pages ORDER BY published_at DESC LIMIT 5;
"
```

To reset:

```bash
docker exec -i inkbytes-dev-postgres psql -U inkbytes -d inkbytes -c "
  TRUNCATE pages, entities, articles, events CASCADE;
"
```

## Status checklist (live)

- [x] Scaffold (D2): all 30+ files
- [x] Imports clean
- [x] Real Haiku call returns valid `EnrichmentResult`
- [x] Real OpenAI embedding (1536-dim) lands in `articles.embedding`
- [x] DB schema auto-applies
- [x] CLUSTER seeds a new event on first article
- [ ] CLUSTER attaches the second article (Reuters fixture, may need similarity threshold tuning)
- [ ] SYNTHESIZE fires and writes a `pages` row
- [ ] FastAPI `/events` lists pages
- [ ] Consume real Messor events from RabbitMQ
- [ ] Dockerfile builds and runs
- [ ] Deploy to DO Droplet

## Key tuning knobs in `env.local.yaml`

| Knob | Default | Effect |
|---|---|---|
| `clustering.similarity_threshold` | 0.78 | Lower → more aggressive clustering |
| `clustering.entity_overlap_min` | 1 (dev) / 2 (prod) | How many shared entity names required |
| `clustering.min_sources_to_publish` | 2 | Don't publish single-source events |
| `clustering.recent_window_hours` | 48 | How far back to look for cluster neighbours |
| `llm.temperature` | 0.2 | Low for news work; nudge up only for synthesis if it feels stiff |
| `application.max_concurrent_articles` | 4 (prod) / 2 (dev) | Pipeline parallelism cap |

## Prompts policy

- Prompts are `.md` files in `prompts/`. Edit freely; commit as code.
- Schema changes (adding/removing fields in `EnrichmentResult` / `PageV1`) → bump to `enrich.v2.md` + new Pydantic model + ADR. Old code reads v1, new reads v2.
- After any prompt edit, re-run `--dry-run` against a fixture and eyeball.
- See [`docs/prompts.md`](./docs/prompts.md) for the full policy.

## Cost watch

| Item | Today's cost | Notes |
|---|---|---|
| 1 ENRICH call (~1400 in / ~280 out) | ~$0.003 | Haiku 4.5 |
| 1 SYNTHESIZE call (~5000 in / ~600 out) | ~$0.008 | varies with cluster size |
| 1 embedding | ~$0.00002 | `text-embedding-3-small` |
| Projected at 5k articles/day + 500 events/day | ~$75/mo | matches MVP plan §8 |

## Known quirks (heads-up)

1. **Anthropic SDK is sync OR async** — use `from anthropic import AsyncAnthropic` (not `Anthropic`) when wiring instructor. Already done in `services/llm_service.py`. Don't downgrade.
2. **FastAPI ≥ 0.115 required** because Curator is on Pydantic v2. Messor's `fastapi==0.99.1` (Pydantic v1) is a different venv — don't conflate them.
3. **Auto-migration runs only if `articles` doesn't exist.** It's not a real migration system. For v1 we'll add a `schema_migrations` table; right now any change to `001_initial_schema.sql` after rows exist requires a manual `TRUNCATE` + reapply.
4. **Stub mode is loud** — first run without env vars logs WARNING twice ("LlmService running in STUB mode", "EmbeddingService running in STUB mode"). That's the indicator, not a bug.
5. **Embedding stub is hash-based**, not semantic. Don't try to test clustering quality without `OPENAI_API_KEY` set.

## Where to read more

| Topic | File |
|---|---|
| Why we collapsed 3 services into 1 | [`docs/adr/0001-curator-collapses-pipeline.md`](./docs/adr/0001-curator-collapses-pipeline.md) |
| C4 architecture + data flow | [`docs/architecture.md`](./docs/architecture.md) |
| Every config knob | [`docs/configuration.md`](./docs/configuration.md) |
| Prompt versioning rules | [`docs/prompts.md`](./docs/prompts.md) |
| Input contract (Messor side) | [`../Messor/docs/contracts.md`](../Messor/docs/contracts.md) |
| MVP plan (week-of) | [`../docs/mvp-plan.md`](../docs/mvp-plan.md) |
