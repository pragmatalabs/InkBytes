#!/usr/bin/env bash
# InkBytes — one-time droplet setup on pragmata-001.
# Safe to re-run (all steps are idempotent).
#
# Usage:  sudo bash infra/scripts/server-bootstrap.sh
set -euo pipefail

PROJECT="inkbytes"
DEPLOY_PATH="/opt/${PROJECT}"
REPO_URL="git@github.com-${PROJECT}:pragmatalabs/InkBytes.git"

echo "==> [1/7] System update"
apt-get update -q && apt-get upgrade -y -q

echo "==> [2/7] Docker + compose plugin"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
fi
apt-get install -y docker-compose-plugin gettext-base curl git

echo "==> [3/7] doctl"
if ! command -v doctl &>/dev/null; then
    V=$(curl -s https://api.github.com/repos/digitalocean/doctl/releases/latest \
        | grep '"tag_name"' | cut -d'"' -f4 | tr -d v)
    curl -sL "https://github.com/digitalocean/doctl/releases/download/v${V}/doctl-${V}-linux-amd64.tar.gz" \
        | tar -xz
    mv doctl /usr/local/bin/
fi
echo "  doctl version: $(doctl version --short 2>/dev/null || echo 'run: doctl auth init')"

echo "==> [4/7] Shared networks (no-op if already exist)"
docker network create traefik-public 2>/dev/null || echo "  traefik-public already exists"
docker network create infra-shared   2>/dev/null || echo "  infra-shared already exists"

echo "==> [5/7] Per-project SSH key for GitHub (read-only repo access)"
KEY_PATH="$HOME/.ssh/${PROJECT}_repo"
if [ ! -f "$KEY_PATH" ]; then
    ssh-keygen -t ed25519 -C "${PROJECT}@pragmata-001" -f "$KEY_PATH" -N ""
    echo ""
    echo "  *** ADD THIS PUBLIC KEY to GitHub repo → Settings → Deploy keys ***"
    echo "  URL: https://github.com/pragmatalabs/InkBytes/settings/keys"
    echo ""
    cat "${KEY_PATH}.pub"
    echo ""
fi

# SSH config alias so git pull uses the right key
if ! grep -q "Host github.com-${PROJECT}" "$HOME/.ssh/config" 2>/dev/null; then
    cat >> "$HOME/.ssh/config" <<EOF

Host github.com-${PROJECT}
    HostName github.com
    User git
    IdentityFile ${KEY_PATH}
EOF
fi

echo "==> [6/7] Clone repo into ${DEPLOY_PATH}"
mkdir -p "$DEPLOY_PATH"
if [ -d "$DEPLOY_PATH/.git" ]; then
    echo "  Repo already cloned, pulling..."
    cd "$DEPLOY_PATH" && git pull origin master
else
    git clone "$REPO_URL" "$DEPLOY_PATH" || {
        echo ""
        echo "  Clone failed — did you add the deploy key to GitHub? (step 5)"
        echo "  Run again after adding the key."
        exit 1
    }
fi

echo "==> [7/7] Bootstrap complete"
cat <<EOF

NEXT STEPS:
  1. Authenticate doctl:
       doctl auth init          # paste your DO PAT

  2. Fill production secrets:
       cp ${DEPLOY_PATH}/infra/.env.production.example ${DEPLOY_PATH}/infra/.env
       nano ${DEPLOY_PATH}/infra/.env

  3. Ensure Traefik is running (shared, once per host):
       ls /opt/traefik/ || echo "Set up Traefik first"
       cd /opt/traefik && docker compose up -d

  4. DNS: Add A records BEFORE first deploy (Let's Encrypt needs them):
       A  inkbytes.pragmata.cloud        → <droplet IP>
       A  admin.inkbytes.pragmata.cloud  → <droplet IP>

  5. First deploy:
       cd ${DEPLOY_PATH} && bash infra/deploy.sh --build

  6. Set GitHub Secrets (see docs/deployment-secrets.md):
       gh secret set DEPLOY_KEY  < ~/.ssh/inkbytes_deploy
       gh secret set DEPLOY_HOST --body "<DROPLET_IP>"
       gh secret set DEPLOY_USER --body "root"

EOF
