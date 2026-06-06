# Atributos de Calidad — InkBytes v0

## Disponibilidad

| Componente | SLA objetivo | Estrategia | Monitoreo |
|---|---|---|---|
| Reader (Next.js) | 99.5% | Docker restart=always + healthcheck `/_health` | Better Stack uptime |
| Curator API | 99.5% | Idem + `/healthz` + `/readyz` | Idem |
| Messor harvester | 99.5% (cosecha; OK saltar un ciclo) | Restart=always + lock anti-overlap | Lag de último ciclo |
| Backoffice | 99.0% (admin tier; tolerante a fallo) | Restart=always | Healthcheck Laravel |
| Postgres | 99.9% (DO managed) | DO managed backups daily | DO panel |
| RabbitMQ | 99.5% (CloudAMQP free tier) | Spool local en Messor cuando broker caído | UI CloudAMQP |
| Anthropic | dependiente del proveedor | Tenacity retries + stub fallback | Logs + alert si error rate > 5% |
| Ollama (embeddings) | best-effort local | Si cae, fallback a OpenAI | Healthcheck loopback |

**SLA compuesto del producto (Reader visible)**: ~99.0% v0. Para 99.9% hay que duplicar el Droplet + LB (post-v0).

## Performance

| Operación | P50 objetivo | P99 objetivo | Método de medición |
|---|---|---|---|
| `GET /` (Reader home) | < 400 ms | < 1.5 s | Vercel Insights / RUM |
| `GET /event/[id]` | < 500 ms | < 1.8 s | Idem |
| Curator API `GET /events` | < 50 ms | < 200 ms | uvicorn metrics + APM |
| Curator API `GET /events/{id}` | < 30 ms | < 150 ms | Idem |
| ENRICH (Haiku call) | 1.5 s | 5 s | Anthropic response_time header |
| Embedding (bge-m3 local) | 80 ms | 250 ms | Ollama logs |
| SYNTHESIZE (Haiku call) | 4 s | 12 s | Idem |
| Ciclo de scraping completo | 2 min | 8 min | Analytics service |

## Escalabilidad

- **Horizontal Reader**: trivial (stateless); duplicar Droplet + LB cuando RPS > 50.
- **Horizontal Curator**: limitado por `max_concurrent_articles`. Para escalar, separar Curator en 3 servicios (post-v0, ADR Curator-0001 reversal path).
- **Horizontal Messor**: shardable por outlet group (post-v0).
- **Vertical**: en v0 el Droplet basic-2gb cubre hasta ~10k artículos/día + ~500 events/día. Escalar a basic-4gb si saturamos CPU.
- **Datos**: Postgres maneja ~1M artículos sin tuning. Más allá → particionar `articles` por `scraped_at`.
- **pgvector IVFFlat**: `lists=100` es razonable para hasta ~100k vectores. Recalcular `lists ≈ √rows` periódicamente.

## Seguridad

- Estándares aplicables: ISO 27001 lite (sin certificación v0), DR Ley 172-13 (al entrar usuarios).
- Cifrado en tránsito: TLS 1.3 en todos los entrypoints públicos; AMQPS en bus.
- Cifrado en reposo: DO Managed Postgres (AES-256 at-rest); DO Spaces (SSE-S3 por defecto).
- Penetration testing: pendiente — programar uno antes del primer usuario pago.

## Mantenibilidad

| Métrica | Objetivo |
|---|---|
| Cobertura de tests Curator | ≥ 60% líneas en v0; ≥ 80% en Sprint-2 |
| Cobertura de tests Messor | ≥ 50% en v0; ≥ 75% en Sprint-2 |
| Deuda técnica explícita en backlog | < 30% del sprint (capacity) |
| Tiempo de onboarding de un dev nuevo | < 1 día (con CLAUDE.md + dev-handoff.md) |
| Tiempo de PR mediano | < 24 h |
| Linting | ruff (Python) + ESLint (TS/JS) + Pint (PHP) — todos en CI |

## Observabilidad

| Pilar | Herramienta v0 | Retención | Alertas |
|---|---|---|---|
| Logs estructurados | stdout → Better Stack / Axiom (free tier) | 7 días | Sí (error rate) |
| Métricas | Pendiente — Prometheus + Grafana (Sprint-2) | — | — |
| Trazas | Pendiente — OpenTelemetry → Tempo (Sprint-2) | — | — |
| Uptime | Better Stack monitors | 30 días | Sí (Slack webhook) |
| Errors | Sentry (free tier) | 30 días | Sí (Slack) |
| Costos LLM | Manual via Anthropic dashboard semanal | — | Pendiente — cost guard ADR Curator-0004 |

## Capacidad

| Recurso | Headroom v0 | Notas |
|---|---|---|
| Droplet 2 GB RAM | ~70% libre con stack completo + Ollama bge-m3 (modelo ~700MB en RAM) | Si saturamos, mover Ollama a un Droplet aparte |
| Droplet 2 vCPU | ENRICH es IO-bound (Anthropic), CPU ocioso | Sin bottleneck previsto |
| Postgres 1 GB | 250k filas `articles` sin tuning | Crece a ~5 GB en 6 meses; subir a basic-2 antes |
| DO Spaces 250 GB | ~30 días de raw HTML retention | Lifecycle policy reduce footprint a estado estacionario ~50 GB |
| RabbitMQ free tier | 1M mensajes/mes; ~30k/día — suficiente | Si superamos, pasar a paid tier o DO managed |

## Roadmap de calidad post-v0

| Sprint | Item | Justificación |
|---|---|---|
| Sprint-2 | OpenTelemetry tracing | Necesario al separar Curator en 3 servicios |
| Sprint-2 | Prometheus metrics endpoints | Visibilidad de costos LLM, latencias por skill |
| Sprint-2 | k6 / Artillery load tests | Validar p99 con carga real |
| Sprint-3 | Penetration test externo | Antes de cobrar a > 50 usuarios |
| Sprint-3 | Compliance docs (DR 172-13 + privacy policy) | Idem |
