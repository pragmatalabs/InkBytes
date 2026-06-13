# Flujos Principales

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

## 1. Cosecha → publicación (end-to-end)

El flujo completo desde que Messor cosecha un artículo hasta que aparece en el Reader.

```mermaid
sequenceDiagram
    participant O as Outlet (RSS/HTML)
    participant M as Messor scraper
    participant R as RabbitMQ (messor)
    participant C as Curator
    participant DB as Postgres+pgvector
    participant LLM as Claude Haiku 4.5
    participant E as Ollama bge-m3
    participant Rd as Reader

    M->>O: RSS-first / homepage head
    M->>M: gate frescura 48h + dedup 3 capas
    M->>R: event.article.scraped (inkbytes.article.v1)
    R->>C: consume (curator.articles-scraped)
    C->>C: kill-switch + gate edad 48h
    C->>DB: upsert_article_raw (content_hash)
    alt contenido sin cambios
        C-->>C: needs_enrichment=False → skip (fast-path)
    else nuevo/cambiado
        C->>LLM: ENRICH (theme/topic/summary/entities)
        C->>E: embed (1024-dim)
        C->>DB: write_enrichment + embedding
        C->>DB: CLUSTER (vecino coseno + entidades)
        alt source_count >= 2
            C->>LLM: SYNTHESIZE (página)
            C->>C: promo_filter + content_filter
            C->>DB: INSERT pages (status=published)
            C-)LLM: ILLUSTRATE (video rail, fire-and-forget)
        end
    end
    Rd->>C: GET /events, /events/{id}
    C->>DB: query published
    C-->>Rd: JSON
```

## 2. Pipeline interno de Curator (`_handle_event`)

```mermaid
flowchart TD
    A[Mensaje event.article.scraped] --> B{processing_enabled?}
    B -->|No| Bx[ProcessingPausedError\nnack requeue + sleep 5s]
    B -->|Sí| C[Semaphore max_concurrent_articles]
    C --> D{scraped_at < 48h?}
    D -->|No| Dx[drop - stale]
    D -->|Sí| E[validar lead_image\nMediaValidator]
    E --> F[upsert_article_raw]
    F --> G{needs_enrichment?}
    G -->|No| Gx[fast-path: skip LLM]
    G -->|Sí| H[ENRICH - 1 llamada LLM]
    H --> I[embed bajo _embed_sem]
    I --> J[write_enrichment]
    J --> K[CLUSTER bajo _cluster_lock]
    K --> L{source_count >= min_sources_to_publish?}
    L -->|No| Lx[esperar más fuentes]
    L -->|Sí| M{watermark: nuevo outlet?}
    M -->|No| Mx[skip re-síntesis]
    M -->|Sí| N[SYNTHESIZE]
    N --> O{promo / noise gate?}
    O -->|mayoría comercial/filler| Ox[skip publish]
    O -->|ok| P[persist page\nfreshness_at=max scraped_at]
    P --> Q[ILLUSTRATE fire-and-forget]
```

## 3. Clustering (decisión attach vs. seed)

```mermaid
flowchart TD
    A[Artículo enriquecido + embedding] --> B[Buscar ≤20 vecinos recientes\nmismo idioma, ventana recent_window_hours\nORDER BY embedding <=> vector]
    B --> C{primer vecino con\ndistance ≤ 1-similarity_threshold?}
    C -->|No| S[Seed evento nuevo ULID]
    C -->|Sí| D{solapamiento entidades\n≥ entity_overlap_min?}
    D -->|No| S
    D -->|Sí| E{vecino tiene event_id?}
    E -->|No| S
    E -->|Sí| F[Attach al evento\n+ update source/article_count]
    F --> G{≥2 outlets pulse\nen breaking_window_minutes?}
    G -->|Sí| H[Marcar breaking]
    G -->|No| I[fin]
```

## 4. Moderación desde el Backoffice

El Backoffice no habla AMQP directamente: publica comandos vía la **HTTP management API** de RabbitMQ.

```mermaid
sequenceDiagram
    participant Op as Operador
    participant BO as Backoffice (Laravel)
    participant MGMT as RabbitMQ Mgmt API
    participant EX as exchange curator.commands
    participant C as Curator

    Op->>BO: POST /moderation/pages/{id}/publish
    BO->>BO: EnsureUserHasRole(operator)
    BO->>MGMT: PUT exchange (idempotente)
    BO->>MGMT: POST publish {routing_key:page.publish, payload:{id}}
    MGMT-->>BO: {routed:true|false}
    Note over BO: si routed=false → error (consumer no bound)
    EX->>C: consume_commands (#)
    C->>C: _handle_command → page.publish
    BO->>BO: AuditLog.record
```

## 5. Trigger de cosecha desde el Backoffice

```mermaid
sequenceDiagram
    participant Op as Operador
    participant BO as Backoffice
    participant J as RunScrapingWorker (queue: scraping)
    participant M as Messor API :8050

    Op->>BO: POST /scraping/trigger {limit, outlet_slugs}
    BO->>BO: validar slugs + rechazar concurrencia (409)
    BO->>BO: crear ScrapingJob (pending) + AuditLog
    BO->>J: dispatch
    J->>J: composeScrapeArgs() → --outlets=.. --limit=..
    J->>M: curl POST /api/scrape/trigger (local o SSH)
    M-->>J: 202 accepted (thread daemon)
    J->>BO: update ScrapingJob (running→completed/failed)
    Note over J,BO: logs → storage/logs/scraping/{id}.log (stream SSE)
```

## 6. Asistente de chat (RAG)

```mermaid
sequenceDiagram
    participant U as Lector
    participant Rd as Reader (/api/ask)
    participant C as Curator (/ask)
    participant E as Ollama bge-m3
    participant DB as Postgres
    participant LLM as Claude Haiku 4.5

    U->>Rd: pregunta + mode
    Rd->>Rd: validar mode, truncar 500 chars
    Rd->>C: POST /ask {question, mode}
    alt mode resume/top10 (digest)
        C->>DB: eventos publicados recientes (36h, ≤50)
    else mode chat
        C->>E: embed pregunta
        C->>DB: ANN pgvector top-12
    end
    C->>LLM: synthesize_model + prompts/assistant.md
    C-->>Rd: {answer_md, sources[n→/event/{id}]}
    Rd-->>U: render markdown + citas [n]
```
