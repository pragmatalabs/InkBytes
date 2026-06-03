# ADR-0004 — Retire the `hermes` namespace; unify under `messor`

* **Status**: Accepted
* **Date**: 2026-06-02
* **Deciders**: Julián de la Rosa
* **Relates to**: ADR-0002 (RabbitMQ event spine), ADR-0003 (DO Spaces artifact store), v1-scope §2

## Context

Historically the InkBytes pipeline used two distinct names on the message
bus and the object store:

- `messor` — for the scraping/event stream produced by the harvester
- `hermes` — for the cross-service log fan-out (and the NestJS gateway
  service that consumed those logs)

[v1-scope](../v1-scope.md) deferred the `hermes` NestJS gateway out of
scope (along with `mefisto` and `walkway`). With no consumer service named
`hermes`, the lingering RabbitMQ exchange `hermes` and DO Spaces folder
`hermes/` are just confusing aliases for "Messor's log channel".

Keeping the `hermes` name implies a separate subsystem that no longer
exists in v1.

## Decision

Retire the `hermes` namespace. Everything Messor produces lives under the
`messor` namespace, with two streams distinguished by a dotted suffix:

| Stream | RabbitMQ exchange | RabbitMQ queue(s) | DO Spaces prefix |
|---|---|---|---|
| Events (article-scraped, etc.) | `messor` | `messor`, `articles-scraped`, `topics-extracted` | `s3://inkbytes/messor/` |
| Logs (structured app logs) | `messor.logs` | `messor.logs` | `s3://inkbytes/messor/logs/` |

Both exchanges are **topic** exchanges; routing keys further classify the
message (e.g. `events.article.scraped`, `logs.error`).

## Concrete renames

| Was | Is |
|---|---|
| RabbitMQ exchange `hermes` | RabbitMQ exchange `messor.logs` |
| RabbitMQ exchange `hermes_exchange` | RabbitMQ exchange `messor.logs` |
| RabbitMQ queue `hermes` | RabbitMQ queue `messor.logs` |
| Routing key `mainHermes.hermes` | Routing key `messor.logs` |
| `logging.exchange_name: hermes` | `logging.exchange_name: messor.logs` |
| `digitalocean.spaces.buckets.main.folders.logs: hermes` | `digitalocean.spaces.buckets.main.folders.logs: messor/logs` |

Applied in `apps/scraper/env.yaml`, `env.example.yaml`, `env.local.yaml`,
and all references in `docs/`.

## Consequences

**Positive**

- One namespace per producer service. Less mental overhead for ops.
- Easier IAM scoping in DO Spaces — one prefix per producer.
- Aligns with v1's "remove complexity from scope" principle.
- Routing-key-based filtering is more flexible than separate exchanges.

**Negative**

- One-time operational migration on the existing RabbitMQ broker:
  declare `messor.logs` exchange + queue, bind, drain `hermes`, delete
  `hermes`. Plan a maintenance window.
- Any external consumer still bound to `hermes` will silently stop
  receiving logs until rebound to `messor.logs`.
- DO Spaces objects under the legacy `hermes/` prefix remain until
  lifecycle policy or manual archival moves them under `messor/logs/`.

## Migration plan

1. Land this config change in `master` (no consumers in scope today, so
   no breaking change for v1).
2. On the broker:
   ```bash
   rabbitmqadmin declare exchange name=messor.logs type=topic durable=true
   rabbitmqadmin declare queue    name=messor.logs durable=true
   rabbitmqadmin declare binding  source=messor.logs destination=messor.logs routing_key=#
   # drain & delete legacy
   rabbitmqadmin delete queue    name=hermes
   rabbitmqadmin delete exchange name=hermes
   ```
3. In DO Spaces, optionally copy existing log objects:
   ```bash
   aws s3 sync s3://inkbytes/hermes/ s3://inkbytes/messor/logs/ \
     --endpoint-url https://nyc3.digitaloceanspaces.com
   aws s3 rm s3://inkbytes/hermes/ --recursive --endpoint-url ...
   ```
4. Update any external log shipper (Better Stack / Axiom) to bind to
   `messor.logs`.

## Alternatives considered

- **Keep `hermes`** — rejected: the name implies a separate service that
  v1 doesn't have.
- **Collapse to a single `messor` exchange for everything** — rejected:
  events and logs have different retention, fan-out, and consumer
  patterns; keeping them as sibling exchanges (`messor` + `messor.logs`)
  preserves operational clarity at no extra cost.
- **Rename to `inkbytes.logs`** — rejected: would imply a shared
  log channel for multiple producer services. v1 has one producer
  (Messor). When/if Entopics/Synochi/Unitas reach production, each gets
  its own `<service>.logs` exchange following the same pattern.

## Follow-ups

- Update the broker setup script (when written) to declare the new
  exchanges.
- ADR-0005 (future) — define the topic routing-key taxonomy under each
  exchange (`events.article.scraped`, `events.outlet.healthcheck`,
  `logs.error`, etc.).
