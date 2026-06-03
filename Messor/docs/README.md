# Messor — Documentation

> *Messor is the 24/7 harvester agent of the InkBytes news platform.
> This directory is the single source of truth for how it works, how to run it,
> and how to evolve it.*

## 🧭 Start here

| If you are… | Read |
|---|---|
| A product/business reader | [product-vision.md](./product-vision.md) |
| A new engineer | [architecture.md](./architecture.md) → [development.md](./development.md) |
| Setting up locally | [installation.md](./installation.md) → [configuration.md](./configuration.md) |
| Deploying to production | [deployment-digitalocean.md](./deployment-digitalocean.md) → [security.md](./security.md) |
| Operating in production | [operations.md](./operations.md) |
| Looking for design decisions | [adr/](./adr/) |

## 📚 Index

### Product

- [Product Vision](./product-vision.md) — what InkBytes is, why Messor exists, KPIs

### Engineering

- [Architecture](./architecture.md) — C4 context/container/component + agent loop + SoC matrix
- [Configuration Reference](./configuration.md) — every `env.yaml` field, env-var overrides
- [API Reference](./api-reference.md) — FastAPI endpoints
- [Development Guide](./development.md) — local setup, code style, contributing
- [Code Documentation Standards](./code-documentation-standards.md)
- [Docstring Templates](./docstring-templates.md)
- [Components](./components/) — per-component deep-dives

### Operations

- [Dev Bring-Up Handoff](./dev-handoff.md) — ticketed plan to bring Messor up locally end-to-end
- [Operations Runbook](./operations.md) — 24/7 daily/weekly checks, alerts, incident playbook
- [Security & Secrets](./security.md) — ⚠️ includes immediate rotation actions
- [DigitalOcean Deployment](./deployment-digitalocean.md) — App Platform / Droplet topologies, CI/CD

### Reference

- [Installation](./installation.md)
- [User Guide](./user-guide.md)
- [Output Contract](./contracts.md) — what Messor produces; what Curator can rely on
- [Decision Records (ADRs)](./adr/)
  - [ADR-0001 — Monorepo migration](./adr/0001-monorepo-migration.md)
  - [ADR-0002 — RabbitMQ event spine](./adr/0002-rabbitmq-events.md)
  - [ADR-0003 — DO Spaces artifact store](./adr/0003-do-spaces-artifact-store.md)
  - [ADR-0004 — Retire `hermes` namespace](./adr/0004-retire-hermes-namespace.md)
  - [ADR-0005 — Messor ↔ Curator responsibility split](./adr/0005-messor-curator-responsibility-split.md)
  - [ADR-0006 — Inline per-article events; S3 becomes archival-only](./adr/0006-inline-events-s3-archival-only.md)

## 🎯 Documentation standards

- **Format**: Markdown, GitHub-flavored.
- **Diagrams**: ASCII inside Markdown for portability; Mermaid only where
  rendered.
- **Code docs**: Google-style Python docstrings; TypeScript via JSDoc/TSDoc.
- **API specs**: OpenAPI 3.0 generated from FastAPI.
- **Decisions**: One ADR per non-trivial decision; sequentially numbered;
  never delete, only supersede.
- **Versioning**: Semantic versioning for the scraper image and the
  documentation header front-matter.

## 🔄 Sync with Notion

The canonical engineering doc set lives **here in the repo**. The
[InkBytes Notion hub](https://www.notion.so/373eca56ed94818da548f66ca288593a)
mirrors product-vision.md + the architecture summary for non-technical
stakeholders. Treat the repo as source of truth; sync to Notion on
significant changes.

## 🚦 Status legend

Every doc carries a status line:

- **Draft** — work in progress, ideas, not yet authoritative
- **v1 / v2 / …** — stable, current; safe to act on
- **Living** — kept fresh on every architectural change
- **Superseded** — kept for history; see successor link at the top
