#!/usr/bin/env bash
# Messor — one-button local development bring-up.
#
# What it does:
#   1. Boots dev RabbitMQ + MinIO via Docker.
#   2. Creates a Python venv under apps/scraper/.venv.
#   3. Installs requirements (includes -e ../../packages/inkbytes).
#   4. Downloads NLTK punkt data.
#   5. Generates env.local.yaml pointed at local RabbitMQ + MinIO.
#   6. Prints next-step commands.
#
# Idempotent. Re-running is safe.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MESSOR_ROOT="$REPO_ROOT/Messor"
SCRAPER_DIR="$MESSOR_ROOT/apps/scraper"
COMPOSE_FILE="$MESSOR_ROOT/infra/docker/dev-compose.yaml"
VENV="$SCRAPER_DIR/.venv"

step() { printf "\n\033[1;34m▶ %s\033[0m\n" "$*"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m⚠\033[0m %s\n" "$*"; }

step "1/5 Bringing up dev infra (RabbitMQ + MinIO)"
if ! command -v docker >/dev/null 2>&1; then
  warn "docker not found — skipping. Install Docker Desktop and re-run."
else
  docker compose -f "$COMPOSE_FILE" up -d
  ok "RabbitMQ UI:  http://localhost:15672  (messor / messor)"
  ok "MinIO console: http://localhost:9001  (messor / messormessor)"
fi

step "2/5 Python venv"
# On macOS, /usr/local/bin/bash (Homebrew Intel) runs Python as x86_64.
# Use the same Python that the user's default shell will use at runtime.
PYTHON_BIN="$(command -v python3)"
if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
  ok "created $VENV ($(\"$VENV/bin/python\" -c 'import platform; print(platform.machine())'))"
else
  ok "venv already exists ($(\"$VENV/bin/python\" -c 'import platform; print(platform.machine())'))"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
python -m pip install --quiet --upgrade pip

step "3/5 Installing requirements"
cd "$SCRAPER_DIR"
# --no-cache-dir prevents stale wheels being reused across architecture changes
python -m pip install -q --no-cache-dir -r requirements.txt
ok "deps installed (including -e ../../packages/inkbytes)"

step "4/5 NLTK punkt data"
python - <<'PY'
import nltk
for pkg in ("punkt", "punkt_tab"):
    try:
        nltk.data.find(f"tokenizers/{pkg}")
        print(f"  ✓ {pkg} already present")
    except LookupError:
        nltk.download(pkg, quiet=True)
        print(f"  ✓ {pkg} downloaded")
PY

step "5/5 env.local.yaml"
if [ ! -f "$SCRAPER_DIR/env.local.yaml" ]; then
  cp "$SCRAPER_DIR/env.local.yaml" "$SCRAPER_DIR/env.local.yaml.bak" 2>/dev/null || true
  warn "env.local.yaml missing — create from env.example.yaml and adjust"
else
  ok "env.local.yaml present"
fi

cat <<NEXT

────────────────────────────────────────────────────────────
Dev environment ready.

Next steps (from $SCRAPER_DIR):

  source .venv/bin/activate

  # One-shot scrape (no broker, no S3 — file-only)
  python main.py env.local.yaml --scrape

  # Smoke check
  bash $MESSOR_ROOT/scripts/dev-smoke.sh

  # Tear down infra when done:
  docker compose -f $COMPOSE_FILE down
────────────────────────────────────────────────────────────
NEXT
