# Getting Started

> *Status: v1 · Owner: documentor-agent · Last updated: 2026-06-12*

Setup local del stack completo de InkBytes.

## Prerequisitos

| Herramienta | Versión | Para |
|---|---|---|
| Docker + Docker Compose | reciente | infraestructura (Postgres, RabbitMQ, MinIO) |
| Python | 3.11 (3.10–3.12 Messor) | Curator + Messor scraper |
| Node.js | 20+ | Reader (Next.js 16) |
| PHP | 8.4 + Composer | Backoffice Laravel |
| Ollama | con `bge-m3` | embeddings (`ollama pull bge-m3`, escucha en :11434) |

## Variables de entorno

Configurar en el shell del host (`~/.zshrc` en macOS) — nunca commitear:

```bash
export ANTHROPIC_API_KEY='sk-ant-...'   # LLM enrich + synthesize
export OPENAI_API_KEY='sk-...'          # fallback de embeddings/LLM
```

Postgres + RabbitMQ + MinIO ya traen defaults en `env.local.yaml`. Detalle completo en [configuration.md](../technical/configuration.md).

## Levantar todo (camino rápido)

```bash
cd /Volumes/Pragmata/Projects/InkBytes

# 1. Infraestructura
bash orchestrator/scripts/up.sh
#   → Postgres :5432, RabbitMQ :5672 (UI :15672), MinIO :9000 (consola :9001)

# 2. Pipeline completo como procesos de dev (necesita Ollama en :11434)
bash orchestrator/scripts/dev-pipeline.sh up
#   → Curator :8060 + Messor (--schedule) + Reader :3000 + Backoffice :8000

# 3. Verificar
bash orchestrator/scripts/dev-pipeline.sh status   # health + conteos del pipeline
bash orchestrator/scripts/dev-pipeline.sh logs     # tail de todos los logs
```

El script `dev-pipeline.sh` maneja dos gotchas: (1) fija cada app Python a **arm64** (los wheels nativos como `pydantic_core` son arm64-only; un arranque bajo Rosetta crashea al importar); (2) usa el `.venv` de cada app (el python de framework de macOS no trae `aio_pika`/`pika`/`newspaper`). El Backoffice corre `php artisan serve` (:8000) + vite y aplica migraciones pendientes.

Tear down:

```bash
bash orchestrator/scripts/down.sh         # conserva volúmenes
bash orchestrator/scripts/down.sh --nuke  # borra volúmenes también
```

> ⚠️ Nunca `docker compose down -v` ni `volume prune` sobre el stack de prod: borraría `inkbytes-messor-scrapes` (estado de dedup) y `inkbytes-postgres-data`. Ver [business-rules.md](../functional/business-rules.md) BR-MES-05.

## Correr un servicio aislado

| Servicio | Comando |
|---|---|
| Infra | `bash orchestrator/scripts/up.sh` |
| Curator (API + worker) | `cd Curator/apps/curator && python main.py --consume` |
| Messor harvester | `cd Messor/apps/scraper && python main.py env.yaml --scrape` |
| Reader | `cd Reader/apps/web && npm run dev` → localhost:3000 |
| Backoffice | `cd Messor/apps/platform && php artisan serve` |

### Modos útiles de Curator (`main.py`)

| Flag | Efecto |
|---|---|
| `--consume` | consume RabbitMQ + sirve API :8060 (dev/single-node) |
| `--worker` | consume sin puerto API (réplica escalable) |
| `--api-only` | solo la API + loop de refresh de config |
| `--fixture <path>` | procesa un evento JSON end-to-end |
| `--dry-run <path>` | ENRICH + embed sin BD |
| `--synthesize-pending` | sintetiza eventos con ≥2 fuentes sin página |
| `--reenrich-missing` / `--reenrich-stubs` | re-enriquece artículos |

### Modos de Messor (`main.py`)

`main.py env.yaml` + uno de: `--scrape [args]` (one-shot), `--schedule` (Docker continuo 4×/día), `--no-api` (coexistir con la API ya corriendo), `--client`.

## Verificar que funciona

```bash
curl http://localhost:8060/healthz      # Curator liveness → {ok:true}
curl http://localhost:8060/status       # conteos del pipeline
curl http://localhost:8050/             # Messor → {"message":"Hola Mundo"}
open http://localhost:3000              # Reader
open http://localhost:8000              # Backoffice (login Laravel Breeze)
open http://localhost:15672             # RabbitMQ UI (messor/messor)
```

Un pipeline sano: `/status` muestra `articles_total` creciendo, luego `events_total`, luego `pages_published`. Si `pages_published` queda en 0, revisar que haya eventos con ≥2 fuentes y que `processing_enabled=true`.
