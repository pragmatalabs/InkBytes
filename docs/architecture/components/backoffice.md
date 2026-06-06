# Componente: Backoffice — Laravel Admin

## Identificación

| Atributo | Valor |
|---|---|
| **Nombre** | Backoffice (`Messor/apps/platform`) |
| **Tipo** | Web app (admin) |
| **Versión** | B12.3+ |
| **Equipo dueño** | Platform |
| **Repositorio** | `pragmatalabs/InkBytes` (subdir `Messor/apps/platform/`) |
| **Estado** | Activo — admin único tras retiro del cliente React (ADR-0001 "one admin") |

## Propósito

Admin interno para curar outlets, disparar ciclos de scraping, ver
historial de sesiones, y recibir alertas operacionales (B11).
Sucesor del cliente React de Messor (retirado en B12.3).

## Responsabilidades

- Outlets CRUD — alta/baja/edición de fuentes.
- Disparar ciclos de scraping vía `▶ Iniciar Scraping`.
- Mostrar historial de `scrape_sessions` (de Postgres, ADR-0006).
- Live logs durante un ciclo.
- Alertas B11 (latencia de ciclos, errores, salud de outlets).
- Auth + autorización para operadores.

## NO es responsabilidad de este componente

- Renderizar el Reader público (Reader Next.js).
- Lógica de scraping (Messor).
- Lógica LLM (Curator).
- Billing usuarios pagos (post-v0).

## Interfaces

### Expone (produce)

| Interface | Tipo | Descripción |
|---|---|---|
| `/login` `/logout` | HTTP | Laravel auth |
| `/outlets` | HTTP / Inertia | CRUD de outlets |
| `/scrape/trigger` | HTTP (POST) | Encola job en queue `scraping` |
| `/scrape/history` | HTTP | Lee `scrape_sessions` de Postgres |
| `/alerts` | HTTP | B11 alerts dashboard |
| Laravel queue `scraping` | DB-backed | Jobs ScrapingJob |
| Cron entries via `schedule:work` | DB-backed | Tareas programadas (alertas) |

### Consume (depende de)

| Dependencia | Tipo | Uso |
|---|---|---|
| Postgres | Eloquent | Users, outlets, scrape_sessions, alerts |
| Messor API (`:8050`) | HTTP/JSON | Lectura adicional de sesiones (`/api/scrapesessions`) |
| Filesystem (`data/outlets/outlets.json`) | shared | Sincroniza con Messor |
| Shell exec | Shell | Lanza `messor-worker` con `--no-api` + `SCRAPING_COMMAND` |

## Tecnología

| Componente | Tecnología | Versión |
|---|---|---|
| Runtime | PHP | 8.3 |
| Framework | Laravel | 11 |
| Front (admin) | Inertia + React + Material UI | — |
| DB | Postgres (compartido) | 16 |
| Auth | Laravel Sanctum / built-in | — |

## Procesos de fondo requeridos

Para que el botón "▶ Iniciar Scraping" funcione, el Droplet necesita **dos procesos
adicionales corriendo en paralelo**:

```bash
php artisan queue:work --queue=scraping --timeout=0   # ejecuta ScrapingJob
php artisan schedule:work                              # alertas B11
```

Ambos deben estar como servicios Docker o `systemd` en producción. Si fallan, las
sesiones quedan encoladas para siempre. Ver `Messor/docs/STATUS.md` §"Backoffice
background processes".

## Atributos de calidad

| Atributo | Objetivo v0 | Medición |
|---|---|---|
| Disponibilidad | 99.0% (admin tier) | Docker healthcheck |
| Latencia render p95 | < 800 ms | Laravel Telescope (dev) / APM |
| Latencia dispatch → run | < 30 s | Logs de queue worker |
| Cobertura tests | ≥ 50% (Sprint-2 ≥ 70%) | phpunit |

## Pendientes / deuda documental

- Documentación formal de tablas Eloquent (Users, Outlets, ScrapeSessions) — incluir en `docs/architecture/views/data-architecture.md` con dueño.
- ADR formal para "queue workers como servicios docker" (hoy implícito).
