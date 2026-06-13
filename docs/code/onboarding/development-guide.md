# Guía de Desarrollo

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

## Workflow obligatorio para TODOS los agentes

> Referencia completa: [`docs/dev-workflow.md`](../../dev-workflow.md).

### Regla 1 — Probar localmente ANTES de desplegar
Nunca hacer push a `origin/master` ni disparar un deploy de producción sin verificar el cambio en dev local.

| Cambio | Verificación mínima |
|---|---|
| Python (Curator/Messor) | bootear el servicio + ejercitar el code path |
| Reader (Next.js) | `npm run dev`, abrir localhost:3000, verificar visualmente |
| Config | confirmar que el contenedor recoge el valor |

Recién entonces: commit → push → `bash infra/deploy.sh [--build]`.

### Regla 2 — Commit local, esperar instrucción de push/deploy
Commitear localmente; **no** hacer push ni deploy sin instrucción explícita. Terminar siempre con: "N commits ahead of origin, ready to push when you say so". Deploy target: **solo DigitalOcean** (`67.205.136.61` / `inkbytes.org`); Hostinger está retirado.

## Convenciones

- **Prompts como archivos `.md`** en `Curator/apps/curator/prompts/` (diffables, revisables). Política de versionado en `Curator/docs/prompts.md`. No escribir prompts como strings Python inline.
- **Pydantic v2 en Curator** (no degradar); **Pydantic v1 en Messor** (no actualizar hasta INK-Sprint-2). La frontera es JSON sobre RabbitMQ.
- **ADRs** para toda decisión no trivial; numeración secuencial por servicio.
- **Banner de status** al tope de cada doc: `> *Status: vN · Owner: ... · Last updated: YYYY-MM-DD*`.
- **`__SET_VIA_ENV__`** como placeholder en YAML versionado; los secretos reales vienen de env vars.
- **Nunca** pegar API keys en chat.

## Patrones de arquitectura

- **Curator** es un servicio de 5 *skills* (`EnrichSkill`, `ClusterSkill`, `SynthesizeSkill`, `IllustrateSkill`, `AssistantSkill`) orquestados por `Application`, **no** un framework multi-agente (LangGraph/CrewAI/AutoGen fueron rechazados explícitamente en ADR-0001).
- Inyección de dependencias manual en `Application.__init__` (servicios + skills).
- Concurrencia con primitivas asyncio: `Semaphore(max_concurrent_articles)`, `_embed_sem` (1), `_cluster_lock`, `_illustrate_sem` (1), locks de síntesis por evento.
- **Messor** usa DI en `Application.__init__` (Config, LoggingService, RestClient, MessageService, StorageService, OutletService, ScraperService, AnalyticsService, APIServer, CommandProcessor) y threading (`ThreadPoolExecutor` por outlet, hilo de pulse, lock de scraping).
- **Backoffice** es Laravel 11 estándar (controllers/models/jobs/middleware) con la peculiaridad del split de schemas `backoffice`/`public`.

## Anti-patrones a evitar (los más caros)

- **Acceder a columnas JSONB de asyncpg sin `_decode_json_col()`** — asyncpg las devuelve como string. En el Reader, guardar defensivamente: `Array.isArray(v) ? v : JSON.parse(v)` (ADR-R-0004).
- **`export const revalidate = N` en páginas del Reader que llaman servicios Docker internos** — ISR pre-renderiza durante el build y hornea el estado de error. Usar `force-dynamic` (ADR-R-0005).
- **`Schema::hasColumn()` en migraciones del Backoffice para tablas `public.*`** — Doctrine DBAL solo introspecciona el primer schema del `search_path` (`backoffice`), así que `public.outlets` es invisible y el guard siempre devuelve false. Usar query cruda contra `information_schema.columns` (ADR-0016 Messor, migraciones `2026_06_10_*`).
- **`IllustrateSkill` sin gate de concurrencia** — cada run abre un Chromium (~200 MB); N eventos concurrentes → OOM. Envolver en `_illustrate_sem` (ADR-0011).
- **Chromium en Docker sin `seccomp:unconfined`** — el perfil seccomp por defecto bloquea los flags de `clone()` que Chromium necesita → SIGTRAP. El worker en `docker-compose.do.yml` lleva `shm_size: '256m'` + `security_opt: [seccomp:unconfined]` (ADR-0011).
- **Scrapling `StealthyFetcher`/`DynamicFetcher` en Docker** — inyectan `channel='chromium'` que SIGTRAP-crashea. Usar `playwright`/`patchright` directamente sin argumento `channel` (ADR-0011).
- **Staging filenames por-DÍA en Messor** — usar timestamp por-RUN (`int(time.time())`), no `generate_today_timestamp()` (causó el flood de 105k mensajes, ADR-0014).
- **`pages.freshness_at` con `max(published_at)`** — usar siempre `max(scraped_at)`.
- **Re-agregar `topics_extracted`/`clusters_path`/config `openai:` a Messor** o llamar `newspaper3k.Article.nlp()` ahí — eso es territorio de Curator (ADR-0005).
- **Volúmenes Docker**: cualquier servicio que escribe estado (dedup, staging) necesita un volumen nombrado; al añadir uno, sembrar con el nombre prefijado `<project>_<volume>` (ADR-0012 Messor).
- **No llamar `logger.setLevel()` sobre el logger** en `LoggingService` — `LoggerFactory` solo setea nivel en los handlers; el logger hereda `WARNING` del root y descarta los `INFO` antes de cualquier handler.

## Tests

- Curator: `scripts/test_promo_filter.py`, `scripts/test_content_filter.py` (ambos deben quedar en ~0 falsos positivos sobre el corpus), `scripts/test_lead_image_validation.py`.
- Messor: `scripts/test_freshness_gate.py`, `scripts/test_per_run_staging.py`.
- Al añadir patrones a un filtro, re-correr ambos tests de filtros + el corpus check.

## Dónde apuntar el `pwd`

| Tarea | `cd` |
|---|---|
| Multi-servicio / docs de sistema | `/Volumes/Pragmata/Projects/InkBytes/` (lee `CLAUDE.md` raíz) |
| Curator | `Curator/apps/curator/` |
| Messor harvester | `Messor/apps/scraper/` |
| Reader | `Reader/apps/web/` |
