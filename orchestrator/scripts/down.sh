#!/usr/bin/env bash
# InkBytes — parent orchestrator: stop the local v0 stack.
#
# Usage:
#   bash orchestrator/scripts/down.sh           # stop (keep volumes)
#   bash orchestrator/scripts/down.sh --nuke    # stop AND delete volumes

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="$ROOT/orchestrator/docker-compose.dev.yaml"

if [ "${1:-}" = "--nuke" ]; then
  docker compose -f "$COMPOSE" --profile full down -v
  echo "✓ stack down + volumes deleted"
else
  docker compose -f "$COMPOSE" --profile full down
  echo "✓ stack down (volumes preserved)"
fi
