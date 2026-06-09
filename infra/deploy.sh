#!/usr/bin/env bash
# InkBytes — idempotent on-host deploy script.
# Run on the VPS inside /docker/inkbytes.
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

# Source .env FIRST so DEPLOY_PROFILE (and all other vars) are available
# before the profile selection block below.
set -a; source "$ENV_FILE"; set +a

# ── Server profile ────────────────────────────────────────────────────────────
# DEPLOY_PROFILE in infra/.env selects the compose override for this server.
#   (empty / unset)  → Hostinger VPS (16 GB, file-based Traefik)
#   do               → DigitalOcean pragmata-001 (7.8 GB, label-based Traefik)
# The override file lives in infra/docker-compose.{profile}.yml.
PROFILE="${DEPLOY_PROFILE:-}"
OVERRIDE_FILE=""
if [ -n "$PROFILE" ] && [ -f "$SCRIPT_DIR/docker-compose.${PROFILE}.yml" ]; then
    OVERRIDE_FILE="-f $SCRIPT_DIR/docker-compose.${PROFILE}.yml"
    echo "[deploy] Server profile: $PROFILE (override: docker-compose.${PROFILE}.yml)"
else
    echo "[deploy] Server profile: default (hostinger)"
fi

# ── 1. Ensure shared network ──────────────────────────────────────────────────
docker network inspect traefik-public &>/dev/null || {
    echo "[deploy] Creating traefik-public network..."
    docker network create traefik-public
}

# ── 1b. On DigitalOcean: connect infra-ollama to inkbytes-internal ─────────────
# infra-ollama lives in the infra-shared network; Curator needs to reach it
# for embeddings (bge-m3). This is idempotent — already-connected is not an error.
if [ "$PROFILE" = "do" ]; then
    NETWORK="inkbytes_inkbytes-internal"
    if docker inspect infra-ollama &>/dev/null; then
        docker network connect "$NETWORK" infra-ollama 2>/dev/null && \
            echo "[deploy][do] infra-ollama connected to $NETWORK" || \
            echo "[deploy][do] infra-ollama already in $NETWORK (ok)"
    else
        echo "[deploy][do] WARNING: infra-ollama not found — embeddings will fail"
    fi
fi

# ── 2. Pull latest code ───────────────────────────────────────────────────────
echo "[deploy] Pulling latest code..."
cd "$REPO_ROOT"
git pull origin master

# ── 3. Images ─────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--build" ]]; then
    echo "[deploy] Building images locally from source..."
    # compose files use pre-built registry images (no build: context defined).
    # Build directly with the correct context paths instead.
    docker build \
        -t "${CURATOR_IMAGE:-ghcr.io/pragmatalabs/inkbytes-curator:latest}" \
        -f "$REPO_ROOT/Curator/apps/curator/Dockerfile" \
        "$REPO_ROOT/Curator/"
    docker build \
        -t "${READER_IMAGE:-ghcr.io/pragmatalabs/inkbytes-reader:latest}" \
        -f "$REPO_ROOT/Reader/apps/web/Dockerfile" \
        "$REPO_ROOT/Reader/apps/web/"
    # Messor — context is Messor/ (Dockerfile COPYs apps/scraper + packages/inkbytes),
    # mirroring .github/workflows/deploy.yml. Previously omitted here, so a
    # `--build` deploy silently shipped a stale Messor image (Messor ADR-0014 fix
    # was pushed but not rebuilt). Keep this in lockstep with the CI build.
    docker build \
        -t "${MESSOR_IMAGE:-ghcr.io/pragmatalabs/inkbytes-messor:latest}" \
        -f "$REPO_ROOT/Messor/docker/Dockerfile" \
        "$REPO_ROOT/Messor/"
else
    echo "[deploy] Pulling images from GitHub Container Registry..."
    if [ -n "${GHCR_TOKEN:-}" ]; then
        echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USER:-pragmatalabs}" --password-stdin 2>/dev/null || true
    fi
    docker compose -f "$COMPOSE" $OVERRIDE_FILE --env-file "$ENV_FILE" pull --ignore-pull-failures || true
fi

# ── 4. (Re)start the stack ────────────────────────────────────────────────────
echo "[deploy] Starting stack..."
docker compose -f "$COMPOSE" $OVERRIDE_FILE --env-file "$ENV_FILE" up -d --remove-orphans

# ── 5. Post-deploy checks ─────────────────────────────────────────────────────
echo "[deploy] Waiting for services to become healthy..."
sleep 8

echo "[deploy] Service status:"
docker compose -f "$COMPOSE" $OVERRIDE_FILE --env-file "$ENV_FILE" ps

echo "[deploy] Pruning dangling images..."
docker image prune -f

echo ""
echo "✓ InkBytes deployed"
echo "  Reader:    https://${READER_DOMAIN:-inkbytes.galvanic.cloud}"
echo "  Backoffice: https://${ADMIN_DOMAIN:-admin.inkbytes.galvanic.cloud}"
echo ""
echo "  Logs:  docker compose -f infra/docker-compose.prod.yml logs -f"
echo "  DB:    docker exec -it inkbytes-postgres psql -U inkbytes -d inkbytes"
echo "  Queue: ssh -L 15683:localhost:15683 root@<DROPLET_IP>  →  localhost:15683"
