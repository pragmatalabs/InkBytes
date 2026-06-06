# Vista de Contexto — InkBytes (C4 L1)

## Descripción

InkBytes ingiere noticias de outlets curados, las enriquece con un LLM,
las clusteriza por evento, y publica una página por evento al lector
pagado. Un administrador interno cura outlets y dispara ciclos.

## Diagrama C4 — Nivel 1: Contexto

```mermaid
C4Context
  title Contexto del Sistema — InkBytes v0

  Person(reader, "Lector pago", "Consume one-pagers por evento")
  Person(admin, "Operador / Editor", "Cura outlets, dispara y monitorea ciclos")

  System(inkbytes, "InkBytes", "Plataforma de news aggregation con IA — colecta, enriquece, sintetiza")

  System_Ext(outlets, "Outlets de Noticias", "BBC, Reuters, Listín Diario, El Universal, etc. — RSS y HTML")
  System_Ext(anthropic, "Anthropic API", "Claude Haiku 4.5 — ENRICH y SYNTHESIZE")
  System_Ext(openai, "OpenAI API", "Embeddings fallback (text-embedding-3-small)")
  System_Ext(do, "DigitalOcean", "Compute (Droplet) + Spaces (S3) + Managed Postgres")
  System_Ext(rmq, "Broker RabbitMQ", "Eventos entre stages — CloudAMQP o DO managed")
  System_Ext(stripe, "Stripe", "Billing (post-v0)")

  Rel(reader, inkbytes, "Lee one-pagers", "HTTPS")
  Rel(admin, inkbytes, "Cura outlets, dispara ciclos", "HTTPS (Backoffice)")
  Rel(inkbytes, outlets, "Cosecha artículos", "HTTPS / RSS")
  Rel(inkbytes, anthropic, "Enriquece + sintetiza", "HTTPS")
  Rel(inkbytes, openai, "Embeddings (fallback)", "HTTPS")
  Rel(inkbytes, do, "Compute + storage", "TCP / HTTPS")
  Rel(inkbytes, rmq, "Pub/sub de eventos", "AMQPS")
  Rel(reader, stripe, "Pago de suscripción (post-v0)", "HTTPS")
```

## Actores y sistemas externos

| Actor / Sistema | Tipo | Relación | Protocolo/Canal |
|---|---|---|---|
| Lector pago | Usuario externo | Consume el Reader | HTTPS |
| Operador / Editor | Usuario interno | Usa Backoffice (Laravel) | HTTPS |
| Outlets de Noticias | Sistemas externos públicos | Provee HTML/RSS | HTTPS |
| Anthropic | Servicio externo (SaaS) | LLM (Haiku 4.5) | HTTPS / REST |
| OpenAI | Servicio externo (SaaS, fallback) | Embeddings | HTTPS / REST |
| Ollama local | Servicio local (Droplet) | Embeddings (primario) | HTTP (`/v1` OpenAI-compatible) |
| DigitalOcean Spaces | Storage (cloud) | Artefactos | HTTPS (S3) |
| DigitalOcean Managed Postgres | DB (cloud) | System of record | TCP/SSL |
| Broker RabbitMQ | Mensajería (externa o managed) | Event spine | AMQPS |
| Stripe | Billing (post-v0) | Suscripciones | HTTPS |

## Fronteras del sistema

**Dentro del alcance v0:**
- Cosecha (Messor), pipeline LLM (Curator), Reader (Next.js), Backoffice (Laravel)
- Persistencia en Postgres + pgvector
- Artefactos en DO Spaces (o MinIO en dev)
- Event spine RabbitMQ entre Messor y Curator
- Admin (operador interno) en Backoffice

**Fuera del alcance v0:**
- App móvil nativa
- API pública B2B
- Internacionalización del Reader (i18n)
- Pagos en producción (Stripe) — se pospone post-MVP, contraseña compartida en v0
- Separación de Curator en tres servicios (Entopics / Synochi / Unitas) — post-MVP
- Indicadores de bias por outlet (left/center/right) — post-MVP
- Notificaciones / digest por email — post-MVP
