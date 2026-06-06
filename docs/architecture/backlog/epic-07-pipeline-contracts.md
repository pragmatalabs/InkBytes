# Epic 07 — Pipeline Contracts

> *Freeze the JSON contracts between services so the team can refactor either side without breaking the other.*

Risk-links: prevents future R-* · Sprints: 2 & 3 · Total: 9 pts

---

## IB-45 · Lock `inkbytes.article.v1` schema in `packages/contracts/`

**As** a service, **I want** to depend on a versioned, validated schema for the Messor→Curator event, **so that** breaking changes are explicit and discoverable.

### Acceptance criteria

```gherkin
Given the Messor→Curator event is documented in Messor/docs/contracts.md
When I create packages/contracts/events/article-v1.json (JSON Schema)
And Pydantic models in packages/contracts/events_v1.py
Then every event published by Messor is validated against the schema before send
And invalid events are dropped + logged (not crashed-on)
And both Messor (v1 wrapper) and Curator (v2 native) import the same contract
```

### Notes

- JSON Schema is the source of truth; Pydantic is generated.
- Round-trip test: Messor publishes, Curator consumes, equality preserved.
- Was Sprint-1 INK-7 — finishing here.

**Sprint**: 2 · **Points**: 3 · **Was**: INK-7 · **Priority**: P0

---

## IB-46 · Lock `inkbytes.session.v1` schema

**As** the Backoffice, **I want** the `scrape.session.completed` event to follow a stable schema, **so that** the run-history page doesn't break when Messor changes internals.

### Acceptance criteria

```gherkin
Given Messor emits scrape.session.completed at end of each cycle
When the event schema is documented in Messor/docs/contracts.md §3
And persisted via JSON Schema in packages/contracts/events/session-v1.json
Then Curator validates and persists into public.scrape_sessions
And the Backoffice run-history page reads from that table
And schema evolution follows the v2 parallel-cola pattern
```

### Notes

- ADR PLT-0006 already references this — formalize now.
- Pair with IB-45 (same package).

**Sprint**: 3 · **Points**: 2 · **Risk**: R-010 follow-up · **Priority**: P1

---

## IB-47 · Lock `PageV1` contract for Reader consumption

**As** the Reader, **I want** the page JSON returned by Curator API to follow a stable contract, **so that** the Next.js render code is buildable independent of Curator changes.

### Acceptance criteria

```gherkin
Given Curator's GET /events/{id} returns a page row
When the OpenAPI spec for that endpoint is published in Curator/docs/openapi.yaml
And PageV1 is referenced in packages/contracts/page-v1.json
Then Reader's TypeScript types are generated from the OpenAPI spec
And a Reader e2e test asserts the contract via Pact or schemathesis
```

### Notes

- Generates TS types via `openapi-typescript`.
- Defensive on the Reader side: render gracefully when optional fields are missing.

**Sprint**: 3 · **Points**: 2 · **Priority**: P1

---

## IB-48 · Schema evolution protocol document

**As** the team, **I want** a documented protocol for "how to change a contract schema without breaking consumers", **so that** every schema change follows the same pattern.

### Acceptance criteria

```gherkin
Given an ADR exists at docs/architecture/decisions/PLT-0011-schema-evolution.md
When a contract field is added/removed/renamed
Then the protocol document specifies:
  - additive change → optional field, same version
  - breaking change → bump major version, parallel queue, dual-consume window 30d
  - deprecation → mark in JSON Schema, monitor consumers, then remove
And consumers can find a state-of-schema dashboard
```

### Notes

- Inspired by Kafka SR / Buf BSR patterns.
- Pure docs work but sets the precedent for the rest of the org.

**Sprint**: 3 · **Points**: 2 · **Priority**: P2
