#!/usr/bin/env bash
# InkBytes — start/stop the continuous pipeline cycle (native Python, no Docker).
#
# Starts Messor in --schedule mode (harvests every 60 min, serves API on :8050)
# and Curator in --consume mode (articles + commands + session summaries).
# Both run as background processes with logs in orchestrator/logs/.
#
# Prerequisites:
#   1. bash orchestrator/scripts/up.sh       (infra: Postgres + RabbitMQ + MinIO)
#   2. ANTHROPIC_API_KEY set in env          (Curator needs it for enrich/synth)
#   3. env.local.yaml present in Messor/apps/scraper/ and Curator/apps/curator/
#
# Usage:
#   bash orchestrator/scripts/cycle.sh             # start cycle
#   bash orchestrator/scripts/cycle.sh stop        # stop cycle
#   bash orchestrator/scripts/cycle.sh status      # check running state
#   bash orchestrator/scripts/cycle.sh logs        # tail both log files

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MESSOR_DIR="$ROOT/Messor/apps/scraper"
CURATOR_DIR="$ROOT/Curator/apps/curator"
PID_DIR="$ROOT/orchestrator/.pids"
LOG_DIR="$ROOT/orchestrator/logs"
ACTION="${1:-start}"

mkdir -p "$PID_DIR" "$LOG_DIR"

_pid_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

case "$ACTION" in
  start)
    # Sanity: infra must be up
    if ! docker ps --filter "name=inkbytes-dev-postgres" --format "{{.Names}}" 2>/dev/null | grep -q inkbytes; then
      echo "✗ Infra not running — start it first:"
      echo "    bash orchestrator/scripts/up.sh"
      exit 1
    fi

    # Guard against double-start
    if _pid_running "$PID_DIR/messor.pid" || _pid_running "$PID_DIR/curator.pid"; then
      echo "✗ Cycle already running — use 'stop' first, or check 'status'."
      exit 1
    fi

    # ── Messor ─────────────────────────────────────────────────────────────
    echo "Starting Messor (--schedule)…"
    (
      cd "$MESSOR_DIR"
      nohup .venv/bin/python main.py env.local.yaml --schedule \
        >> "$LOG_DIR/messor.log" 2>&1 &
      echo $! > "$PID_DIR/messor.pid"
    )

    # ── Curator ────────────────────────────────────────────────────────────
    echo "Starting Curator (--consume)…"
    (
      cd "$CURATOR_DIR"
      nohup .venv/bin/python main.py --consume \
        >> "$LOG_DIR/curator.log" 2>&1 &
      echo $! > "$PID_DIR/curator.pid"
    )

    sleep 1  # let processes settle before reporting

    echo
    echo "✓ Cycle running"
    echo "  Messor:  PID $(cat "$PID_DIR/messor.pid")  — harvests every 60 min + API :8050"
    echo "  Curator: PID $(cat "$PID_DIR/curator.pid") — processes articles continuously + API :8060"
    echo "  Logs:    $LOG_DIR/{messor,curator}.log"
    echo
    echo "  tail:  bash orchestrator/scripts/cycle.sh logs"
    echo "  stop:  bash orchestrator/scripts/cycle.sh stop"
    ;;

  stop)
    stopped=0
    for svc in messor curator; do
      pid_file="$PID_DIR/$svc.pid"
      if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
          kill "$pid" && echo "Stopped $svc (PID $pid)"
          stopped=$((stopped + 1))
        else
          echo "$svc was not running (stale PID $pid)"
        fi
        rm -f "$pid_file"
      else
        echo "$svc was not started"
      fi
    done
    [ "$stopped" -gt 0 ] && echo "✓ Cycle stopped" || echo "(nothing to stop)"
    ;;

  status)
    all_ok=true
    for svc in messor curator; do
      pid_file="$PID_DIR/$svc.pid"
      if _pid_running "$pid_file"; then
        echo "✓ $svc  running (PID $(cat "$pid_file"))"
      else
        echo "✗ $svc  not running"
        all_ok=false
      fi
    done
    $all_ok && exit 0 || exit 1
    ;;

  logs)
    exec tail -f "$LOG_DIR/messor.log" "$LOG_DIR/curator.log"
    ;;

  *)
    echo "Usage: $0 [start|stop|status|logs]"
    exit 1
    ;;
esac
