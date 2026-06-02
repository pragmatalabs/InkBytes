# ADR-0001 — Monorepo migration (Laravel platform + Python scraper)

* **Status**: Accepted
* **Date**: 2026-04 (in progress)
* **Deciders**: Julián de la Rosa
* **Supersedes**: ad-hoc layout where Messor lived at the repo root

## Context

The original Messor layout had Python sources at the repo root, mixed with
`client/`, `api/`, `core/`, `services/`, plus a separate Laravel project
(`Inkbytes-PowerDesktop`) elsewhere in the workspace. The boundary between
"the harvester service" and "the platform that owns outlets, articles,
billing" was unclear, and shared types (article, outlet, session) drifted
between languages.

## Decision

Adopt a single monorepo under `Messor/` with the following layout:

```text
apps/
  platform/     # Laravel 11 + Inertia + React (MUI) — the platform & admin
  scraper/      # Python service — the harvester agent
packages/
  contracts/    # Shared schemas (article, outlet, session)
infra/
  docker/       # Docker Compose, Dockerfiles, nginx
docs/           # This documentation
```

Root entrypoint `main.py` is a thin compatibility wrapper that forwards into
`apps/scraper/main.py`.

## Consequences

**Positive**

- Clear separation of concerns: scraper service vs. platform.
- Shared types live in one place (`packages/contracts`).
- Single CI pipeline can build both apps.
- Easier production deploy via a single repo to DO App Platform.

**Negative**

- Bigger working tree; tooling (Composer, Poetry/Pip, npm) must coexist.
- Symlink `apps/scraper/inkbytes -> ../../../src/inkbytes` is a transitional
  hack; we will retire it in favor of `packages/contracts`.

**Follow-ups**

- ADR-0004 (planned): retire `src/inkbytes` symlink and publish
  `packages/contracts` as a Python package consumed by the scraper.
- Move `client/` (legacy operator React app) under `apps/platform` once
  parity is reached.
- Delete `Messor copy/` and `V1/` after one release of stability.
