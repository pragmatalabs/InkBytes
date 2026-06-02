# ADR-0002 — RabbitMQ as the event spine between Messor and the pipeline

* **Status**: Accepted
* **Date**: 2026-06-01
* **Deciders**: Julián de la Rosa

## Context

Messor must hand off scraped articles to the rest of the InkBytes pipeline
(Entopics → Synochi → Unitas) without coupling the harvester to downstream
implementations or release schedules. The downstream services need at-least-
once delivery, replay, and the ability to scale horizontally per stage.
Synchronous REST coupling would make the pipeline fail-closed: if Entopics is
down, scraping stalls.

## Decision

Use **RabbitMQ** as the asynchronous event bus between stages.

Concrete queues / exchanges (matches today's `env.yaml`):

| Exchange / Queue | Direction | Payload |
|---|---|---|
| Exchange `messor` | Messor → pipeline | Article events |
| Queue `articles-scraped` | Consumed by Entopics | One message per article |
| Queue `topics-extracted` | Entopics → Synochi | NER + topics |
| Exchange `hermes` | All services | Structured logs |

Conventions:

- Connection over **AMQPS** (`ssl.enabled: true`).
- **Confirm mode** on publishers — a publish is only considered durable after
  the broker acks.
- **Durable** exchanges and queues, **persistent** messages.
- Consumers use **manual ack** with prefetch tuned per service.
- A poison-message queue (`dead-letter`) collects messages that exceed retry
  caps.
- Heartbeat 600s; automatic reconnect with exponential backoff (already in
  `MessageService._check_connection_health`).
- Local **spool** (`data/rabbit/queue.json`) buffers events when the broker is
  unreachable; flushed on next successful connect.

## Consequences

**Positive**

- Stages are decoupled — Entopics can be redeployed without stopping Messor.
- Backpressure is visible (queue depth) and operable.
- Replay is possible by re-publishing from DO Spaces artifacts.

**Negative**

- Operational overhead: we own (or rent) a broker.
- Eventual consistency: end-to-end latency is broker- and consumer-bound.
- Requires discipline on schema evolution — see ADR-0005 (planned) for
  message schema versioning.

## Alternatives considered

- **HTTP fan-out** from Messor to each consumer — rejected: tight coupling,
  poor backpressure handling.
- **Kafka** — rejected for v1: heavier ops, the event volume doesn't justify
  it yet. Revisit at M3 (scale-out).
- **Redis Streams / NATS** — viable, but the codebase already invests in pika
  + a running RabbitMQ broker, and `hermes` log fan-out depends on it.

## Follow-ups

- Confirm publisher-confirm-mode is enabled end-to-end in `MessageService`
  (verify in code, otherwise patch).
- Document message schemas under `packages/contracts/events/`.
- Add a dead-letter queue and a redelivery dashboard.
