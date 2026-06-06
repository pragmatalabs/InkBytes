# Componente: Curator — LLM Pipeline

## Identificación

| Atributo | Valor |
|---|---|
| **Nombre** | Curator (`apps/curator`) |
| **Tipo** | Worker (long-running async) + API |
| **Versión** | 0.1.0 |
| **Equipo dueño** | Pipeline |
| **Repositorio** | `pragmatalabs/InkBytes` (subdir `Curator/`) |
| **Estado** | En desarrollo (D3 — primer pipeline real end-to-end verificado) |

## Propósito

Transformar artículos de Messor en one-pagers reader-ready. En v0
colapsa Entopics + Synochi + Unitas en un solo servicio Python con tres
skills (ADR-0001 de Curator).

## Responsabilidades

- Consumir eventos `inkbytes.article.v1` de RabbitMQ.
- Persistir el shell crudo del artículo (`articles` table).
- **Skill 1 ENRICH**: una llamada Haiku → `EnrichmentResult` (entities, topic, summary, sentiment, factuality, keywords_canonical).
- **Skill 2 CLUSTER**: embedding bge-m3 + cosine + entity overlap → asignar/crear `event_id`.
- **Skill 3 SYNTHESIZE**: cuando `source_count ≥ min_sources_to_publish`, llamada Haiku → `PageV1` (headline, synthesis_md, evidence_rail, entities_top).
- Persistir `scrape_sessions` (de Messor `scrape.session.completed`, ADR-0006).
- Servir `/events`, `/events/{id}`, `/healthz`, `/readyz`, `/status` al Reader y Backoffice.

## NO es responsabilidad de este componente

- Cosechar artículos (Messor).
- Renderizar HTML del one-pager (Reader).
- Trigger / scheduling (Messor + Backoffice).
- Billing / auth (Backoffice / post-v0).

## Interfaces

### Expone (produce)

| Interface | Tipo | Descripción |
|---|---|---|
| `GET /healthz` | FastAPI | Liveness 200 |
| `GET /readyz` | FastAPI | 200 si DB + RMQ saludables; 503 si no |
| `GET /status` | FastAPI | Counters: articles_total, enriched, events, pages |
| `GET /events?limit=N` | FastAPI | Lista paginada de pages publicadas |
| `GET /events/{id}` | FastAPI | PageV1 completo |
| Exchange `curator` (post-v0) | RabbitMQ | Eventos `event.event.updated`, `event.page.published` |

### Consume (depende de)

| Dependencia | Tipo | Uso |
|---|---|---|
| RabbitMQ `messor` exchange | AMQPS | Consume `event.article.scraped` |
| Anthropic API | HTTPS | Haiku 4.5 para ENRICH + SYNTHESIZE |
| Ollama local `/v1/embeddings` | HTTP | bge-m3 (1024-dim) — primario |
| OpenAI `/v1/embeddings` | HTTPS | text-embedding-3-small — fallback |
| Postgres + pgvector | TCP/SSL | events, articles, entities, pages, scrape_sessions |
| `prompts/*.md` | Filesystem | Versioned prompts |

## Tecnología

| Componente | Tecnología | Versión |
|---|---|---|
| Runtime | Python | 3.11 |
| Web framework | FastAPI | ≥ 0.115 (Pydantic v2) |
| Async runtime | asyncio | stdlib |
| Bus client | aio-pika | 9.4+ |
| DB client | asyncpg + pgvector | 0.29 / 0.3 |
| LLM client | anthropic AsyncAnthropic + instructor | ≥ 0.40 / ≥ 1.6 |
| Embedding client | httpx (a Ollama) + openai (fallback) | — |
| Schemas | Pydantic | v2 |
| Retries (planned) | tenacity | 8.5+ |

## Atributos de calidad

| Atributo | Objetivo v0 | Medición |
|---|---|---|
| Disponibilidad consumer | 99.5% | aio-pika robust reconnect + Docker restart |
| Latencia ENRICH p95 | < 3 s/artículo | Anthropic response time |
| Latencia SYNTHESIZE p95 | < 8 s/evento | Idem |
| Costo /artículo (ENRICH) | ≤ $0.005 | Tokens × tarifa Haiku |
| Costo /evento (SYNTHESIZE) | ≤ $0.015 | Idem |
| Cluster recall (mismo evento) | ≥ 85% en dataset de test | Manual hand-check de 100 eventos |
| LLM JSON validity | ≥ 99% (instructor + retries) | Logs |

## Tuning knobs (env.yaml)

| Knob | Default | Rango razonable |
|---|---|---|
| `clustering.similarity_threshold` | 0.78 | 0.70–0.85 |
| `clustering.entity_overlap_min` | 1 (dev) / 2 (prod) | 1–3 |
| `clustering.min_sources_to_publish` | 2 | 2–4 |
| `clustering.recent_window_hours` | 48 | 24–72 |
| `llm.temperature` | 0.2 | 0.0–0.4 |
| `application.max_concurrent_articles` | 4 (prod) / 2 (dev) | 1–8 |

## Decisiones de diseño

- [Curator/docs/adr/0001-curator-collapses-pipeline.md](../../../Curator/docs/adr/0001-curator-collapses-pipeline.md)
- Curator ADR-0003 (Ollama bge-m3 como primario; ver `Curator/CLAUDE.md` — pendiente de archivar como ADR formal en `Curator/docs/adr/0003-ollama-bge-m3-embeddings.md`).
- [Curator/docs/prompts.md](../../../Curator/docs/prompts.md) — versionado de prompts.
