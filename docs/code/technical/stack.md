# Stack Tecnológico

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

InkBytes es un monorepo con cuatro aplicaciones desplegables y un kernel compartido. La frontera entre servicios es **JSON sobre RabbitMQ** (Messor → Curator) y **HTTP/REST** (Reader/Backoffice → Curator).

## Resumen por capa

| Capa | Tecnología | Versión | Servicio |
|---|---|---|---|
| Harvester | Python + FastAPI + newspaper3k | Py 3.10–3.12, FastAPI 0.99.1, newspaper3k 0.2.8 | Messor/scraper |
| Backoffice | Laravel + Inertia + React | Laravel 11, PHP 8.4, React | Messor/platform |
| Servicio LLM | Python + FastAPI + asyncpg | Py 3.11–3.12, Pydantic v2 | Curator |
| Frontend | Next.js (App Router) + React | Next 16.2.7, React 19.2.4, TS 5 | Reader |
| Base de datos | PostgreSQL + pgvector + pg_trgm | embeddings 1024-dim | compartida |
| Bus de eventos | RabbitMQ | topic exchanges | compartida |
| LLM (enrich + synth) | Anthropic Claude Haiku 4.5 | `claude-haiku-4-5` | Curator |
| Embeddings | Ollama `bge-m3` (1024-dim) | OpenAI-compatible `/v1` | Curator |
| Object store (prod) | DigitalOcean Spaces (S3) | bucket `inkbytes` | Messor/Curator |
| Object store (dev) | MinIO | docker-compose | local |

## Messor — Harvester (`Messor/apps/scraper/`)

- **Lenguaje/runtime:** Python `>=3.10,<3.13` (imagen Docker `python:3.11`). **Pydantic v1** (`>=1.10.14,<2`) — no actualizar hasta INK-Sprint-2.
- **Web/API:** `fastapi==0.99.1`, `uvicorn[standard]` (puerto 8050).
- **Scraping:** `newspaper3k==0.2.8`, `lxml_html_clean`, `beautifulsoup4`, `feedparser>=6.0.11` (RSS-first), `feedfinder2`, `tldextract`, `langdetect`, `nltk` (tokenizer `punkt`).
- **Mensajería:** `pika>=1.3.2` (cliente RabbitMQ síncrono).
- **Almacenamiento:** `boto3` (DigitalOcean Spaces, archival).
- **Otros:** `PyYAML`, `numpy`, `pandas`. Kernel compartido instalado editable: `-e ../../packages/inkbytes`.
- **Dockerfile:** 2 etapas (`python:3.11` builder → `python:3.11-slim` runner); hornea NLTK punkt; `EXPOSE 8050`; `CMD ["python","main.py","env.yaml","--schedule"]`.

## Messor — Backoffice (`Messor/apps/platform/`)

- **Framework:** Laravel 11 (estilo `bootstrap/app.php`), **PHP 8.4-fpm**.
- **Frontend:** Inertia.js + React (Vite), Material-UI.
- **Base de datos:** Postgres, base `inkbytes`, `search_path = backoffice,public`. Las tablas propias viven en el schema `backoffice`; las tablas del pipeline (`outlets`, `events`, `pages`, `articles`, `scrape_sessions`) las posee Curator en `public` (ADR-0003).
- **Control de Curator:** vía la **HTTP management API de RabbitMQ** (Guzzle/`Http`, sin paquete AMQP) y vía la tabla `backoffice.curator_settings`.
- **Observabilidad Docker:** lectura del socket Unix del daemon (`DockerRuntimeService`).
- **Dockerfile:** PHP 8.4-fpm + nginx + supervisord; `EXPOSE 80`.

## Curator — Servicio LLM (`Curator/apps/curator/`)

- **Lenguaje/runtime:** Python `>=3.11,<3.13`. **Pydantic v2** (`>=2.7.0,<3`) — no degradar.
- **LLM / structured output:** `anthropic>=0.40.0`, `openai>=1.50.0`, `instructor>=1.6.0` (salidas estructuradas tipadas). Proveedor por defecto: Anthropic (`claude-haiku-4-5`); alternativas DeepSeek/OpenAI.
- **Pipeline:** `aio-pika>=9.4.0` (consumidor async), `asyncpg>=0.29.0`, `pgvector>=0.3.0`, `boto3>=1.34.0`.
- **API:** `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `pydantic-settings>=2.5.0` (puerto 8060).
- **Media:** `scrapling[fetchers]>=0.2.9` (Playwright + Patchright Chromium para la galería de video).
- **Embeddings:** Ollama `bge-m3` 1024-dim por OpenAI-compatible `/v1` (fallback OpenAI `text-embedding-3-small`).
- **Utilidades:** `PyYAML`, `python-dotenv`, `tenacity>=8.5.0` (reintentos), `ulid-py>=1.1.0` (ids de evento), `structlog>=24.4.0`.
- **Dockerfile:** `python:3.11-slim` + libs de Chromium + `playwright install chromium` + `patchright install chromium` (path compartido `PLAYWRIGHT_BROWSERS_PATH`); corre como `USER 10001:10001`; HEALTHCHECK `/healthz`; `EXPOSE 8060`; `CMD python main.py --config env.yaml --consume`.

## Reader — Frontend (`Reader/apps/web/`)

- **Framework:** **Next.js 16.2.7 / React 19.2.4**, App Router, TypeScript 5.
- **Estilos:** Tailwind CSS v4 (`@tailwindcss/postcss`).
- **Sin librerías de datos ni de grafos:** el force-graph de entidades es SVG hecho a mano (simulación velocity-Verlet propia); el fondo animado usa un motor WebGL vendorizado (`@/lib/ink-shader`, "InkWall").
- **Build:** `next.config.ts` con `output: "standalone"`.
- **Dockerfile:** multi-stage `node:20-alpine`; copia `.next/standalone`; `ENV PORT=3000 HOSTNAME=0.0.0.0`; `EXPOSE 3000`; `CMD ["node","server.js"]`.

## Kernel compartido (`Messor/packages/inkbytes/`, `src/inkbytes/`)

Paquete Python compartido (pydantic v1) usado por Messor. Las nuevas adiciones de schema requieren un version bump del paquete (convención del repo).

## Decisiones de stack bloqueadas

| Decisión | Elección |
|---|---|
| LLM enrich + synthesize | Anthropic Claude Haiku 4.5 |
| Embeddings | Ollama `bge-m3` 1024-dim (fallback OpenAI) |
| Runtime de embeddings | Ollama (`/v1` OpenAI-compatible) |
| DB | Postgres + pgvector |
| Bus | RabbitMQ |
| Object store prod / dev | DO Spaces / MinIO |
| Pydantic | v1 en Messor, v2 en Curator (frontera = JSON RabbitMQ) |
| Deploy | Único Droplet DigitalOcean |
