#!/usr/bin/env bash
# InkBytes — idempotent on-host deploy script.
# Run on pragmata-001 inside /opt/inkbytes.
#
# Usage:
#   ./infra/deploy.sh          # pull registry images + restart
#   ./infra/deploy.sh --build  # build locally (no registry) + restart
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$SCRIPT_DIR/docker-compose.prod.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# ── Preflight ─────────────────────────────────────────────────────────────────
[ -f "$ENV_FILE" ] || {
    echo "ERROR: $ENV_FILE not found."
    echo "       cp infra/.env.production.example infra/.env && fill secrets"
    exit 1
}

set -a; source "$ENV_FILE"; set +a

# ── 1. Ensure shared network ──────────────────────────────────────────────────
docker network inspect traefik-public &>/dev/null || {
    echo "[deploy] Creating traefik-public network..."
    docker network create traefik-public
}

# ── 2. Pull latest code ───────────────────────────────────────────────────────
echo "[deploy] Pulling latest code..."
cd "$REPO_ROOT"
git pull origin master

# ── 3. Images ─────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--build" ]]; then
    echo "[deploy] Building images locally..."
    docker compose -f "$COMPOSE" --env-file "$ENV_FILE" build --parallel
else
    echo "[deploy] Pulling images from registry..."
    doctl registry login --expiry-seconds 600 || true
    docker compose -f "$COMPOSE" --env-file "$ENV_FILE" pull --ignore-pull-failures || true
fi

# ── 4. (Re)start the stack ────────────────────────────────────────────────────
echo "[deploy] Starting stack..."
docker compose -f "$COMPOSE" --env-file "$ENV_FILE" up -d --remove-orphans

# ── 5. Post-deploy checks ─────────────────────────────────────────────────────
echo "[deploy] Waiting for services to become healthy..."
sleep 8

echo "[deploy] Service status:"
docker compose -f "$COMPOSE" --env-file "$ENV_FILE" ps

echo "[deploy] Pruning dangling images..."
docker image prune -f

echo ""
echo "✓ InkBytes deployed"
echo "  Reader:    https://${READER_DOMAIN:-inkbytes.org}"
echo "  Backoffice: https://${ADMIN_DOMAIN:-admin.inkbytes.org}"
echo ""
echo "  Logs:  docker compose -f infra/docker-compose.prod.yml logs -f"
echo "  DB:    docker exec -it inkbytes-postgres psql -U inkbytes -d inkbytes"
echo "  Queue: ssh -L 15683:localhost:15683 root@<DROPLET_IP>  →  localhost:15683"
