# Componente: Messor — Harvester Agent

## Identificación

| Atributo | Valor |
|---|---|
| **Nombre** | Messor (`apps/scraper`) |
| **Tipo** | Worker (long-running) + API auxiliar |
| **Versión** | 1.0.0 |
| **Equipo dueño** | Pipeline |
| **Repositorio** | `pragmatalabs/InkBytes` (subdir `Messor/`) |
| **Estado** | Estable (v1 scope locked) |

## Propósito

Cosechar artículos de outlets configurados, deduplicar, persistir en staging
local y DO Spaces, y emitir eventos `event.article.scraped` y
`scrape.session.completed` a RabbitMQ. Es el front door del pipeline.

## Responsabilidades

- Fetch HTML/RSS, parse con newspaper3k.
- Extraer campos objetivos (title, text, url, language, publish_date, authors, meta).
- Filtros de calidad: min_word_count, language allowlist, freshness window, dedup local + histórico.
- Persistir staging JSON local + subir a DO Spaces.
- Emitir un evento RabbitMQ por artículo + un evento por sesión.
- Servir `/api/scrapesessions` y `/api/outlets` solo lectura al Backoffice.

## NO es responsabilidad de este componente

- NER, topic modeling, sentiment, factuality (Curator).
- Clustering, similarity (Curator).
- Synthesis de one-pagers (Curator).
- Llamadas a LLM (Curator).
- Triggering de scraping (lo dispara el Backoffice vía queue worker).
- Outlets CRUD (lo hace el Backoffice).

## Interfaces

### Expone (produce)

| Interface | Tipo | Descripción |
|---|---|---|
| Exchange `messor` | RabbitMQ topic | Eventos `event.article.scraped` (`inkbytes.article.v1`) + `scrape.session.completed` (`inkbytes.session.v1`) |
| Exchange `messor.logs` | RabbitMQ topic | Log fan-out (ADR-0004) |
| `GET /api/scrapesessions` | FastAPI | Lee `data/scrapes/*.db.json` — historial paginado |
| `GET /api/outlets` | FastAPI | Lee `data/outlets/outlets.json` |
| `GET /healthz` | FastAPI | Liveness |
| `s3://inkbytes/messor/staging/<session>/*.json` | DO Spaces | Artefactos por ciclo |

### Consume (depende de)

| Dependencia | Tipo | Uso |
|---|---|---|
| Outlets HTML/RSS | HTTPS | Cosecha de contenido |
| RabbitMQ | AMQPS | Publish |
| DO Spaces | S3 | Upload |
| `data/outlets/outlets.json` | Filesystem | Lista de outlets activos |

## Tecnología

| Componente | Tecnología | Versión |
|---|---|---|
| Runtime | Python | 3.11 |
| Web framework | FastAPI | 0.99.1 (pinned, Pydantic v1) |
| Scraping | newspaper3k + lxml + lxml_html_clean | 0.2.8 / 5.x / 0.4+ |
| Bus client | pika | 1.3.2 |
| S3 client | boto3 | 1.34+ |
| Schemas | Pydantic | v1 (NO subir a v2 — ADR-0007) |
| Concurrencia | `ThreadPoolExecutor` | stdlib |

## Atributos de calidad

| Atributo | Objetivo v0 | Medición |
|---|---|---|
| Disponibilidad | 99.5% (restart=always) | Healthcheck Docker |
| Ciclo end-to-end | ≤ schedule_interval (60 min) | Stats por sesión |
| % artículos exitosos por outlet | ≥ 90% | Analytics service |
| Detección de duplicados | ≥ 99% (cross-session + cross-batch) | Test fixtures |
| Latencia publicación evento (fetch → RMQ ack) | < 30 s p95 | Logs estructurados |

## Decisiones de diseño relacionadas

- [Messor/docs/adr/0001-monorepo-migration.md](../../../Messor/docs/adr/0001-monorepo-migration.md)
- [Messor/docs/adr/0002-rabbitmq-events.md](../../../Messor/docs/adr/0002-rabbitmq-events.md)
- [Messor/docs/adr/0003-do-spaces-artifact-store.md](../../../Messor/docs/adr/0003-do-spaces-artifact-store.md)
- [Messor/docs/adr/0004-retire-hermes-namespace.md](../../../Messor/docs/adr/0004-retire-hermes-namespace.md)
- [Messor/docs/adr/0005-messor-curator-responsibility-split.md](../../../Messor/docs/adr/0005-messor-curator-responsibility-split.md)
