# Curator — Configuration Reference

> *Source of truth: `apps/curator/env.example.yaml` · Last updated: 2026-06-02*

Curator reads a YAML config at startup and overlays environment variables
on top. Secrets MUST come from env vars in production. Placeholders
`__SET_VIA_ENV__` cause a fail-fast in `production` mode (warning only in
`development`).

## File location

| Environment | Path |
|---|---|
| Dev | `apps/curator/env.local.yaml` (gitignored) |
| Docker / DO | `/app/env.yaml` (committed template) + env-var overlay |

CLI:

```bash
python main.py --config env.local.yaml --fixture fixtures/sample_article.json
python main.py --config env.yaml       --consume
```

## Sections

### `application`

| Field | Default | Description |
|---|---|---|
| `name` | `Curator` | Display name |
| `version` | `0.1.0` | Semantic version |
| `mode` | `development` | `development` \| `production` |
| `log_level` | `INFO` | DEBUG / INFO / WARNING / ERROR |
| `max_concurrent_articles` | `4` | Pipeline semaphore (parallel ENRICH+CLUSTER) |

### `llm`

| Field | Default | Description |
|---|---|---|
| `provider` | `anthropic` | Only Anthropic supported in v0 |
| `enrich_model` | `claude-haiku-4-5` | Skill 1 model |
| `synthesize_model` | `claude-haiku-4-5` | Skill 3 model |
| `max_tokens_enrich` | `600` | Output cap for ENRICH |
| `max_tokens_synth` | `900` | Output cap for SYNTHESIZE |
| `temperature` | `0.2` | Low for news work |
| `api_key` | env | `ANTHROPIC_API_KEY` |

### `embeddings`

| Field | Default | Description |
|---|---|---|
| `provider` | `openai` | Only OpenAI in v0 |
| `model` | `text-embedding-3-small` | 1536-dim |
| `dimensions` | `1536` | Must match the model |
| `api_key` | env | `OPENAI_API_KEY` |

### `clustering`

| Field | Default | Description |
|---|---|---|
| `similarity_threshold` | `0.78` | Min cosine similarity to join a cluster |
| `min_sources_to_publish` | `2` | Don't synthesize 1-source events |
| `entity_overlap_min` | `2` | Must share ≥ N entities |
| `recent_window_hours` | `48` | Only cluster against articles in this window |

### `database`

| Field | Default | Description |
|---|---|---|
| `url` | env | `DATABASE_URL` (postgresql://…) |
| `pool_min` | `2` | asyncpg pool min |
| `pool_max` | `10` | asyncpg pool max |

### `rabbitmq`

| Field | Default | Description |
|---|---|---|
| `url` | env | `RABBITMQ_URL` (amqp://…) |
| `consume_exchange` | `messor` | Messor publishes here |
| `consume_queue` | `curator.articles-scraped` | Bound to the exchange |
| `consume_routing_key` | `event.article.scraped` | Topic pattern |
| `publish_exchange` | `curator` | Curator's own outbound exchange |

### `spaces`

S3-compatible storage. Production = DO Spaces; dev = MinIO.

| Field | Default | Description |
|---|---|---|
| `endpoint_url` | env | `S3_ENDPOINT` |
| `access_key` | env | `S3_KEY` |
| `secret_key` | env | `S3_SECRET` |
| `bucket` | `inkbytes` | Shared bucket |
| `region` | `nyc3` | DO region |

### `api`

| Field | Default | Description |
|---|---|---|
| `host` | `0.0.0.0` | Bind host; internal-only in prod |
| `port` | `8060` | Bind port |
| `cors_allow_origins` | `["http://localhost:3000", "http://localhost:3001"]` | Reader + Admin origins |

## Env-var overrides (the mapping)

| Env var | YAML target |
|---|---|
| `ANTHROPIC_API_KEY` | `llm.api_key` |
| `OPENAI_API_KEY` | `embeddings.api_key` |
| `DATABASE_URL` | `database.url` |
| `RABBITMQ_URL` | `rabbitmq.url` |
| `S3_ENDPOINT` | `spaces.endpoint_url` |
| `S3_KEY` | `spaces.access_key` |
| `S3_SECRET` | `spaces.secret_key` |
| `S3_BUCKET` | `spaces.bucket` |
| `CURATOR_LOG_LEVEL` | `application.log_level` |
| `CURATOR_MODE` | `application.mode` |

## Fail-fast rules

In `production` mode, missing `database.url` or `rabbitmq.url` raises at
boot. Missing LLM/embedding keys log a warning and the services drop into
**stub mode** (offline-deterministic outputs) — this is intentional so a
broken vendor doesn't fail the deploy; you decide per-incident.

## Minimal dev config

```yaml
application: { mode: development, log_level: DEBUG, max_concurrent_articles: 2 }
llm:         { api_key: LOCAL_DEV_UNSET }           # stub mode
embeddings:  { api_key: LOCAL_DEV_UNSET }           # stub mode
clustering:  { similarity_threshold: 0.78, min_sources_to_publish: 2,
               entity_overlap_min: 2, recent_window_hours: 48 }
database:    { url: postgresql://inkbytes:inkbytes@localhost:5432/inkbytes }
rabbitmq:    { url: amqp://messor:messor@localhost:5672/ }
spaces:      { endpoint_url: http://localhost:9000, access_key: messor,
               secret_key: messormessor, bucket: inkbytes, region: us-east-1 }
api:         { host: 127.0.0.1, port: 8060 }
```
