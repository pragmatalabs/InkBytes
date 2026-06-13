# API Reference

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

Cubre los cuatro superficies HTTP del monorepo más los contratos de RabbitMQ que unen Messor y Curator.

- [Curator API (`:8060`)](#curator-api-8060)
- [Messor Harvester API (`:8050`)](#messor-harvester-api-8050)
- [Backoffice (Laravel, `:80`)](#backoffice-laravel-80)
- [Reader route handlers (Next.js)](#reader-route-handlers-nextjs)
- [Contratos RabbitMQ](#contratos-rabbitmq)

---

## Curator API (`:8060`)

FastAPI (`core/api_server.py`, montado con `build_app(app)`). CORS habilitado (`GET`, `POST`). **Sin autenticación en ningún endpoint** (servicio interno detrás de la red Docker / Traefik). Límites de query: `_MAX_EVENTS_LIMIT=500`, `_MAX_GRAPH_NODES=200`, `_MAX_GRAPH_EDGES=500`, `_MAX_QUESTION_LEN=500`.

### `GET /healthz`
**Descripción**: Liveness probe. **Auth**: No. **Response**: `{ok, service, version}`.

### `GET /readyz`
**Descripción**: Readiness probe; ejecuta `db.healthcheck()`. **Auth**: No. **Response**: `{ok, checks:{database}}`; **503** si la BD está caída.

### `GET /status`
**Descripción**: Conteos del pipeline + estado vivo. **Auth**: No.
**Response**: `articles_total/enriched/embedded/pending`, `events_total/published`, `pages_published`, `synths_in_flight`, `processing_enabled`, `llm:{provider, enrich_model, synthesize_model, base_url}`, `embeddings:{provider, model, dimensions, stale, blocked, reembedding}`.

### `GET /events`
**Descripción**: Eventos publicados, más recientes primero, con ranking global-first (ADR-0017). **Auth**: No.
**Parámetros** (query, combinados con AND):

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `limit` | int | 500 | Máx 500 |
| `theme` | string | — | Validado contra `_VALID_THEMES` (8 verticales) |
| `category` | string | — | Filtro por categoría |
| `topic` | string | — | Filtro por topic (drill-down de trending) |

**Response**: lista de `{id, headline, freshness_at, published_at, source_count, article_count, language, topic, theme, outlet_names[≤5], synthesis_excerpt(180), avg_factuality, lead_image, coverage_spark[7×6h], has_global_outlet, category}`. `Cache-Control: public, max-age=30`.
`lead_image` = COALESCE de la imagen de un artículo con `cluster_distance ≤ 0.45`, si no `events.hero_image`.

### `GET /events/{event_id}`
**Descripción**: Página única de un evento (join `pages` + `events`, status IN `published`/`concluded`). **Auth**: No. **404** si no existe.
**Response**: `p.*` + `source_count, article_count, topic, lead_image, timeline[≤20]`, y `media_rail` decodificado. `timeline` y `media_rail` pasan por `_decode_json_col` (columnas JSONB devueltas como string por asyncpg — ver ADR-R-0004).

### `GET /events/{event_id}/related`
**Descripción**: Eventos relacionados por solapamiento de entidades + topic (ADR-0005). **Auth**: No.
**Parámetros**: `limit=5`, `min_score=0.4`. Score = coeficiente de solapamiento de entidades × multiplicador de topic (1.3 si mismo topic).
**Response**: `[{id, headline, freshness_at, published_at, source_count, article_count, topic, language, outlet_names, score}]`. **404** si el evento no está publicado.

### `GET /topics/trending`
**Descripción**: Top topics por número de eventos distintos en una ventana (ADR-0027). **Auth**: No.
**Parámetros**: `window_hours=48` (clamp 1h–7d), `limit=20` (máx 100). Junk filtrado vía `_JUNK_TOPIC_PATTERNS`; cuasi-duplicados colapsados con `_dedupe_trending` (Jaccard ≥0.5).
**Response**: `[{topic, event_count, article_count, theme}]`. `max-age=120`.

### `GET /graph`
**Descripción**: Grafo de co-ocurrencia de entidades (ADR-0005 Approach A, tabla `entities`). **Auth**: No.
**Parámetros**: `min_event_count=2`, `limit_nodes=80` (cap 200), `min_edge_weight=2`, `limit_edges=250` (cap 500).
**Response**: `{nodes, edges, meta:{node_count, edge_count, event_count}}`. `max-age=120`.

### `GET /outlets`
**Descripción**: Catálogo de outlets con estadísticas (`db.get_outlets_with_stats()`). **Auth**: No. **Consumido por Messor** como fuente primaria de outlets. **Response**: lista de outlets con stats.

### `POST /ask`
**Descripción**: Asistente de chat sobre el corpus (RAG sobre eventos publicados, ADR-0022). **Auth**: No.
**Request body**: `AskRequest { question (máx 500), mode }` — `mode` ∈ `resume` | `top10` | `chat`; en `chat` la pregunta no puede ser vacía (**400**).
**Response**: `{answer_md, sources:[{n, event_id, title, summary, topic, outlet, url}]}`. Las URLs de las fuentes son `/event/{id}` (deterministas, nunca emitidas por el modelo).

---

## Messor Harvester API (`:8050`)

FastAPI (`api/main.py` + `api/routers/scrape.py`), CORS `*`. **Sin autenticación** (el módulo `api_security.py` contiene solo código muerto no cableado).

### `GET /`
Health/banner → `{"message":"Hola Mundo"}`.

### `GET /api/scrapesessions`
**Descripción**: Historial de cosecha paginado, construido desde los staging files locales (`data/scrapes/`). Nombre de archivo: `{unix_ts}.{outlet_slug}.db.json`.
**Parámetros**: `page`, `limit`, `outlet`, `today` (acepta también estilo Strapi: `pagination[page]`, `pagination[pageSize]`, `filters[outlet][$eq]`).
**Response**: `{data:[...], meta:{pagination:{page, pageSize, pageCount, total}}}`.

### `POST /api/scrape/trigger`
**Descripción**: Lanza una cosecha one-shot en un thread daemon de fondo (lo invoca el worker del Backoffice). Responde de inmediato.
**Request body**: `{outlet_slugs:[...], limit:N}` → se traduce a `--outlets=a,b --limit=N`.
**Response**: `{status:"accepted", message, outlet_slugs, limit}`.

### `POST /api/scrape/on-demand`
**Descripción**: Cosecha on-demand de breaking-news (ADR-0029), en fondo con prioridad AMQP 9.
**Request body**: `{query, url, lang(en|es), limit(1–25)}` — requiere `query` **o** `url`.
**Response**: `{status:"accepted", brand, query, url}`.

### `GET /api/outlets`
**Descripción**: Catálogo de outlets (solo activos) desde `outlets.json`. **Response**: `[{outlet...}]`.

---

## Backoffice (Laravel, `:80`)

### API pública
- `GET /api/news-outlets` → `SourceApiController@index` — catálogo de outlets de solo lectura (fuente de fallback para Messor).

### Web (Inertia) — todas bajo `middleware(['auth','verified'])`

**Solo lectura (cualquier rol autenticado):**

| Método | URI | Controlador |
|---|---|---|
| GET | `/` | Home (sin auth) |
| GET | `/dashboard` | `DashboardController` |
| GET | `/outlets`, `/outlets/export` | `OutletController@index`, `@export` |
| GET | `/scraping`, `/scraping/status`, `/scraping/{id}/stream` (SSE), `/scraping/{id}/tail` | `ScrapingJobController` |
| GET | `/runtime`, `/runtime/snapshot` | `RuntimeController` |
| GET | `/run-history` | `RunHistoryController@index` |
| GET | `/scrape-results`, `/scrape-results/{session}` | `ScrapeResultsController` |
| GET | `/health`, `/api/curator-pipeline` | `HealthController@index`, `@curatorPipeline` |
| GET | `/alerts` | `AlertController@index` |
| GET | `/moderation` | `EventModerationController@index` |
| GET | `/model-usage`, `/model-usage/export` | `ModelUsageController` |

**`role:operator`:**

| Método | URI | Controlador@método |
|---|---|---|
| POST/PUT/DELETE | `/outlets`, `/outlets/{outlet}`, `/outlets/bulk` | `OutletController@store/@update/@destroy/@bulk` |
| POST | `/outlets/import/preview`, `/outlets/import/apply` | `@importPreview`, `@importApply` |
| POST | `/alerts/{alert}/acknowledge` | `AlertController@acknowledge` |
| POST | `/scraping/trigger` | `ScrapingJobController@trigger` |
| POST | `/moderation/pages/{page}/publish\|unpublish\|drop` | `EventModerationController@publishPage/@unpublishPage/@dropPage` |
| POST | `/moderation/events/{event}/resynthesize\|recluster` | `@resynthesizeEvent/@reclusterEvent` |

**`role:admin`:**

| Método | URI | Controlador@método |
|---|---|---|
| GET/PUT | `/settings` | `CuratorSettingController@edit/@update` |
| POST | `/settings/reset`, `/settings/reembed`, `/settings/processing` (kill-switch) | `@reset/@reembed/@toggleProcessing` |
| GET/POST/PUT/DELETE | `/api-keys`, `/api-keys/{apiKey}`, `/api-keys/history`, `/api-keys/{apiKey}/test` | `ApiKeyController` |
| GET | `/audit-log` | `AuditLogController@index` |
| GET/PUT | `/users`, `/users/{user}/role` | `UserController@index/@updateRole` |

**`auth`:** `/profile` (`ProfileController@edit/@update/@destroy`). **`routes/auth.php`**: grupos guest/auth de Laravel Breeze (register, login, forgot/reset password, verify-email, confirm-password, `PUT password`, `POST logout`).

> Roles inclusivos: `admin` ⊇ `operator` ⊇ `viewer`. La verificación real es server-side (`EnsureUserHasRole`, alias `role`); el hide/disable en React es cosmético. Ver [business-rules.md](../functional/business-rules.md#rbac).

---

## Reader route handlers (Next.js)

### `POST /api/ask` (`app/api/ask/route.ts`)
Proxy del asistente. Valida `mode` ∈ `{resume, top10, chat}` (default `chat`), trunca `question` a 500 chars, exige pregunta no vacía en `chat`. Reenvía a `${CURATOR_API_URL}/ask` (`cache:"no-store"`). Devuelve `{answer_md, sources[]}`; **400** input inválido, **502** si Curator falla.

### `POST /api/auth` (`app/api/auth/route.ts`)
Gate de password de demo. Lee `formData` (`password`, `next`). Compara contra `INKBYTES_DEMO_PASSWORD`; mismatch → 303 a `/login?error=1`; éxito → setea cookie `inkbytes_auth` (httpOnly, sameSite lax, secure en prod, 30 días) y 303 a `next`. Si la env var no está, el gate queda abierto.

> Las páginas del Reader (`/`, `/event/[id]`, `/entities`, etc.) consumen la Curator API vía `lib/api.ts`. Ver [data layer](#reader-data-layer) abajo.

### Reader data layer (`lib/api.ts`)
`BASE = process.env.CURATOR_API_URL ?? "http://localhost:8060"`. `apiFetch<T>(path, revalidate)` usa `fetch(..., {next:{revalidate}})`.

| Función | Endpoint Curator | revalidate |
|---|---|---|
| `getEvents(limit=500, {theme,topic,category})` | `/events` | 60 |
| `getEvent(id)` | `/events/{id}` | 300 |
| `getRelatedEvents(id, minScore=0.4, limit=5)` | `/events/{id}/related` | 300 |
| `getTrendingTopics(limit=12, windowHours=48)` | `/topics/trending` | 120 |
| `getGraph(...)` | `/graph` | 120 |
| `getOutlets()` | `/outlets` | 60 |
| `getStatus()` | `/status` | 30 |

---

## Contratos RabbitMQ

La frontera Messor→Curator es **JSON sobre RabbitMQ** (pydantic v1 publica, pydantic v2 valida).

### Exchange `messor` (topic, durable)

**`event.article.scraped`** — un mensaje por artículo. Publicado por Messor (`message_service.publish_article_event`), consumido por Curator en la cola `curator.articles-scraped` (`x-max-priority:10`). Schema `inkbytes.article.v1`:

```json
{
  "schema": "inkbytes.article.v1",
  "session_id": "session-<ts>-<slug>",
  "spaces_key": "messor/...",
  "article": {
    "id": "...", "outlet": {"id": "...", "name": "..."},
    "url": "...", "canonical_url": "...", "title": "...",
    "text": "(≤8000 chars)", "language": "en|es",
    "published_at": "...", "scraped_at": "...", "word_count": 0,
    "authors": [], "meta_categories": [], "category": "...",
    "keywords": [], "metadata": {}, "lead_image": "...", "video_url": "..."
  }
}
```
Los mensajes de *pulse* (breaking) se publican con `priority=9`.

**`event.scrape.session.completed`** — resumen por outlet tras cada corrida. Cola `curator.scrape-sessions`. Schema `inkbytes.scrape_session.v1`: `{session_id, started_at, ended_at, total/successful/failed_articles, duplicates_total, success_rate, duration, outlets[], total_outlets, lane: "pulse"|"cycle"}`.

### Exchange `curator.commands` (topic, durable)

Comandos de moderación publicados por el Backoffice (vía la **management HTTP API** de RabbitMQ) y consumidos por Curator (`message_service.consume_commands`, routing `#`). Payload `{"id": targetId}`. Comandos válidos (`CuratorCommandService::COMMANDS` ↔ `Application._handle_command`):

`page.publish`, `page.unpublish`, `page.drop`, `event.resynthesize`, `event.recluster`, `event.mark_breaking`, `event.clear_breaking`, `event.force_publish`, `embeddings.reembed`.

### Exchange `messor.logs`

Exchange/cola de logging (renombrado desde `hermes`, ADR-0004). La cola legacy `articles-scraped` (eventos a nivel de archivo) ya **no** se publica (huérfana, cleanup 2026-06-13).

### Política de ack/nack (Curator, `message_service.py`)
- `prefetch_count = 8`.
- `ProcessingPausedError` (kill-switch) → sleep 5s + `nack(requeue=True)`.
- `LlmQuotaError` → `nack(requeue=True)` + `on_quota_exhausted`.
- Errores transientes (`APITimeoutError`/`APIConnectionError`) → `nack(requeue=True)`.
- Otros → `nack(requeue=False)` (drop). Comandos de mutación nunca se reencolan.
