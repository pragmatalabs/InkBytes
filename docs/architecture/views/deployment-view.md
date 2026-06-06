# Vista de Deployment — InkBytes v0

## Diagrama de Deployment

```mermaid
graph TB
  subgraph Internet["🌐 Internet"]
    Users["👥 Lectores pagos"]
    Operator["🛠️ Operador / Editor"]
  end

  subgraph DO["☁️ DigitalOcean — region nyc3"]
    subgraph Edge["🔒 Edge (LE-SSL)"]
      LB["nginx + Let's Encrypt<br/>inkbytes.app · admin.inkbytes.app"]
    end

    subgraph Droplet["💻 Droplet · basic-2gb · Docker Compose"]
      direction TB
      reader["reader<br/>Next.js · :3000"]
      backoffice["backoffice<br/>Laravel · :8080"]
      curator_api["curator-api<br/>FastAPI · :8060"]
      curator_worker["curator-worker<br/>--consume"]
      messor_api["messor-api<br/>FastAPI · :8050"]
      messor_worker["messor-worker<br/>--schedule | --no-api"]
      ollama["ollama<br/>bge-m3 · :11434"]
      qworker["queue-worker<br/>queue:work + schedule:work"]
    end

    subgraph Managed["🗄️ Managed / Externos en DO"]
      pg["DO Managed Postgres<br/>+ pgvector"]
      spaces["DO Spaces<br/>bucket: inkbytes"]
    end
  end

  subgraph External["🌐 Externos a DO"]
    rmq["RabbitMQ<br/>CloudAMQP / DO Managed Broker"]
    anthropic["Anthropic API<br/>Haiku 4.5"]
    openai["OpenAI API<br/>(fallback)"]
  end

  subgraph Obs["📊 Observabilidad"]
    logs["Better Stack / Axiom"]
    sentry["Sentry"]
  end

  Users -->|HTTPS 443| LB
  Operator -->|HTTPS 443| LB
  LB --> reader & backoffice

  reader --> curator_api
  backoffice --> messor_api
  backoffice --> qworker
  qworker --> messor_worker

  messor_worker --> spaces & rmq
  curator_worker --> rmq & ollama & anthropic & openai
  curator_worker --> pg
  curator_api --> pg
  messor_api --> pg

  Droplet -. logs/metrics .-> logs
  Droplet -. errors .-> sentry
```

## Inventario de nodos

| Nodo | Rol | Plataforma | CPU | RAM | Almacenamiento | Redundancia |
|---|---|---|---|---|---|---|
| `inkbytes-droplet` | App/Worker/Edge | DO basic-2gb (Ubuntu 24.04) | 2 vCPU | 2 GB | 60 GB SSD | 1 instancia (v0) |
| `inkbytes-db` | DB primaria | DO Managed Postgres (db-s-1vcpu-1gb) | 1 vCPU | 1 GB | 10 GB SSD + WAL | Daily backup |
| `inkbytes-spaces` | Object store | DO Spaces (S3) | — | — | 250 GB incluidos | 3-way geo-redundancy |
| `inkbytes-rmq` | Broker | CloudAMQP "Little Lemur" o DO Managed | — | — | — | Free tier o paid |

## Estrategia de red

| Zona | CIDR / Lugar | Componentes | Acceso entrada | Acceso salida |
|---|---|---|---|---|
| Internet | público | Usuarios | — | — |
| Edge | Droplet :443 | nginx + LE certs | Internet (TCP 443) | App tier (loopback) |
| App | loopback Droplet | reader, backoffice, curator-*, messor-* | Edge | DB, Spaces, RMQ, Anthropic, OpenAI |
| Data | DO VPC privado | DO Managed Postgres | App tier (DO VPC) | — |
| Bus | externo | RabbitMQ | App tier (AMQPS 5672) | — |
| Storage | público con keys | DO Spaces | App tier (HTTPS) | — |

**Firewall del Droplet (UFW):**
- IN: 22 (ssh, llaves), 80 (LE renew), 443 (HTTPS público)
- OUT: 443 (Anthropic, OpenAI, Spaces), 5672 (RabbitMQ AMQPS), 25060 (Postgres SSL), 53 (DNS)
- TODO lo demás: deny

## Resiliencia y disponibilidad

| Componente | SLA objetivo v0 | Estrategia | RTO | RPO |
|---|---|---|---|---|
| Reader / Curator API | 99.5% | Restart=always en Docker | < 5 min | 0 (lectura de DB) |
| Postgres | 99.9% (managed) | DO managed backups daily | < 1 h | < 24 h |
| RabbitMQ | 99.5% | Spool local en Messor cuando broker caído | < 30 min | < 1 ciclo (60 min) |
| Spaces | 99.99% (DO SLA) | Versionado + lifecycle 90 días | < 5 min | 0 |
| Anthropic | externo, depende del proveedor | Tenacity retries + stub fallback | — | — |
| Ollama (embeddings primario) | best-effort local | OpenAI como fallback | < 1 ciclo | 0 |

**Estado actual (gap vs. objetivo):** v0 corre en single Droplet sin HA. R-005 en risk register.

## Despliegue — flujo

```mermaid
sequenceDiagram
  participant Dev as Desarrollador
  participant GH as GitHub master
  participant Drop as Droplet
  participant DO as DO Spaces (artifacts)

  Dev->>GH: git push origin master
  GH->>GH: GitHub Actions: lint + test + docker build
  GH->>DO: push images to Container Registry
  GH->>Drop: ssh + docker compose pull && up -d
  Drop->>Drop: healthcheck /healthz para cada servicio
  Drop->>Dev: ping en Slack si falla
```

## Rollback

```bash
ssh ops@inkbytes-droplet
cd /opt/inkbytes
docker compose -f docker-compose.prod.yaml pull --policy missing
docker compose -f docker-compose.prod.yaml up -d --no-deps <service>=<previous-tag>
```

Sesiones en vuelo terminan; el siguiente ciclo usa la imagen anterior.

## Cost shape (mensual estimado)

| Item | Tier | USD |
|---|---|---|
| DO Droplet basic-2gb | 1 instancia | 24 |
| DO Managed Postgres (db-s-1vcpu-1gb) | shared | 15 |
| DO Spaces (250 GB) | base | 5 |
| CloudAMQP Little Lemur | free | 0 |
| LLM (Haiku) — 5k articles/day + 500 events/day | Anthropic | 75 |
| Embeddings — bge-m3 local | OpenAI fallback (raro) | ~1 |
| Sentry + Better Stack (free tiers) | — | 0 |
| Domain + LE SSL | — | 1 |
| **Total** | | **~120 USD/mes** |
