#!/usr/bin/env bash
# InkBytes — run the FULL local pipeline as dev processes (not Docker).
#
#   Messor (harvest, --schedule)  →  RabbitMQ  →  Curator (--consume)  →  Postgres  →  Reader
#
# Infra (Postgres :5432, RabbitMQ :5672, MinIO :9000) stays in Docker via up.sh;
# the three apps run as local processes against env.local.yaml so you can edit +
# restart fast. Embeddings need Ollama on :11434 (bge-m3).
#
# IMPORTANT: the apps MUST run under each app's `.venv/bin/python` — the macOS
# framework python lacks the deps (aio_pika / pika / newspaper). This script
# pins the right interpreter so you don't hit that trap.
#
# Usage:
#   bash orchestrator/scripts/dev-pipeline.sh up      # bring up infra + all apps
#   bash orchestrator/scripts/dev-pipeline.sh down    # stop the apps (infra stays)
#   bash orchestrator/scripts/dev-pipeline.sh status  # what's running + pipeline counts
#   bash orchestrator/scripts/dev-pipeline.sh logs    # tail all app logs

set -uo pipefail

# The app .venv pythons are universal binaries but their native wheels
# (pydantic_core, …) are arm64-only. If this script is spawned from a translated
# (x86_64/Rosetta) context — e.g. a background runner — child pythons inherit
# x86_64 and crash on import. Re-exec the whole script natively on Apple Silicon
# so every child inherits arm64.
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = "1" ] && [ "$(arch 2>/dev/null)" != "arm64" ]; then
    exec arch -arm64 /bin/bash "$0" "$@"
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CURATOR="$ROOT/Curator/apps/curator"
MESSOR="$ROOT/Messor/apps/scraper"
READER="$ROOT/Reader/apps/web"
BACKOFFICE="$ROOT/Messor/apps/platform"   # Laravel admin (Stop-Curator toggle, settings)
LOGDIR="/tmp/inkbytes-dev"
mkdir -p "$LOGDIR"

# The .venv pythons are universal binaries but the native wheels (pydantic_core,
# etc.) are arm64-only. A backgrounded/Rosetta launch can run the interpreter as
# x86_64 → "incompatible architecture" on import. Pin to arm64 on Apple Silicon.
ARCHCMD=""
[ "$(uname -m)" = "arm64" ] && ARCHCMD="arch -arm64"
CUR_PY="$ARCHCMD $CURATOR/.venv/bin/python"
MES_PY="$ARCHCMD $MESSOR/.venv/bin/python"

c_log="$LOGDIR/curator.log"
m_log="$LOGDIR/messor.log"
r_log="$LOGDIR/reader.log"
b_log="$LOGDIR/backoffice.log"        # artisan serve
bv_log="$LOGDIR/backoffice-vite.log"  # vite assets

_port_pids() { lsof -ti :"$1" 2>/dev/null; }
_proc_pids() { pgrep -f "$1" 2>/dev/null; }

