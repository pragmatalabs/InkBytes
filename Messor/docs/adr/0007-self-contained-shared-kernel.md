# ADR-0007 — Self-contained shared kernel (no symlinks); Docker installs it from context

* **Status**: Accepted
* **Date**: 2026-06-02
* **Deciders**: Julián de la Rosa
* **Relates to**: ADR-0001 (monorepo migration), [root ADR-0002](../../../docs/adr/0002-github-monorepo-single-source.md) (GitHub single source), [docs/lessons-learned.md](../../../docs/lessons-learned.md)

## Context

The shared kernel `packages/inkbytes/` re-exported three subpackages —
`common`, `database`, `models` — as **symlinks** to repo-root directories:

```
Messor/packages/inkbytes/inkbytes/common   -> ../../../../common
Messor/packages/inkbytes/inkbytes/database -> ../../../../database
Messor/packages/inkbytes/inkbytes/models   -> ../../../../models
```

A second, legacy symlink chain also existed (`apps/scraper/inkbytes` and
`Messor/inkbytes` → the untracked `src/inkbytes`). This caused a string of
real problems:

1. **Import shadowing / local-vs-CI divergence.** `apps/scraper/inkbytes`
   was a tracked symlink to the *untracked* `src/inkbytes`. Because the cwd
   wins on `sys.path`, `import inkbytes` resolved to that symlink locally,
   while a fresh clone (no `src/`) silently fell back to the editable
   `packages/inkbytes` install — so local and CI could run different code.
2. **Docker couldn't build.** The kernel symlinks pointed to repo-root dirs
   that live *outside* the `Messor/` build context, so the old Dockerfile
   resorted to cloning `common`/`models`/`database` from
   `gitlab.com/inkbytes/*` — a remote that has since been severed
   (see root ADR-0002).
3. **Symlink fragility** in general (Windows checkouts, tarballs, `COPY`).

Investigation showed the repo-root `common/`, `database/`, `models/`
directories had **no other consumers** — nothing imports them directly;
all access is via `inkbytes.common.*`, `inkbytes.models.*`,
`inkbytes.database.*`. Curator has its own (Pydantic v2) models and does
not touch them. So they existed *only* to be symlink targets.

## Decision

Make the shared kernel **fully self-contained** and consume it as an
ordinary installed package.

1. **Move the real source** of `common/`, `database/`, `models/` from the
   repo root **into** `packages/inkbytes/inkbytes/` as ordinary directories
   (git recorded this as renames; history preserved). Delete the orphaned
   repo-root copies.
2. **Remove all kernel symlinks** — the three in-package ones and the two
   legacy `… -> src/inkbytes` links (`apps/scraper/inkbytes`,
   `Messor/inkbytes`).
3. **Consume via the editable install** already declared in
   `apps/scraper/requirements.txt` (`-e ../../packages/inkbytes`).
   `import inkbytes` now resolves identically on local, CI, a fresh clone,
   and inside the container — and fails *loudly* (ImportError) if the
   package isn't installed, instead of silently using stale code.
4. **Rewrite the Dockerfile** for the monorepo layout: no GitLab clone;
   install the kernel from the build context via `requirements.txt`;
   multi-stage (`python:3.11` builder → `python:3.11-slim` runtime); bake
   NLTK `punkt`/`punkt_tab`; create the bind-mounted runtime dirs so the
   image runs standalone; `CMD … --schedule` (non-interactive — pairs with
   the EOF/serve-mode fix, ADR follow-up below).
5. **Slim the Docker build context** via `.dockerignore`: exclude runtime
   artifacts (`data/history` was 710 MB, `logs/`) and sibling apps
   (`apps/platform`, `client`). Context dropped 1.68 GB → ~671 KB.

## Consequences

**Positive**

- One canonical copy of the kernel; `import inkbytes` is identical
  everywhere. No more local-vs-clone drift.
- `docker build` works from the `Messor/` context with no external repos.
  Verified: image builds (447 MB) and `import inkbytes` →
  `/app/packages/inkbytes/...` plus the full app DI graph imports (run
  exit 0) inside the container.
- No symlinks anywhere in the kernel — portable to Windows/tar/COPY.
- GitLab is no longer a build dependency.

**Negative / trade-offs**

- The kernel directory is larger (it now holds real source, not links).
- `git` shows ~80 renames in the consolidating commit; reviewers must trust
  rename detection.
- `requires-python` for the kernel stays `>=3.10,<3.13`; the image uses
  3.11 while local dev is 3.12 — both in range, but builds for the
  DigitalOcean droplet must target `linux/amd64`
  (`docker build --platform linux/amd64`).

## Alternatives considered

- **Build context = repo root** (keep symlinks; change compose
  `context: ..` → `../..` and add a root `.dockerignore`). Rejected: keeps
  symlink fragility, pulls `Curator/`/`Reader/`/`Trashx/` into the build
  context, and doesn't fix the local-vs-clone import divergence.
- **Vendor a copy into the kernel while keeping root dirs too.** Rejected:
  two copies of the same source invites drift. Since the root dirs have no
  other consumers, moving (not copying) is a clean consolidation.
- **Keep cloning the kernel from GitLab in Docker.** Rejected outright —
  GitLab is being retired (root ADR-0002); the monorepo is the single
  source of truth.

## Follow-ups

- `command_processor.process_commands()` was hardened in the same effort:
  one-shot (`--scrape … < /dev/null`) exits cleanly; bare `main.py` in a
  non-interactive shell enters **serve mode** (blocks the API alive) rather
  than spinning on EOF. See [lessons-learned](../../../docs/lessons-learned.md).
- For the full production image, build `--platform linux/amd64` and supply
  service hostnames via the env-var overlay (the committed `env.yaml` still
  points at `localhost`).
- If `src/` (legacy duplicate) is ever needed, it stays untracked; nothing
  references it now.
