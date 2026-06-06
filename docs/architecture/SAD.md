# Software Architecture Document
## InkBytes — v0 (MVP scope)

> **Estado**: En revisión
> **Fecha**: 2026-06-02
> **Arquitecto responsable**: Julián de la Rosa
> **Stakeholders**: Pragmata Labs, primeros usuarios pagos, equipo de ingeniería

---

## 1. Propósito y Alcance

**InkBytes** es un lector de noticias pago y libre de publicidad donde cada
evento noticioso se presenta como una **única página elegante** sintetizada
desde múltiples fuentes.

Este documento cubre la arquitectura **v0** (MVP que ship esta semana) —
un pipeline de tres servicios sobre un solo Droplet de DigitalOcean.
Quedan **fuera del alcance** de este SAD: la app móvil, la API pública
B2B, la separación post-v0 de Curator en Entopics/Synochi/Unitas, y la
internacionalización del Reader.

## 2. Contexto de Negocio

| Eje | Valor |
|---|---|
| Problema | El lector promedio tiene 12 pestañas abiertas sobre el mismo evento; los ad walls e infinite scroll hacen el consumo agotador. |
| Solución | Una página por evento, multi-fuente, con barra de evidencia y diversidad de fuentes visible. |
| Modelo | Suscripción pagada (~9 USD/mes), sin ads, sin tracking. |
| Vertical inicial | LATAM bilingüe (DR/MX/CO/AR) + EN business/tech. |
| Métricas norte | 100 usuarios pagos a 30 días post-launch; margen bruto ≥ 80%. |

## 3. Restricciones y Supuestos

| Tipo | Descripción |
|---|---|
| **Tiempo** | MVP en una semana (T-0 = 2026-06-07). |
| **Equipo** | 1–2 ingenieros + 1 PO. |
| **Plataforma** | Single DigitalOcean Droplet en v0. Sin Kubernetes. |
| **LLM** | Anthropic Claude Haiku 4.5 (ENRICH + SYNTHESIZE) — locked. |
| **Embeddings** | Ollama `bge-m3` local (1024-dim), OpenAI `text-embedding-3-small` como fallback — ADR-0003 (Curator). |
| **Persistencia** | Postgres + pgvector (managed DO), DigitalOcean Spaces para artefactos. |
| **Event bus** | RabbitMQ (CloudAMQP o DO managed). |
| **Boundary Pydantic** | v1 en Messor, v2 en Curator; la frontera es el JSON sobre RabbitMQ. |
| **Admin único** | Laravel Backoffice (`apps/platform`). El cliente React legado fue retirado en B12.3 — ADR-0001. |
| **Compliance** | No procesamos PII en el pipeline; snippet-only display por restricciones de licencia de outlets. |

## 4. Vistas de Arquitectura

- [Vista de Contexto](views/context-view.md) — C4 L1
- [Vista de Contenedores](views/container-view.md) — C4 L2
- [Vista de Componentes](views/component-view.md) — C4 L3 por servicio
- [Vista de Deployment](views/deployment-view.md) — Droplet + redes + zonas
- [Mapa de Integraciones](views/integration-map.md) — Interfaces externas
- [Arquitectura de Datos](views/data-architecture.md) — Modelo + flujos
- [Vista de Seguridad](views/security-view.md) — STRIDE + AAA + zonas de confianza

## 5. Atributos de Calidad

Ver [quality/quality-attributes.md](quality/quality-attributes.md). Resumen:

| NFR | Objetivo v0 |
|---|---|
| Uptime Reader | ≥ 99.5% (single Droplet) |
| Ciclo de cosecha | Cada 60 min, jitter < 5 min |
| Latencia publicación | < 15 min desde fuente hasta one-pager visible |
| Latencia render Reader p95 | < 1.5 s (cache cálido) |
| Costo OPEX | ≤ $125 USD/mes a 5k artículos/día |
| Cobertura de tests Curator | ≥ 60% en líneas (Sprint-2 ≥ 80%) |

## 6. Decisiones Arquitectónicas

Ver [decisions/ADR-index.md](decisions/ADR-index.md). Decisiones clave consolidadas:

| ADR | Decisión | Servicio |
|---|---|---|
| Messor ADR-0001 | Monorepo migration (apps/, packages/, infra/, docs/) | Messor |
| Messor ADR-0002 | RabbitMQ como spine de eventos | Messor |
| Messor ADR-0003 | DigitalOcean Spaces como artifact store | Messor |
| Messor ADR-0004 | Retirar namespace `hermes` → `messor.logs` | Messor |
| Messor ADR-0005 | Split Messor (harvester) ↔ Curator (LLM pipeline) | Messor |
| Curator ADR-0001 | Curator colapsa Entopics + Synochi + Unitas en v0 | Curator |
| Curator ADR-0003 | Ollama `bge-m3` local para embeddings (1024-dim); OpenAI como fallback | Curator |
| Platform ADR-0001 | "One admin" — Laravel Backoffice retira el cliente React | Platform |
| Platform ADR-0006 | Persistir `scrape.session.completed` en `public.scrape_sessions` | Curator |
| Platform ADR-0007 | `packages/inkbytes` con código self-contained (sin symlinks) | Messor |

## 7. Riesgos

Ver [quality/risk-register.md](quality/risk-register.md). Top-3:

| ID | Riesgo | Severidad |
|---|---|---|
| R-001 | LLM alucina hechos en SYNTHESIZE | Alta |
| R-005 | Single Droplet = single point of failure | Alta |
| R-009 | Secretos previamente filtrados (env.yaml legacy) sin rotar y sin scrub de historia | Crítica |

## 8. Glosario

| Término | Definición |
|---|---|
| **Evento (en producto)** | Unidad atómica de lectura — un newsworthy thing cubierto por múltiples fuentes. Distinto del término técnico "evento RabbitMQ". |
| **One-pager** | Página única consolidada por evento; salida final de SYNTHESIZE. |
| **Skill** | Una capacidad de Curator (ENRICH / CLUSTER / SYNTHESIZE). |
| **Outlet** | Fuente de noticias (BBC, Reuters, Diario Libre…). |
| **Session** | Un ciclo de scraping de Messor; rastreado en `scrape_sessions`. |
| **Backoffice** | Laravel admin en `apps/platform` (sucesor del cliente React). |
| **Curator** | Pipeline LLM que reemplaza Entopics+Synochi+Unitas en v0. |
| **inkbytes.article.v1** | Schema del evento Messor→Curator. |
