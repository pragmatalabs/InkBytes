# Configuration

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

Convenciones del repo:
- Los YAML versionados usan placeholders **`__SET_VIA_ENV__`**; los secretos reales llegan por variables de entorno del shell del host.
- **Nunca** pegar API keys en chat ni commitearlas. Configurar vía shell (`~/.zshrc`) o 1Password/Doppler.
- Curator combina tres capas de config (en orden): **YAML** (`env.yaml` / `--config`) → **overlay de env vars** → **overlay en runtime desde `backoffice.curator_settings`** (re-leído cada ~30 s).

## Variables de entorno del host (nunca commitear)

```bash
export ANTHROPIC_API_KEY='sk-ant-...'   # LLM enrich + synthesize
export OPENAI_API_KEY='sk-...'          # fallback de embeddings / LLM
# Postgres + RabbitMQ + MinIO ya están en env.local.yaml
```

## Curator (`Curator/apps/curator/`)

### Env vars (`core/config.py` → `_overlay_env`)

| Variable | Mapea a |
|---|---|
| `ANTHROPIC_API_KEY` | `llm.api_key` |
| `OPENAI_API_KEY` | `embeddings.api_key` + `llm.openai_api_key` |
| `DEEPSEEK_API_KEY` | `llm.deepseek_api_key` |
| `EMBEDDINGS_PROVIDER` / `_BASE_URL` / `_MODEL` / `_DIMENSIONS` | config de embeddings |
| `DATABASE_URL` | `database.url` |
| `RABBITMQ_URL` | `rabbitmq.url` |
| `S3_ENDPOINT` / `_KEY` / `_SECRET` / `_BUCKET` | object store |
| `CURATOR_LOG_LEVEL`, `CURATOR_MODE` | logging / modo |

`database.url` y `rabbitmq.url` fallan-rápido si quedan en `__SET_VIA_ENV__` en modo producción.

### Tunables overlay desde `backoffice.curator_settings` (`_DB_SETTINGS_MAP`)
`enrich_model`, `synthesize_model`, `max_tokens_enrich`, `max_tokens_synth`, `temperature`, `llm_provider`, `llm_base_url`, las API keys (vacío = "usar env"), `similarity_threshold`, `entity_overlap_min`, `min_sources_to_publish`, `recent_window_hours`, `conclude_after_days`, `processing_enabled`, `embeddings_provider`/`model`/`base_url`.
`dimensions` se excluye a propósito (es un asunto de migración). **Las API keys son env-only**; Curator nunca lee `backoffice.api_keys`.

### Defaults principales (`config.py`)

| Grupo | Valores |
|---|---|
| `AppCfg` | `max_concurrent_articles=8`, `max_article_age_hours=48`, `config_refresh_seconds=30`, `validate_lead_images=True`, `lead_image_probe_timeout_s=4.0`, `filter_promotional=True`, `filter_noise=True`, `processing_enabled=True` |
| `LlmCfg` | `provider=anthropic`, `enrich_model=synthesize_model=claude-haiku-4-5`, `max_tokens_enrich=1500`, `max_tokens_synth=2500`, `temperature=0.2` |
| `EmbedCfg` | `provider=ollama`, `model=bge-m3`, `dimensions=1024`, `base_url=http://localhost:11434/v1` |
| `ClusterCfg` | `similarity_threshold=0.50`, `min_sources_to_publish=2`, `entity_overlap_min=1`, `recent_window_hours=48`, `breaking_window_minutes=60`, `breaking_ttl_hours=2`, `breaking_recency_hours=3` |
| `DbCfg` | `pool_min=2`, `pool_max=10` |
| `RmqCfg` | `consume_exchange=messor`, `consume_queue=curator.articles-scraped`, `consume_routing_key=event.article.scraped`, `prefetch_count=8`, `commands_exchange/queue=curator.commands` |
| `ApiCfg` | `host=0.0.0.0`, `port=8060`, `cors_allow_origins=["*"]` |

## Messor — Harvester (`Messor/apps/scraper/`)

