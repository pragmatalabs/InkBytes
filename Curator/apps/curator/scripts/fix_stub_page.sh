#!/usr/bin/env bash
#
# fix_stub_page.sh — re-synthesize one event through the real Phase 2.3 command
# path so a page that was written in STUB mode (no API keys) gets real content.
#
# It runs the canonical Backoffice → Curator flow end-to-end:
#   1. boots `main.py --consume-commands` (sole consumer on curator.commands)
#   2. publishes an `event.resynthesize` command to RabbitMQ
#   3. waits for the dispatch, then verifies the DB row in public.pages
#   4. shuts the consumer down cleanly
#
# Keys: provide ANTHROPIC_API_KEY + OPENAI_API_KEY by either
#   (a) exporting them before calling, or
#   (b) letting the script prompt you (hidden input).
# Without real keys Curator falls into STUB mode; the script detects that and
# aborts BEFORE publishing, so it can never re-stub the page.
#
# Usage (from apps/curator, or anywhere — it cd's itself):
#   bash scripts/fix_stub_page.sh [EVENT_ID] [CONFIG]
# Defaults: EVENT_ID=01KT5E6AYJW4014BEYM5V0Z6B7  CONFIG=env.local.yaml
#
set -euo pipefail

EVENT_ID="${1:-01KT5E6AYJW4014BEYM5V0Z6B7}"
CONFIG="${2:-env.local.yaml}"
STUB_HEADLINE="Stub one-pager (offline dev)"

# Resolve apps/curator (this file lives in apps/curator/scripts/).
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

PSQL=(docker exec -i inkbytes-dev-postgres psql -U inkbytes -d inkbytes -tA)
q() { "${PSQL[@]}" -c "$1"; }

note() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
die()  { printf '\033[31mFAIL: %s\033[0m\n' "$*" >&2; exit 1; }

# ── 1. keys ────────────────────────────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  read -rs -p "ANTHROPIC_API_KEY: " ANTHROPIC_API_KEY; echo
fi
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  read -rs -p "OPENAI_API_KEY: " OPENAI_API_KEY; echo
fi
export ANTHROPIC_API_KEY OPENAI_API_KEY
[[ -n "${ANTHROPIC_API_KEY}" && "${ANTHROPIC_API_KEY}" != "LOCAL_DEV_UNSET" ]] \
  || die "ANTHROPIC_API_KEY empty/placeholder — would run in STUB mode."
[[ -n "${OPENAI_API_KEY}" && "${OPENAI_API_KEY}" != "LOCAL_DEV_UNSET" ]] \
  || die "OPENAI_API_KEY empty/placeholder — would run in STUB mode."

# ── 2. preconditions ─────────────────────────────────────────────────────--
note "Preconditions"
[[ -d .venv ]] || die "no .venv in $APP_DIR"
# shellcheck disable=SC1091
source .venv/bin/activate

# .venv/bin/python is a universal (x86_64 + arm64) binary and inherits the
# parent shell's architecture. If this terminal runs under Rosetta, even
# `uname -m` reports x86_64, so we can't trust it. The native wheels
# (pydantic_core, asyncpg…) are built for one arch; probe both slices and pick
# whichever one actually imports pydantic_core.
PY=(python)
if command -v arch >/dev/null 2>&1; then
  picked=""
  for cand in arm64 x86_64; do
    if arch "-${cand}" python -c "import pydantic_core" 2>/dev/null; then
      PY=(arch "-${cand}" python); picked="${cand}"; break
    fi
  done
  [[ -n "${picked}" ]] || die "venv cannot import pydantic_core under arm64 or x86_64 — rebuild the venv (see scripts/fix_stub_page.sh header)."
  echo "python arch: ${picked}"
else
  python -c "import pydantic_core" 2>/dev/null \
    || die "venv cannot import pydantic_core — rebuild the venv."
fi

q "SELECT 1;" >/dev/null || die "cannot reach Postgres (is the dev stack up?)"

# Refuse to run if someone else already owns the commands queue — otherwise
# RabbitMQ round-robins and our command might be applied by another consumer.
consumers="$(docker exec messor-dev-rabbitmq rabbitmqctl list_queues name consumers 2>/dev/null \
             | awk '$1=="curator.commands"{print $2}')"
