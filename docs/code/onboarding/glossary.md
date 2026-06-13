# Glosario del Dominio

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

| Término | Definición |
|---|---|
| **Evento (Event)** | Cluster de artículos sobre la misma historia. Unidad central del dominio (tabla `events`, id ULID). Estados: `draft`, `published`, `dropped`, `concluded`. |
| **Página (Page)** | La versión sintetizada y publicable de un evento (headline + síntesis Markdown + evidence rail). 1:1 con un evento; `pages.id = event_id`. Es lo que ve el lector. |
| **Artículo (Article)** | Una pieza cosechada de un outlet, enriquecida y embebida. Pertenece a 0..1 eventos. |
| **Outlet** | Medio de noticias del catálogo. Tiene región, idioma, vertical, `feed_url`, `pulse`. |
| **Messor** | Servicio harvester (Stage 1). Cosecha artículos y los publica a RabbitMQ. |
| **Curator** | Servicio LLM que colapsa Entopics+Synochi+Unitas en v0. Ejecuta enrich→cluster→synthesize→ask. |
| **Reader** | Frontend público Next.js que renderiza eventos publicados. |
| **Backoffice / platform** | App Laravel de operación, moderación y configuración. |
| **ENRICH** | Skill que clasifica/resume/extrae entidades de un artículo con una llamada LLM. |
| **CLUSTER** | Skill que asigna un artículo a un evento (vecino más cercano por coseno + entidades) o siembra uno nuevo. Sin LLM. |
| **SYNTHESIZE** | Skill que genera la página de un evento con ≥2 fuentes. |
| **ILLUSTRATE** | Skill que busca videos de YouTube para el media rail (fire-and-forget). |
| **ASK / Asistente** | Backend de chat RAG sobre eventos publicados (`POST /ask`). |
| **Embedding** | Vector 1024-dim (bge-m3) de un artículo, usado para clustering y recuperación. Columna `articles.embedding`. |
| **bge-m3** | Modelo de embeddings multilingüe (1024-dim) servido por Ollama vía endpoint OpenAI-compatible. |
| **Pulse** | Cosecha de alta frecuencia (cada ~5 min) restringida a outlets `pulse=true` con `feed_url`, para breaking news. |
| **Breaking news** | Evento marcado por velocidad: ≥2 outlets pulse dentro de `breaking_window_minutes` (ADR-0024). |
| **Evidence rail** | Lista de citas (2–8) con enlace a la fuente, en cada página. |
| **Media rail** | Galería de **solo videos** (YouTube) de una página (`pages.media_rail`, ADR-0014). |
| **Lead image** | Imagen principal de un artículo/evento; validada contra hotlinking antes de mostrarse (ADR-0019). |
| **Freshness gate** | Filtro que descarta artículos fuera de la ventana de 48 h (Messor en intake, Curator en consume). |
| **`freshness_at`** | Timestamp de frescura de una página = `max(scraped_at)` de sus artículos (nunca `published_at`). |
| **`scraped_at`** | Momento en que Messor cosechó el artículo (`NOW()` en harvest). Fuente de verdad de frescura. |
| **Content hash** | MD5 de prefijo normalizado para el fast-path de duplicados (`articles.content_hash`). |
| **Promo filter** | Filtro de contenido comercial/afiliado/deals (`promo_filter.py`, ADR-0020). |
| **Content / noise filter** | Filtro de filler no-noticia: horóscopos, lotería, apuestas (`content_filter.py`, ADR-0021). |
| **Kill-switch** | Toggle `processing_enabled` que pausa el pipeline de Curator sin pérdida de mensajes (ADR-0023). |
| **Watermark de síntesis** | `events.last_synth_source_count`: re-sintetiza solo cuando entra un nuevo outlet. |
| **Story arc** | Archivo de un evento concluido (`story_arcs`, ADR-0013). |
| **Theme / vertical** | Una de 8 categorías editoriales asignadas en ENRICH (`articles.theme`). `events.topic` está vacío — no usar. |
| **Región** | `"global"` o `"{macro}-{cc}"` (p.ej. `latam-do`, `europe-es`). Single source: `config/regions.php`. |
| **Lane** | Tipo de corrida de cosecha: `cycle` (programada) o `pulse` (`scrape_sessions.lane`). |
| **Staging file** | Archivo local por-RUN (`{ts}.{slug}.db.json`) donde Messor escribe antes de publicar (dedup). |
| **RBAC** | Roles inclusivos `viewer` ⊂ `operator` ⊂ `admin` (`EnsureUserHasRole`). |
| **`curator_settings`** | Tabla `backoffice` (fila única id=1) que overlay-ea la config de Curator en runtime. |
| **`model_usage`** | Tabla `backoffice` donde Curator vuelca el consumo de tokens/costo (`CostMeter`). |
| **ADR** | Architecture Decision Record. Numeración secuencial por servicio (`Curator/docs/adr/`, `docs/adr/`). |
| **v0** | El MVP actual: Curator colapsa los 3 servicios; vive en producción en `inkbytes.org`. |