### Env vars (`env.example.yaml`, `core/config.py`)

| Variable | Propósito |
|---|---|
| `CURATOR_OUTLETS_URL` | fuente primaria de outlets (default `http://localhost:8060/outlets`) |
| `MESSOR_API_BASE_URL` | fallback de outlets (Backoffice) |
| `RABBITMQ_HOST` / `PORT` / `USER` / `PASS` | sobrescriben el YAML |
| `MESSOR_SCHEDULE_INTERVAL_MINUTES` | ciclo de cosecha (default **360** = 4×/día) |
| `MESSOR_STARTUP_DELAY_MINUTES` | retraso de arranque (default 0) |
| `MESSOR_PULSE_INTERVAL_MINUTES` | intervalo del hilo pulse (default 5; 0 desactiva) |
| `DO_SPACES_KEY` / `DO_SPACES_SECRET` / `DO_API_TOKEN` | DigitalOcean Spaces |
| `PLATFORM_API_TOKEN` | API del Backoffice |

### YAML clave
- Exchanges: `general=inkbytes@`, `scraping=messor`, `logging=messor.logs`.
- `articles.freshness_window_hours: 48`; `articles.supported_languages: [en, es]`.
- `scraper.min_word_count: 40`; `scraping.save_mode: send_to_api`.
- `platform_api.endpoints.outlets: news-outlets`.

## Messor — Backoffice (`Messor/apps/platform/`)

Laravel `.env` estándar. Claves específicas de InkBytes:
- **DB**: conexión `pgsql`, base `inkbytes`, `search_path = backoffice,public`.
- **`config/regions.php`**: convención de regiones (ver abajo).
- **`config/curator.php`** / `services.curator.rabbitmq`: `management_url` (default `http://localhost:15672`), user/pass `messor`, vhost `/`, `commands_exchange=curator.commands`.
- **`config/scraping.php`**: `command` (env `SCRAPING_COMMAND`, con placeholder `{SCRAPE_ARGS}`), `remote_host`/`ssh_key_path`/`ssh_options` para deploy SSH.
- **`config/runtime_monitor.php`**: `socket_path` del daemon Docker.
- `CURATOR_URL` (`:8060`) y `MESSOR_URL` (`:8050`) para los health probes.

### Regla de regiones (`config/regions.php`)
Una región es **`"global"`** o **`"{macro}-{cc}"`** donde `{macro}` ∈ keys de `macros` y `{cc}` = ISO 3166-1 alpha-2 minúsculas.
- `macros.latam` = `[dr, mx, co, ar, pe, cl, ec, pr, ve]`
- `macros.europe` = `[es, fr, de]`
- `standalone` = `[global]`

La whitelist `allowed` es **derivada** (consumida por `OutletController` y el dropdown de la UI). Para extender, añadir el código bajo su macro — **nunca** mantener una segunda lista a mano.

## Reader (`Reader/apps/web/`)

| Variable | Default | Uso |
|---|---|---|
| `CURATOR_API_URL` | `http://localhost:8060` | `lib/api.ts`, `/api/ask`, `sitemap`; en prod apunta al host interno `inkbytes-curator-api` |
| `NEXT_PUBLIC_BASE_URL` | `https://inkbytes.app` | layout/sitemap/robots |
| `NEXT_PUBLIC_SITE_URL` | — | base de fallback para auth |
| `INKBYTES_DEMO_PASSWORD` | — | password del gate de demo (si no está, gate abierto) |
| `NODE_ENV` | — | flag `secure` de cookie + ayudas de splash |

`next.config.ts`: `output: "standalone"`. `proxy.ts` (middleware) es el gate de auth, **deshabilitado en v0** (devuelve `NextResponse.next()`).

> ⚠️ No usar `export const revalidate = N` en páginas del Reader que llaman servicios Docker internos: ISR pre-renderiza durante el `docker build` cuando el hostname interno no existe y hornea el estado de error. Usar `export const dynamic = "force-dynamic"` (ADR-R-0005).