if [[ -n "${consumers:-}" && "${consumers}" != "0" ]]; then
  die "curator.commands already has ${consumers} consumer(s) — stop them first so this command isn't stolen."
fi

events0="$(q "SELECT count(*) FROM public.events;")"
pages0="$(q "SELECT count(*) FROM public.pages;")"
before="$(q "SELECT headline FROM public.pages WHERE id='${EVENT_ID}';")"
[[ -n "${before}" ]] || die "no page row for id=${EVENT_ID}"
echo "baseline: events=${events0} pages=${pages0}"
echo "page headline before: ${before}"

# ── 3. start the command consumer ───────────────────────────────────────--
note "Starting --consume-commands"
LOG="$(mktemp -t curator-cmd.XXXXXX).log"
"${PY[@]}" main.py --config "${CONFIG}" --consume-commands >"${LOG}" 2>&1 &
CONSUMER_PID=$!
cleanup() {
  kill "${CONSUMER_PID}" 2>/dev/null || true
  wait "${CONSUMER_PID}" 2>/dev/null || true
}
trap cleanup EXIT

# Wait for "Consuming commands exchange=" (ready) — abort if it falls into STUB.
ready=""
for _ in $(seq 1 60); do
  if grep -q "STUB mode" "${LOG}"; then
    cat "${LOG}"; die "Curator entered STUB mode — keys not applied."
  fi
  if grep -q "Consuming commands exchange=" "${LOG}"; then ready=1; break; fi
  kill -0 "${CONSUMER_PID}" 2>/dev/null || { cat "${LOG}"; die "consumer exited early."; }
  sleep 1
done
[[ -n "${ready}" ]] || { cat "${LOG}"; die "consumer never became ready."; }
echo "consumer ready (log: ${LOG})"

# ── 4. publish the command ──────────────────────────────────────────────--
note "Publishing event.resynthesize ${EVENT_ID}"
"${PY[@]}" scripts/publish_command.py event.resynthesize "${EVENT_ID}" "${CONFIG}"

# ── 5. wait for the dispatch to complete ────────────────────────────────--
done_line="event.resynthesize ${EVENT_ID} dispatched"
got=""
for _ in $(seq 1 120); do
  if grep -qF "${done_line}" "${LOG}"; then got=1; break; fi
  kill -0 "${CONSUMER_PID}" 2>/dev/null || { cat "${LOG}"; die "consumer died mid-dispatch."; }
  sleep 1
done
[[ -n "${got}" ]] || { tail -n 40 "${LOG}"; die "no dispatch confirmation within timeout."; }
echo "dispatch confirmed."

# ── 6. verify the DB row ────────────────────────────────────────────────--
note "Verifying public.pages"
after="$(q "SELECT headline FROM public.pages WHERE id='${EVENT_ID}';")"
synlen="$(q "SELECT length(synthesis_md) FROM public.pages WHERE id='${EVENT_ID}';")"
rail="$(q "SELECT coalesce(jsonb_array_length(evidence_rail),0) FROM public.pages WHERE id='${EVENT_ID}';")"
pub="$(q "SELECT published_at FROM public.pages WHERE id='${EVENT_ID}';")"
events1="$(q "SELECT count(*) FROM public.events;")"
pages1="$(q "SELECT count(*) FROM public.pages;")"

echo "headline after : ${after}"
echo "synthesis chars: ${synlen}"
echo "evidence_rail  : ${rail} source(s)"
echo "published_at   : ${pub}"
echo "events=${events1} (was ${events0})  pages=${pages1} (was ${pages0})"

[[ "${after}" != "${STUB_HEADLINE}" ]] || die "headline is still the stub."
[[ -n "${pub}" ]]                       || die "published_at is NULL (should stay set)."
[[ "${events1}" == "${events0}" ]]      || die "event count changed ${events0} -> ${events1}."
[[ "${pages1}" == "${pages0}" ]]        || die "page count changed ${pages0} -> ${pages1}."

printf '\n\033[32mPASS — page %s re-synthesized with real content; counts unchanged.\033[0m\n' "${EVENT_ID}"
