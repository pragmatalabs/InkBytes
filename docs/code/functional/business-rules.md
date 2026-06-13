# Reglas de Negocio

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

Cada regla lista su implementación (clase/método) y el ADR que la documenta. La mayoría son *precision-first*: prefieren dejar pasar un borderline antes que filtrar noticia legítima.

## Cosecha (Messor)

### BR-MES-01 — Gate de frescura estricto
- **Condición**: un artículo solo se cosecha si su `publish_date` cae dentro de `articles.freshness_window_hours` (48 h).
- **Consecuencia**: fecha ausente o no parseable → **descartado**; fecha futura > now + `_FUTURE_SKEW_DAYS` (2 d) → descartado. RSS `_feed_published` sirve de fallback.
- **Implementación**: `ScraperService.process_outlet_articles` + `is_article_fresh`. **ADR-0015** (Messor).

### BR-MES-02 — Solo cabeza del homepage
- **Condición**: del crawl de homepage se toma el **head**, cap `MAX_ARTICLES_PER_OUTLET = 300`.
- **Motivo**: el tail-crawl de newspaper3k sacaba enlaces de archivo profundos (años atrás).
- **Implementación**: `_slice_outlet_articles`. **ADR-0015**.

### BR-MES-03 — Dedup en 3 capas
- **Capa URL (7 días)**: `load_known_article_urls` carga URLs de staging files de los últimos 7 días para lookup O(1); más blocklist `url_skip_patterns.yaml`.
- **Capa de batch**: `article_exists` contra el `StagingStore` de la corrida actual.
- **Capa de contenido**: `check_article_exists_in_all_scrapes` por MD5(title+text); mismo hash = skip, hash cambiado = re-publica.
- **Implementación**: `ScraperService` + `StagingStore`. Relacionado con la regla per-RUN de abajo.

### BR-MES-04 — Staging filename por-RUN (no por-DÍA)
- **Regla**: los staging files se nombran `{int(time.time())}.{slug}.db.json` (timestamp por corrida), **no** por medianoche.
- **Motivo**: un archivo por-día acumula y re-publica todo cada ciclo (causa del flood de 105k mensajes). Por-RUN publica solo lo nuevo.
- **Implementación**: `process_outlet_articles`. **ADR-0014** (Messor).

### BR-MES-05 — Estado de dedup persistente
- **Regla**: `data/scrapes/` debe tener un volumen Docker; los volúmenes `inkbytes-postgres-data` y `inkbytes-messor-scrapes` son `external: true`.
- **Motivo**: sin volumen, cada deploy borra el estado de dedup y re-publica todo. `docker compose down -v` / `volume prune` jamás sobre el stack prod.
- **ADR-0012 / ADR-0014** (Messor).

## Enriquecimiento y clustering (Curator)

### BR-CUR-01 — Gate de frescura en intake
- **Condición**: en `Application._handle_event`, se descarta cualquier artículo cuyo `scraped_at` sea más viejo que `max_article_age_hours` (48 h), **antes** de cualquier llamada LLM.
- **Motivo**: guarda contra el incidente de 105k mensajes.
- **Implementación**: `Application._handle_event`. **ADR-0025**.

### BR-CUR-02 — Fast-path de duplicados
- **Condición**: `upsert_article_raw` calcula `content_hash` (MD5 de prefijo normalizado). Si el contenido no cambió y `enriched_at` ya está, devuelve `needs_enrichment=False`.
- **Consecuencia**: se salta ENRICH/embed/cluster (ahorro de costo LLM).
- **Implementación**: `_content_hash()`. **ADR-0018 / ADR-0015**.

### BR-CUR-03 — Gate de calidad de clustering
- **Condición**: un artículo se adjunta a un evento solo si su vecino más cercano cumple distancia coseno ≤ `1 - similarity_threshold` (0.50) **Y** solapamiento de entidades ≥ `entity_overlap_min` (1) **Y** el vecino tiene `event_id`.
- **Consecuencia**: si no, se siembra un evento nuevo (id ULID).
- **Implementación**: `ClusterSkill.run`; `_cluster_lock` evita sembrar eventos duplicados. **ADR-0017** (calibración bge-m3).

### BR-CUR-04 — Detección de breaking news
- **Condición**: un evento se marca breaking cuando ≥2 outlets distintos con `outlets.pulse=true` tienen artículos dentro de `breaking_window_minutes` (60), con guarda de recencia `breaking_recency_hours` (3) y TTL `breaking_ttl_hours` (2).
- **Implementación**: detector de velocidad en `ClusterSkill`. Override manual: comandos `event.mark_breaking` / `force_publish`. **ADR-0024**.

## Síntesis y publicación (Curator)

### BR-CUR-05 — Umbral mínimo de fuentes
- **Condición**: un evento solo se sintetiza/publica con ≥ `min_sources_to_publish` (2) outlets distintos.
- **Implementación**: `Application._synthesize_once`.

### BR-CUR-06 — Watermark de re-síntesis
- **Condición**: un evento solo se re-sintetiza cuando entra un **nuevo outlet** (`events.last_synth_source_count` < source_count actual). Sobrevive a reinicios.
- **Motivo**: evita re-síntesis (y costo) redundante.
- **Implementación**: `_synthesize_once` + lock `asyncio.Lock` por evento. mig. 015.

