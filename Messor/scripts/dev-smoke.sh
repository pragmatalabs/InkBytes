#!/usr/bin/env bash
# Messor — local dev smoke check.
# Run after dev-up.sh + one scrape cycle. Asserts the basic invariants.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRAPER_DIR="$REPO_ROOT/Messor/apps/scraper"
STAGING_DIR="$SCRAPER_DIR/data/scrapes"

pass() { printf "  \033[32mPASS\033[0m %s\n" "$*"; }
fail() { printf "  \033[31mFAIL\033[0m %s\n" "$*"; exit 1; }

echo "▶ Messor dev smoke check"

# 1. venv exists
[ -d "$SCRAPER_DIR/.venv" ] || fail "no .venv (run scripts/dev-up.sh first)"
pass ".venv present"

# 2. inkbytes package importable
"$SCRAPER_DIR/.venv/bin/python" -c "import inkbytes" \
  && pass "import inkbytes" \
  || fail "inkbytes not installed (pip install -e Messor/packages/inkbytes)"

# 3. core modules importable
# core/scraper.py loads ConfigLoader('./env.yaml') at import time so we must
# run the check from $SCRAPER_DIR where env.yaml lives.
(cd "$SCRAPER_DIR" && "$SCRAPER_DIR/.venv/bin/python" -c "
import sys; sys.path.insert(0, '.')
from core.application import Application
from core.staging_store import StagingStore
") && pass "core modules import" || fail "core import failed"

# 4. env.local.yaml exists and points to local services
grep -q "save_mode: local_only\|messor.logs" "$SCRAPER_DIR/env.local.yaml" \
  && pass "env.local.yaml uses messor.logs naming" \
  || fail "env.local.yaml is missing or stale"

# 5. at least one staging file produced (only if user has run a cycle)
if [ -d "$STAGING_DIR" ] && [ -n "$(ls -A "$STAGING_DIR" 2>/dev/null)" ]; then
  count=$(ls "$STAGING_DIR" | wc -l | tr -d ' ')
  pass "staging dir has $count file(s)"
  echo "    latest: $(ls -t "$STAGING_DIR" | head -1)"
else
  echo "  -- no scrape run yet; do:  cd $SCRAPER_DIR && python main.py env.local.yaml --scrape"
fi

# 6. dev infra reachable (best-effort)
if command -v nc >/dev/null 2>&1; then
  nc -z localhost 5672 2>/dev/null && pass "RabbitMQ :5672 reachable" || echo "  -- RabbitMQ :5672 not up (ok for local_only mode)"
  nc -z localhost 9000 2>/dev/null && pass "MinIO    :9000 reachable" || echo "  -- MinIO    :9000 not up (ok for local_only mode)"
fi

echo
echo "✓ Smoke check complete."
