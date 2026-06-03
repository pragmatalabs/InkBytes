# ADR-0002 (repo-wide) — GitHub monorepo is the single source of truth; sever GitLab

* **Status**: Accepted
* **Date**: 2026-06-02
* **Deciders**: Julián de la Rosa
* **Scope**: Repository-wide (supersedes the per-service remotes)
* **Relates to**: [ADR-0001](./0001-consolidate-backend-into-laravel-backoffice.md) (Laravel Backoffice consolidation), [Messor ADR-0001](../../Messor/docs/adr/0001-monorepo-migration.md) (monorepo migration), [Messor ADR-0007](../../Messor/docs/adr/0007-self-contained-shared-kernel.md) (self-contained kernel), [docs/lessons-learned.md](../lessons-learned.md)

## Context

After the monorepo migration, several directories were still independent
git repositories nested inside the InkBytes tree, each pointing at its own
remote (or none):

| Path | Hidden remote |
|---|---|
| `Messor/.git` | `gitlab.com/inkbytes/messor` |
| `database/.git` | `gitlab.com/inkbytes/database` |
| `common/.git` | (local-only, no remote) |
| `models/.git` | (local-only, no remote) |
| `src/.git` | legacy GitHub copy (duplicate of the shared kernel) |

Consequences of this split:

- The shared kernel `Messor/packages/inkbytes/` was **never in GitHub** — an
  over-broad `.gitignore` rule (`inkbytes/`) silently excluded it.
- `database`, `common`, `models` looked tracked but were really separate
  repos; `git add` from the root treated them as embedded gitlinks, not
  source.
- Two sources of truth (GitHub monorepo vs. the GitLab module repos) that
  could — and did — diverge.

## Decision

The **GitHub monorepo `github.com/pragmatalabs/InkBytes` (branch `master`)
is the single source of truth.** Sever every other git remote/repo inside
the tree.

1. Remove the nested `.git` directories: `Messor`, `database`, `common`,
   `models` (and the already-absent `src`). This drops their separate
   histories (no-archive was chosen deliberately); current files are
   preserved.
2. Absorb `database/`, `common/`, `models/` as tracked source in the
   monorepo (later consolidated into the kernel — Messor ADR-0007).
3. Fix the `.gitignore` rules that were hiding the shared kernel and the
   former GitLab modules; re-include them as real source while keeping
   `venv/`, `__pycache__`, `.next`, `node_modules`, and secrets ignored.
4. Remove `Messor/.gitlab-ci.yml` (GitLab CI no longer applies; CI will be
   GitHub Actions when added).

## Consequences

**Positive**

- One canonical remote. No GitLab/GitHub divergence.
- The shared kernel and former modules are now versioned in GitHub.
- Docker builds need no external repos (Messor ADR-0007).

**Negative**

- The separate per-module git histories are gone (`database`, `common`,
  `models`, `Messor`'s GitLab history). Accepted: the working trees were
  preserved and the modules had little independent history of value.
- Anyone with the old GitLab clones must re-clone from GitHub.

## Alternatives considered

- **Keep GitLab as a mirror.** Rejected: two remotes is exactly the
  divergence problem we hit; a mirror needs sync tooling and discipline.
- **Archive the histories first (git bundle / subtree import).** Offered
  and declined by the decider — the file state matters, the history did
  not.

## Follow-ups

- Retire the GitLab project pages once confident nothing depends on them.
- `Trashx/` (local-only, untracked) still holds parked legacy repos,
  some with unpushed work — review repo-by-repo before deleting (tracked in
  [STATUS.md](../STATUS.md)).
- Add GitHub Actions CI (lint + test + image build) — see Messor's
  Sprint-1 backlog (INK-9).
