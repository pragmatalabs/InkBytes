# Architecture Decision Records — Índice

> Los ADRs viven dentro de cada servicio (`Messor/docs/adr/`,
> `Curator/docs/adr/`). Este índice los lista en un solo lugar para
> visibilidad cross-service.

## Convenciones

- Numeración **por servicio** (cada servicio tiene su propia secuencia).
- Estados: **Propuesto** · **Aceptado** · **Reemplazado** · **Deprecado**.
- Nunca se eliminan; los reemplazados se marcan como tal con link al sucesor.

## Messor

| ADR | Título | Estado | Fecha | Doc |
|---|---|---|---|---|
| MSR-0001 | Monorepo migration | Aceptado | 2026-04 | [`Messor/docs/adr/0001-monorepo-migration.md`](../../Messor/docs/adr/0001-monorepo-migration.md) |
| MSR-0002 | RabbitMQ as event spine | Aceptado | 2026-06-01 | [`Messor/docs/adr/0002-rabbitmq-events.md`](../../Messor/docs/adr/0002-rabbitmq-events.md) |
| MSR-0003 | DO Spaces as artifact store | Aceptado | 2026-06-01 | [`Messor/docs/adr/0003-do-spaces-artifact-store.md`](../../Messor/docs/adr/0003-do-spaces-artifact-store.md) |
| MSR-0004 | Retire `hermes` namespace → `messor.logs` | Aceptado | 2026-06-02 | [`Messor/docs/adr/0004-retire-hermes-namespace.md`](../../Messor/docs/adr/0004-retire-hermes-namespace.md) |
| MSR-0005 | Messor ↔ Curator responsibility split | Aceptado | 2026-06-02 | [`Messor/docs/adr/0005-messor-curator-responsibility-split.md`](../../Messor/docs/adr/0005-messor-curator-responsibility-split.md) |

## Curator

| ADR | Título | Estado | Fecha | Doc |
|---|---|---|---|---|
| CUR-0001 | Curator collapses Entopics + Synochi + Unitas in v0 | Aceptado | 2026-06-02 | [`Curator/docs/adr/0001-curator-collapses-pipeline.md`](../../Curator/docs/adr/0001-curator-collapses-pipeline.md) |
| CUR-0003 | Ollama `bge-m3` (1024-dim) as primary embeddings; OpenAI fallback | Aceptado | 2026-06-02 | _pendiente de archivar formalmente en `Curator/docs/adr/0003-…`_ |

## Platform (Backoffice)

| ADR | Título | Estado | Fecha | Doc |
|---|---|---|---|---|
| PLT-0001 | "One admin" — Laravel Backoffice retira el cliente React | Aceptado | B12.3 | _en `Messor/apps/platform/docs/adr/`_ |
| PLT-0006 | `scrape.session.completed` persistido en `public.scrape_sessions` | Aceptado | B11 | _en `Messor/apps/platform/docs/adr/`_ |
| PLT-0007 | `packages/inkbytes` con código self-contained (sin symlinks) | Aceptado | post-INK-1 | _en `Messor/docs/adr/`_ |

## ADRs propuestos / pendientes de redacción formal

| Tema | Justificación | Owner |
|---|---|---|
| ADR Curator-0002 — Pydantic v2 boundary | Pydantic v2 en Curator vs v1 en Messor — la frontera explícita es el JSON RabbitMQ | Pipeline |
| ADR Platform-0008 — Queue workers como servicios docker permanentes | Hoy implícito; afecta operabilidad | Platform |
| ADR Curator-0004 — Cost guard per cycle | Cuando LLM cost > $5/ciclo, abrir circuit breaker | Pipeline |
| ADR Reader-0001 — Brand voice + tipografía | Locks el prompt de SYNTHESIZE | Front + Owner |
| ADR Platform-0009 — Reset pgvector a 1024 dims | Cambio de OpenAI 1536 → bge-m3 1024; requiere migration | Pipeline |
| ADR Platform-0010 — Schema migrations runner | Reemplazar el `_ensure_schema` mágico por sqitch / asyncpg-migrate | Platform |

## Cómo proponer un ADR

1. Crear archivo `{NN}-{titulo-en-kebab}.md` en el `docs/adr/` del servicio que lo decide.
2. Usar el template (ver cualquier ADR existente).
3. Estado inicial: **Propuesto**.
4. Listarlo en este índice + en el `Sources` del SAD.
5. Tras review de arquitectura → cambiar a **Aceptado** (o **Rechazado** con razón).
