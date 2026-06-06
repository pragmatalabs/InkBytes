# Vista de Componentes — InkBytes (C4 L3)

Esta vista descompone cada contenedor relevante en sus componentes
internos. Para componentes individuales con su contrato detallado ver
[components/](../components/).

## 1. Messor (apps/scraper) — Componentes

```mermaid
C4Component
  title Componentes — Messor Harvester

  Container_Boundary(messor, "Messor — apps/scraper") {
    Component(cli, "CLI", "argparse", "Modos: scheduled / one-shot / interactive / --no-api")
    Component(app, "Application", "Python", "DI + lifecycle + process lock")
    Component(cfg, "Config", "PyYAML", "Carga env.yaml")
    Component(log, "LoggingService", "Python logging + pika", "Sink: stdout + messor.logs exchange")
    Component(msg, "MessageService", "pika", "RabbitMQ publisher (article.scraped + session.completed)")
    Component(outlets, "OutletService", "JSON loader", "Lee data/outlets/*.json")
    Component(scraper, "ScraperService", "ThreadPoolExecutor", "Orquesta cosecha por outlet")
    Component(stage, "StagingStore", "stdlib json", "JSON-file per-cycle store (reemplaza TinyDB)")
    Component(storage, "StorageService", "boto3", "DO Spaces upload")
    Component(analytics, "AnalyticsService", "Python", "Stats por sesión")
    Component(api, "APIServer", "FastAPI", "/api/scrapesessions, /api/outlets")
  }

  Rel(cli, app, "invoca")
  Rel(app, cfg, "lee")
  Rel(app, log, "wires")
  Rel(app, msg, "wires")
  Rel(app, outlets, "wires")
  Rel(app, scraper, "wires")
  Rel(app, storage, "wires")
  Rel(app, analytics, "wires")
  Rel(app, api, "wires (opcional)")
  Rel(scraper, stage, "dedup + persist")
  Rel(scraper, storage, "delega upload")
  Rel(scraper, msg, "publica eventos")
```

### Responsabilidades por capa (Messor)

| Capa | Componentes | Patrón | Responsabilidad |
|---|---|---|---|
| Presentación | `CLI`, `APIServer` | argparse / FastAPI | Entradas (CLI, HTTP) |
| Aplicación | `Application`, `ScraperService` | Service Layer + DI | Orquestación del agente |
| Dominio | `models.outlets`, `models.articles` (en `packages/inkbytes`) | DDD pobre | Tipos del dominio |
| Infraestructura | `StorageService`, `MessageService`, `StagingStore` | Repository / Adapter | I/O |

## 2. Curator (apps/curator) — Componentes

