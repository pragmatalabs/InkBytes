# Vista de Contenedores — InkBytes (C4 L2)

## Diagrama C4 — Nivel 2: Contenedores

```mermaid
C4Container
  title Vista de Contenedores — InkBytes v0

  Person(reader, "Lector pago")
  Person(admin, "Operador / Editor")

  System_Boundary(inkbytes, "InkBytes Platform") {
    Container(web, "Reader Web", "Next.js / React", "Lista de eventos + /event/[id]")
    Container(backoffice, "Backoffice", "Laravel + Inertia + MUI", "Outlets CRUD, scrape trigger, run history, alertas")
    Container(messor_api, "Messor API", "Python / FastAPI", "GET /api/scrapesessions, /api/outlets — solo lectura para Backoffice")
    Container(messor_worker, "Messor Harvester", "Python / newspaper3k", "Scheduled / one-shot — produce eventos articles-scraped")
    Container(curator_api, "Curator API", "Python / FastAPI", "GET /events, /events/{id}, /healthz, /readyz, /status")
    Container(curator_worker, "Curator Pipeline", "Python / asyncio / Haiku", "ENRICH → CLUSTER → SYNTHESIZE")
    Container(queue_worker, "Backoffice Queue Workers", "PHP CLI", "queue:work --queue=scraping + schedule:work (alertas B11)")
    Container(ollama, "Ollama (embeddings)", "Go runtime", "bge-m3 local — endpoint /v1 OpenAI-compatible")
    ContainerDb(pg, "Postgres + pgvector", "PostgreSQL 16", "events, articles, entities, pages, scrape_sessions, users")
    ContainerDb(spaces, "DigitalOcean Spaces", "S3-compatible", "Staging JSONs, logs, raw HTML")
    ContainerQueue(rmq, "RabbitMQ", "AMQPS", "Exchanges: messor (events), messor.logs")
  }

  System_Ext(outlets, "News Outlets")
  System_Ext(anthropic, "Anthropic")

  Rel(reader, web, "HTTPS")
  Rel(admin, backoffice, "HTTPS")

  Rel(backoffice, messor_api, "Lista sesiones / outlets", "HTTP/JSON")
  Rel(backoffice, queue_worker, "Encola job de scraping (DB)", "DB")
  Rel(queue_worker, messor_worker, "Shell-exec con --no-api", "exec")

  Rel(messor_worker, outlets, "Cosecha", "HTTPS / RSS")
  Rel(messor_worker, spaces, "Sube staging JSON", "HTTPS / S3")
  Rel(messor_worker, rmq, "Publica article.scraped + session.completed", "AMQPS")

  Rel(curator_worker, rmq, "Consume articles-scraped", "AMQPS")
  Rel(curator_worker, anthropic, "ENRICH + SYNTHESIZE", "HTTPS")
  Rel(curator_worker, ollama, "Embed (bge-m3)", "HTTP / OpenAI-compat")
  Rel(curator_worker, pg, "Persiste articles/events/pages", "TCP/SSL")
  Rel(curator_worker, pg, "Persiste scrape_sessions (ADR-0006)", "TCP/SSL")

  Rel(curator_api, pg, "Lee pages para Reader", "TCP/SSL")
  Rel(web, curator_api, "GET /events, /events/{id}", "HTTPS")

  Rel(messor_api, pg, "Lee scrape_sessions (opcional)", "TCP/SSL")
```

## Catálogo de contenedores

| Contenedor | Tecnología | Puerto | Responsabilidad | Equipo dueño |
|---|---|---|---|---|
| `reader` | Next.js 14 / React | 3000 | UI pública: lista de eventos + página de evento | Front |
| `backoffice` | Laravel 11 + Inertia + MUI | 8080 | Admin: outlets, scrape trigger, history, alertas B11 | Platform |
| `messor-api` | Python 3.11 / FastAPI | 8050 | Endpoints de lectura para Backoffice (`/api/scrapesessions`, `/api/outlets`) | Pipeline |
| `messor-worker` | Python 3.11 / newspaper3k | — | Harvester en modo scheduled o one-shot | Pipeline |
| `curator-api` | Python 3.11 / FastAPI | 8060 | Endpoints de lectura para Reader (`/events`, `/events/{id}`) | Pipeline |
| `curator-worker` | Python 3.11 / asyncio | — | Pipeline ENRICH → CLUSTER → SYNTHESIZE | Pipeline |
| `queue-worker` | PHP CLI | — | `queue:work --queue=scraping` (dispara scrape) + `schedule:work` (alertas B11) | Platform |
| `ollama` | Go (binario) | 11434 | `bge-m3` local; endpoint OpenAI-compatible `/v1/embeddings` | Platform |
| `postgres` | PostgreSQL 16 + pgvector | 5432 | System of record | Platform |
| `rabbitmq` | CloudAMQP / DO managed | 5672 / 15672 | Event spine + log fan-out | Platform |
| `spaces` | DO Spaces (S3) | 443 | Artefactos staging/history | Platform |

## Comunicación entre contenedores

| Origen | Destino | Protocolo | Formato | Sincrónico | Schema |
|---|---|---|---|---|---|
| `reader` | `curator-api` | HTTPS | JSON | Sí | — |
| `backoffice` | `messor-api` | HTTP | JSON | Sí | — |
| `backoffice` | `queue-worker` (vía Postgres) | DB-backed | — | Sí (enqueue) | Laravel jobs |
| `queue-worker` | `messor-worker` | `exec` | CLI args | Sí | `SCRAPING_COMMAND` env |
| `messor-worker` | `spaces` | HTTPS (S3) | JSON files | Sí | per-cycle staging JSON |
| `messor-worker` | `rabbitmq` | AMQPS | JSON | No (publish + confirm) | `inkbytes.article.v1` · `scrape.session.completed` |
| `curator-worker` | `rabbitmq` | AMQPS | JSON | No (consume) | `inkbytes.article.v1` |
| `curator-worker` | `ollama` | HTTP | OpenAI-compat | Sí | `/v1/embeddings` |
| `curator-worker` | `anthropic` | HTTPS | JSON / tool_use | Sí | `EnrichmentResult` / `PageV1` |
| `curator-worker` | `postgres` | TCP/SSL | SQL + pgvector | Sí | schema 001 |
| `curator-api` | `postgres` | TCP/SSL | SQL | Sí | read-only views |

## Notas operativas

- **`messor-worker` con `--no-api`** se ejecuta cuando el queue worker lo dispara,
  para coexistir con `messor-api` que ya tiene el puerto 8050. Sin ese flag,
  el worker intentaría bindear el puerto y morir.
- **Backoffice requiere DOS procesos de fondo** (Laravel): `queue:work --queue=scraping --timeout=0` y `schedule:work`. Sin ellos, el botón "▶ Iniciar Scraping" encola pero no ejecuta.
- **El cliente React legado fue retirado** en B12.3 (ADR-0001 "one admin"). El Backoffice es el único admin.
