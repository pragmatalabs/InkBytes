# Curator — InkBytes pipeline (Stages 2 + 3 + 4)

> *The LLM-powered service that turns Messor's articles into reader-ready one-pagers.*
>
> *In v0 this collapses what the long-term architecture splits into Entopics
> (NER + topics), Synochi (synthesis) and Unitas (clustering + QA). See
> [docs/adr/0001-curator-collapses-pipeline.md](./docs/adr/0001-curator-collapses-pipeline.md).*

## What it does

```text
RabbitMQ event "articles-scraped" from Messor
              │
              ▼
   ┌──────────────────────────┐
   │ Skill 1: ENRICH          │  Haiku → {entities, topic, summary, sentiment, factuality}
   ├──────────────────────────┤
   │ Skill 2: CLUSTER         │  embedding + cosine + entity overlap → event_id
   ├──────────────────────────┤
   │ Skill 3: SYNTHESIZE      │  Haiku → {headline, synthesis_md, evidence_rail}
   └──────────┬───────────────┘
              ▼
        Postgres (events, articles, entities, pages)
              │
              ▼
        Reader (winston-r) reads /event/[id]
```

## Layout

```text
Curator/
├── apps/curator/             # the Python service
│   ├── main.py               # entrypoint
│   ├── core/                 # application, config, api_server
│   ├── skills/               # enrich, cluster, synthesize
│   ├── services/             # llm, embedding, message, database, storage
│   ├── contracts/            # Pydantic v2 models for the v1 event schema
│   ├── prompts/              # Haiku prompts as .md files
│   ├── db/migrations/        # SQL schema
│   ├── fixtures/             # sample article event for offline dev
│   ├── env.{example,local}.yaml
│   ├── requirements.txt · pyproject.toml · Dockerfile
├── docs/                     # service-specific docs
└── infra/docker/             # production overrides
```

## Quickstart

```bash
# from the parent InkBytes/ directory, bring up infra
bash orchestrator/scripts/up.sh

# install Curator deps
cd Curator/apps/curator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# apply DB migration
psql postgresql://inkbytes:inkbytes@localhost:5432/inkbytes -f db/migrations/001_initial_schema.sql

# set required env (or copy env.example.yaml → env.local.yaml and fill in)
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export DATABASE_URL=postgresql://inkbytes:inkbytes@localhost:5432/inkbytes
export RABBITMQ_URL=amqp://messor:messor@localhost:5672/

# run offline against a fixture (no Messor required)
python main.py --fixture fixtures/sample_article.json

# or run against a live RabbitMQ
python main.py --consume
```

## Contract with Messor

The full contract is in [`Messor/docs/contracts.md`](../Messor/docs/contracts.md).
TL;DR: Curator receives `inkbytes.article.v1` events and is the
**sole owner** of every enrichment, clustering and synthesis field.

## Status

- v0 scaffold (D2): structure ✅ · skills wired ✅ · DB schema ✅
- D3: real Haiku calls + first 10 hand-checked event pages in DB
- D4: Reader pulls from DB

See [`../docs/mvp-plan.md`](../docs/mvp-plan.md) for the week-of plan.