```mermaid
C4Component
  title Componentes — Curator Pipeline

  Container_Boundary(curator, "Curator — apps/curator") {
    Component(cli, "main.py", "argparse + asyncio", "Modos: --consume / --fixture / --dry-run / --api-only")
    Component(app, "Application", "Python asyncio", "DI + lifecycle + Semaphore(N) pipeline")
    Component(cfg, "Config", "pydantic + YAML", "env.yaml + env-var overlay + fail-fast")
    Component(mq, "MessageService", "aio-pika", "Consumer de articles-scraped (topic exchange)")
    Component(db, "DatabaseService", "asyncpg + pgvector", "Pool + auto-migration on startup")
    Component(llm, "LlmService", "instructor + AsyncAnthropic", "Structured outputs (Haiku 4.5); stub offline")
    Component(emb, "EmbeddingService", "httpx → Ollama (/v1)", "bge-m3 local; OpenAI fallback; stub offline")
    Component(s_enr, "EnrichSkill", "Skill 1", "1 Haiku call → EnrichmentResult")
    Component(s_clu, "ClusterSkill", "Skill 2", "pgvector cosine + entity overlap → event_id")
    Component(s_syn, "SynthesizeSkill", "Skill 3", "1 Haiku call → PageV1 cuando sources ≥ 2")
    Component(api, "APIServer", "FastAPI", "/healthz, /readyz, /status, /events, /events/{id}")
    Component(contracts, "Contracts", "Pydantic v2", "article_v1 · enriched_v1 · page_v1")
    Component(prompts, "Prompts", "Markdown files", "enrich.md, synthesize.md (versionados como código)")
  }

  Rel(cli, app, "invoca")
  Rel(app, cfg, "lee")
  Rel(app, mq, "consume")
  Rel(app, db, "wires")
  Rel(app, s_enr, "Skill 1")
  Rel(app, s_clu, "Skill 2")
  Rel(app, s_syn, "Skill 3")
  Rel(app, api, "expone")
  Rel(s_enr, llm, "structured call")
  Rel(s_enr, prompts, "carga enrich.md")
  Rel(s_clu, db, "embedding NN + entities")
  Rel(s_syn, llm, "structured call")
  Rel(s_syn, prompts, "carga synthesize.md")
  Rel(s_syn, db, "lee cluster + persiste page")
  Rel(s_enr, contracts, "valida EnrichmentResult")
  Rel(s_syn, contracts, "valida PageV1")
  Rel(s_enr, emb, "(no — embedding lo hace Application)")
```

### Loop del pipeline (Curator)

```text
Application._handle_event(payload)
  │
  ├─► db.upsert_article_raw(article, spaces_key)       — fila raw
  │
  ├─► enrich.run(article)              → EnrichmentResult (LLM)
  │
  ├─► embed.embed(title + text[:4000]) → list[float] (1024-dim bge-m3)
  │
  ├─► db.write_enrichment(...)         — persist enrichment + embedding + entities
  │
  ├─► cluster.run(article_id, embedding, entities, ...)  → ClusterResult
  │
  └─► if cluster.source_count ≥ min_sources_to_publish:
         synthesize.run(event_id)      → PageV1 (LLM); INSERT pages
```

## 3. Backoffice (apps/platform) — Componentes (resumen)

```mermaid
C4Component
  title Componentes — Backoffice Laravel

  Container_Boundary(bo, "apps/platform — Laravel 11") {
    Component(controllers, "Controllers", "PHP/Inertia", "OutletsController, ScrapeController, AlertsController")
    Component(jobs, "Jobs", "Laravel Queue", "ScrapingJob — dispatch en queue 'scraping'")
    Component(scheduler, "Scheduler", "Laravel schedule", "B11 alerts hourly")
    Component(eloquent, "Eloquent Models", "PHP", "Outlet, ScrapeSession, User")
    Component(inertia, "Inertia React Pages", "TSX + MUI", "Outlets CRUD, Run history, Live logs")
  }

  Rel(controllers, jobs, "dispatch")
  Rel(jobs, eloquent, "lee outlets")
  Rel(jobs, controllers, "ejecuta SCRAPING_COMMAND vía shell")
  Rel(eloquent, controllers, "renderiza páginas Inertia")
  Rel(scheduler, eloquent, "evalúa alertas")
```

El detalle de Backoffice se mantiene como deuda documental hasta v0+1 — ver
[components/backoffice.md](../components/backoffice.md) para la ficha de alto nivel.

## 4. Reader (apps/web) — Componentes (placeholder)

Reader aún no está scaffoldeado al cierre de este SAD. Diseño previsto:

| Componente | Tecnología | Rol |
|---|---|---|
| `/` (Home) | Next.js Server Component | Lista de eventos top (lee `/events` de Curator API) |
| `/event/[id]` | Server Component | Renderiza `PageV1`: headline, synthesis_md (mdx), evidence_rail, entities |
| Layout / Tema | Tailwind + tipografía propia | Brand voice — pendiente de lock |
| Auth gate v0 | Middleware password compartido | Single shared password (env) |
| Auth gate v1 | Magic link (Resend) | Post-MVP |