### BR-CUR-07 — Filtro de contenido promocional
- **Condición**: se salta un cluster cuyos títulos sean **mayoría estricta** comerciales (gift guides, "best X", deals, afiliados); además se rechazan headlines sintetizados con estilo de anuncio.
- **Excepción** `_EDITORIAL_KEEP`: NO filtra noticia que solo menciona una marca, ni noticia *sobre* un evento de compras (tips de fraude en Black Friday), ni best-of editorial ("best shows to stream").
- **Implementación**: `services/promo_filter.is_promotional()` / `promo_reason()`, aplicado en `SynthesizeSkill.run`, flag `application.filter_promotional`. **ADR-0020**. Tests: `scripts/test_promo_filter.py` (debe quedar ~0 falsos positivos).

### BR-CUR-08 — Filtro de filler no-noticia
- **Condición**: se salta un cluster mayoría-estricta de horóscopos / resultados de lotería / tips de apuestas; se rechazan headlines de filler.
- **Excepción**: NUNCA matchear nombres de signo sueltos (`Cáncer` enfermedad, Papa `León`, `Virgo`/`Virgin`); mantener noticia de regulación de gambling y `pronóstico` del clima.
- **Implementación**: `services/content_filter.is_excluded()` / `exclusion_reason()`, flag `application.filter_noise`. **ADR-0021**. Tests: `scripts/test_content_filter.py` (0 falsos positivos).

### BR-CUR-09 — Caps de artículos para el LLM
- **Condición**: la síntesis usa máximo `_MAX_ARTICLES` (15) artículos, `_MAX_PER_OUTLET` (2), ordenados por recencia.
- **Motivo**: cap de costo y de tokens.
- **Implementación**: `SynthesizeSkill`. **ADR-0015**.

### BR-CUR-10 — `freshness_at` = max(scraped_at)
- **Regla**: `pages.freshness_at` se calcula con `max(scraped_at)`, **nunca** `max(published_at)`.
- **Motivo**: `published_at` es provisto por el outlet (puede ser nulo, futuro o erróneo) y fijaría historias futuras arriba del feed. `scraped_at` es sellado por Messor en harvest (siempre presente, nunca futuro).
- **Implementación**: `SynthesizeSkill._persist`.

## Media

### BR-CUR-11 — Guarda de hotlink / foto de autor
- **Condición**: antes de aceptar un `lead_image`, se valida con `is_displayable()` (probe async con fingerprint de navegador `Sec-Fetch-*`) y `is_author_photo()` (regex de URL). Imágenes bloqueadas → NULL (fallback a otra fuente).
- **Motivo**: ciertos CDNs (p.ej. brightspot) devuelven un placeholder 1×1 con HTTP 200 a fetchers server-side; un `curl` 200 no prueba que la imagen renderice en el navegador.
- **Implementación**: `MediaValidator`, flag `application.validate_lead_images`, timeout `lead_image_probe_timeout_s` (4 s). **ADR-0019 / ADR-0016**.

### BR-CUR-12 — Media rail solo videos
- **Regla**: `pages.media_rail` contiene **solo videos** (YouTube). El fetcher de imágenes Bing está parado.
- **Motivo**: las imágenes traían fotos editoriales/producto off-topic.
- **Implementación**: `IllustrateSkill` (Playwright directo, sin `channel=`, flags Docker-safe), concurrencia limitada con `_illustrate_sem` (Semaphore 1). **ADR-0014 / ADR-0011**.

## Operación

### BR-OPS-01 — Kill-switch del pipeline
- **Condición**: `backoffice.curator_settings.processing_enabled = false` pausa el pipeline enrich→cluster→synthesize. Curator lo poll-ea (~30 s) y lanza `ProcessingPausedError`; los artículos se reencolan en RabbitMQ (sin pérdida), la API sigue arriba.
- **Implementación**: `CuratorSettingController@toggleProcessing` (escribe) ↔ `Application._handle_event` (lee). **ADR-0023**.

### BR-OPS-02 — Cuota / cap de costo LLM
- **Condición**: `LlmService.structured` lanza `LlmQuotaError` al detectar "usage limits"/"insufficient_quota"; el consumidor reencola y detiene vía `on_quota_exhausted`. No hay cap en $ duro — se apoya en el muro de cuota del proveedor.
- **Costo**: `CostMeter` acumula tokens/costo por label con pricing cache-aware y vuelca a `backoffice.model_usage`. **ADR-0028**.

### BR-OPS-03 — Validación de slugs en trigger de scrape
- **Condición**: `ScrapingJobController@trigger` valida `name`, `limit` (1–200) y `outlet_slugs` (regex `/^[a-z0-9._-]+$/` + allowlist contra `public.outlets.id`); rechaza corridas concurrentes (**409** si ya hay job pending/running).
- **Implementación**: `ScrapingJobController` + `RunScrapingWorker`.

### BR-OPS-04 — Alerta de una abierta por dedup_key
- **Condición**: índice parcial único en `alerts(dedup_key) WHERE status='open'` — no hay dos alertas abiertas con la misma clave.
- **Tipos**: scrape_low_success, stale_outlet, over_budget, pipeline_stalled.

## Archivo

### BR-CUR-13 — Conclusión de historias
- **Condición**: eventos sin actividad por ≥ `conclude_after_days` (default 0 = desactivado) se archivan a `story_arcs`.
- **Implementación**: `run_conclude_stories`. **ADR-0013**.

## RBAC
{#rbac}
- Roles `User::ROLES` = `admin`, `operator`, `viewer` (default `viewer`).
- Inclusivos: `isOperator()` true para operator **o** admin; `hasRole('viewer')` true para cualquier autenticado.
- `EnsureUserHasRole` (alias `role`) aborta **403** si no hay usuario o si falla todos los roles pasados (basta un match). El gate real es server-side; el React es cosmético.
