#!/usr/bin/env bash
# Commit script for the Messor v1 docs + monorepo migration.
#
# Run from the repo root (/Volumes/Pragmata/Projects/InkBytes) in your host
# terminal — NOT inside the Cowork sandbox. The sandbox cannot unlink
# .git/index.lock on this volume.
#
# Usage:
#   cd /Volumes/Pragmata/Projects/InkBytes
#   bash Messor/scripts/commit-v1-docs.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# 1. Clear any stuck lock left over from a previous session.
if [ -f .git/index.lock ]; then
  echo "› removing stale .git/index.lock"
  rm -f .git/index.lock
fi

git status -s | head -10
echo

# 2. Commit the monorepo migration (deletions at repo root + new apps/ tree).
echo "› staging monorepo migration"
git add -A \
  Messor/apps \
  Messor/packages \
  Messor/infra \
  Messor/api \
  Messor/scraping \
  Messor/spaces \
  Messor/scripts \
  Messor/env.yaml \
  Messor/env.do.yaml \
  Messor/poetry.lock \
  Messor/pyproject.toml \
  Messor/requirements.txt \
  Messor/__main__.py \
  Messor/docker-compose.yaml \
  Messor/docker/Dockerfile \
  Messor/docker/Dockerfile.old \
  Messor/docker/docker-compose.yaml \
  Messor/.dockerignore \
  Messor/.gitignore \
  Messor/README.md \
  Messor/__init__.py \
  Messor/AGENTS.md \
  Messor/main.py \
  Messor/package.json \
  Messor/package-lock.json \
  Messor/logo.png 2>/dev/null || true

git commit -m "refactor(messor): consolidate to apps/scraper + apps/platform monorepo

Move legacy Messor root sources under apps/scraper. Adopt monorepo
layout (apps/, packages/, infra/). Root main.py becomes a compatibility
wrapper. Remove Dockerfile.old and unused root docker-compose."

# 3. Commit the docs + sanitized env template.
echo "› staging docs and sanitized env template"
git add \
  Messor/docs \
  Messor/apps/scraper/env.example.yaml

git commit -m "docs(messor): v1 scope, C4 architecture, ops, security, ADRs

- docs/v1-scope.md: simplified v1 target, what's in / what's out
- docs/product-vision.md: paid one-pager reader, Messor as 24/7 agent
- docs/architecture.md: C4 L1-L3 + separation-of-concerns matrix
- docs/configuration.md: env.yaml schema + env-var overrides
- docs/security.md: flags leaked secrets, rotation playbook
- docs/operations.md: 24/7 runbook, incident playbooks
- docs/deployment-digitalocean.md: App Platform topology
- docs/adr/0001-monorepo-migration.md
- docs/adr/0002-rabbitmq-events.md
- docs/adr/0003-do-spaces-artifact-store.md
- apps/scraper/env.example.yaml: committed template (no secrets)

Note: apps/scraper/env.yaml remains gitignored. Real values come from
env vars or a local env.local.yaml. Rotate all previously-leaked tokens
and scrub history with git-filter-repo as a follow-up."

# 4. Push.
echo "› pushing to origin/master"
git push origin master

echo
echo "✓ Done. See: https://github.com/pragmatalabs/InkBytes/commits/master"