up() {
    echo "[dev] 1/5 infra (Postgres/RabbitMQ/MinIO)…"
    bash "$ROOT/orchestrator/scripts/up.sh" infra >/dev/null 2>&1 || true

    echo "[dev] 2/5 checking Ollama (embeddings) on :11434…"
    if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "      ⚠️  Ollama not reachable — embeddings will fail. Start it: 'ollama serve' + 'ollama pull bge-m3'"
    fi

    echo "[dev] 3/5 Curator (--consume, :8060)…"
    _port_pids 8060 | xargs -r kill -9 2>/dev/null; sleep 1
    ( cd "$CURATOR" && nohup $CUR_PY main.py --config env.local.yaml --consume > "$c_log" 2>&1 & )

    echo "[dev] 4/5 Messor (--schedule, harvests every schedule_interval_minutes)…"
    _proc_pids "main.py env.local.yaml --schedule" | xargs -r kill 2>/dev/null
    ( cd "$MESSOR" && nohup $MES_PY main.py env.local.yaml --schedule --no-browser > "$m_log" 2>&1 & )

    echo "[dev] 5/6 Reader (npm run dev, :3000)…"
    if [ -z "$(_port_pids 3000)" ]; then
        ( cd "$READER" && nohup npm run dev > "$r_log" 2>&1 & )
    else
        echo "      (already serving on :3000 — left as-is)"
    fi

    echo "[dev] 6/6 Backoffice (Laravel admin :8000 + vite)…"
    # PHP is fine as-is (no arm64-only wheels like Python). Apply any pending
    # migrations, then serve + vite for the Inertia/React assets.
    ( cd "$BACKOFFICE" && php artisan migrate --force >/dev/null 2>&1 || true )
    _port_pids 8000 | xargs -r kill -9 2>/dev/null
    ( cd "$BACKOFFICE" && nohup php artisan serve --port=8000 > "$b_log" 2>&1 & )
    # VITE_APP_ORIGIN must match the artisan serve origin — vite.config.js
    # defaults it to :18080 (Docker dev), which CORS-blocks every asset on :8000.
    ( cd "$BACKOFFICE" && VITE_APP_ORIGIN=http://localhost:8000 nohup npm run dev > "$bv_log" 2>&1 & )

    echo "[dev] waiting for Curator health…"
    for _ in $(seq 1 20); do curl -sf http://localhost:8060/healthz >/dev/null 2>&1 && break; sleep 2; done
    echo
    status
}

down() {
    echo "[dev] stopping apps (infra left running)…"
    _port_pids 8060 | xargs -r kill 2>/dev/null
    _proc_pids "main.py env.local.yaml --schedule" | xargs -r kill 2>/dev/null
    _proc_pids "main.py --config env.local.yaml --consume" | xargs -r kill 2>/dev/null
    # Reader (next dev) — kill the npm + next-server on :3000
    _port_pids 3000 | xargs -r kill 2>/dev/null
    # Backoffice — artisan serve (:8000) + its vite
    _port_pids 8000 | xargs -r kill 2>/dev/null
    _proc_pids "artisan serve" | xargs -r kill 2>/dev/null
    sleep 1
    echo "[dev] done. (Infra still up — use orchestrator/scripts/down.sh to stop it.)"
}

status() {
    echo "── InkBytes local pipeline ─────────────────────────────"
    printf "infra     : "; docker ps --format '{{.Names}}' 2>/dev/null | grep -qE 'dev-postgres' && echo "up" || echo "DOWN (run up.sh infra)"
    printf "ollama    : "; curl -sf http://localhost:11434/api/tags >/dev/null 2>&1 && echo "up (:11434)" || echo "DOWN"
    printf "curator   : "; curl -sf http://localhost:8060/healthz >/dev/null 2>&1 && echo "up (:8060)" || echo "DOWN"
    printf "messor    : "; [ -n "$(_proc_pids 'main.py env.local.yaml --schedule')" ] && echo "up (--schedule)" || echo "DOWN"
    printf "reader    : "; [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null)" = "200" ] && echo "up (:3000)" || echo "DOWN"
    printf "backoffice: "; c=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/ 2>/dev/null); [ "$c" = "200" ] || [ "$c" = "302" ] && echo "up (:8000)" || echo "DOWN"
    if curl -sf http://localhost:8060/status >/dev/null 2>&1; then
        curl -s http://localhost:8060/status 2>/dev/null | $CUR_PY -c "import sys,json;d=json.load(sys.stdin);print('pipeline  : articles=%s pending=%s events=%s pages=%s processing=%s'%(d['articles_total'],d['articles_pending'],d['events_total'],d['pages_published'],d.get('processing_enabled')))" 2>/dev/null
    fi
    echo "logs      : $LOGDIR/{curator,messor,reader}.log"
    echo "────────────────────────────────────────────────────────"
}

case "${1:-up}" in
    up)     up ;;
    down)   down ;;
    status) status ;;
    logs)   tail -n 40 -F "$c_log" "$m_log" "$r_log" ;;
    *)      echo "usage: $0 {up|down|status|logs}"; exit 1 ;;
esac
