#!/usr/bin/env bash
# InkBytes — parent orchestrator: bring up the local v0 stack.
#
# Stages it knows about (controlled by --profile):
#   infra      : Postgres + RabbitMQ + MinIO (always up)
#   messor     : adds the harvester
#   full       : adds Curator + Reader + Admin (requires those repos)
#
# Usage:
#   bash orchestrator/scripts/up.sh             # infra only
#   bash orchestrator/scripts/up.sh messor      # infra + messor
#   bash orchestrator/scripts/up.sh full        # everything

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="$ROOT/orchestrator/docker-compose.dev.yaml"
PROFILE="${1:-infra}"

case "$PROFILE" in
  infra)
    docker compose -f "$COMPOSE" up -d postgres rabbitmq minio minio-bootstrap
    ;;
  messor)
    docker compose -f "$COMPOSE" up -d postgres rabbitmq minio minio-bootstrap messor
    ;;
  full)
    if [ ! -d "$ROOT/Curator" ] || [ ! -d "$ROOT/Reader" ]; then
      echo "✗ Curator/ or Reader/ not yet scaffolded — see docs/mvp-plan.md §7 D2/D4."
      exit 1
    fi
    docker compose -f "$COMPOSE" --profile full up -d
    ;;
  *)
    echo "Unknown profile: $PROFILE"
    echo "  use one of: infra | messor | full"
    exit 2
    ;;
esac

echo
echo "✓ Stack up (profile: $PROFILE)"
echo "  Postgres:      localhost:5432   (inkbytes / inkbytes)"
echo "  RabbitMQ UI:   http://localhost:15672 (messor / messor)"
echo "  MinIO console: http://localhost:9001  (messor / messormessor)"
[ "$PROFILE" = "messor" ] && echo "  Messor:        http://localhost:8050"
if [ "$PROFILE" = "full" ]; then
  echo "  Reader:        http://localhost:3000"
  echo "  Admin:         http://localhost:3001"
  echo "  Curator:       http://localhost:8060"
fi
