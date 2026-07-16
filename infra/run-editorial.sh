#!/usr/bin/env bash
# InkBytes — "Today's [Topic] Outlook" daily editorial batch (ADR-0008).
#
# Invoked by cron at the 11:59 AM AST morning-briefing cut (= 15:59 UTC, which
# also sits OUTSIDE the DeepSeek peak-pricing window — ADR-0038). Generates one
# editorial per theme × language into the `editorials` table; the Curator
# /outlook API + Reader /outlook page read from it.
#
#   crontab -e  →  59 15 * * * /opt/inkbytes/infra/run-editorial.sh >> /var/log/inkbytes-editorial.log 2>&1
#
# Provider is a config flag (ADR-0008): defaults to DeepSeek (the droplet can't
# host the 12B quality floor). To flip to local gemma4 after the 16 GB upgrade,
# set EDITORIAL_LLM_PROVIDER/_BASE_URL/_MODEL in infra/.env — no code change.
# Contains NO secrets: it only reads them from infra/.env at runtime.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a; source "$SCRIPT_DIR/.env"; set +a

NETWORK="${EDITORIAL_NETWORK:-inkbytes_inkbytes-internal}"
DBURL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@inkbytes-postgres:5432/${POSTGRES_DB:-inkbytes}"

# TTS synthesis is REMOTE (ADR-0011): the batch POSTs to the Piper microservice on
# the 16 GB box, so this container is light (text + a network call + Spaces upload).
# No CPU/memory cap needed — the onnxruntime RAM that swap-thrashed the droplet now
# lives off-box. (If EDITORIAL_TTS_URL is unset the batch just skips audio; it will
# NOT synthesize locally on the droplet — the image ships no Piper.)
exec docker run --rm --network "$NETWORK" \
  -e DATABASE_URL="$DBURL" \
  -e EDITORIAL_LLM_PROVIDER="${EDITORIAL_LLM_PROVIDER:-deepseek}" \
  -e EDITORIAL_LLM_BASE_URL="${EDITORIAL_LLM_BASE_URL:-https://api.deepseek.com/v1}" \
  -e EDITORIAL_LLM_MODEL="${EDITORIAL_LLM_MODEL:-deepseek-chat}" \
  -e EDITORIAL_LLM_API_KEY="${EDITORIAL_LLM_API_KEY:-${DEEPSEEK_API_KEY:-}}" \
  -e PUSH_TRIGGER_SECRET="${PUSH_TRIGGER_SECRET:-}" \
  -e CURATOR_INTERNAL_URL="${CURATOR_INTERNAL_URL:-http://inkbytes-curator-api:8060}" \
  -e EDITORIAL_TTS_ENABLED="${EDITORIAL_TTS_ENABLED:-true}" \
  -e EDITORIAL_TTS_URL="${EDITORIAL_TTS_URL:-}" \
  -e EDITORIAL_TTS_SECRET="${EDITORIAL_TTS_SECRET:-}" \
  -e EDITORIAL_TTS_CONCURRENCY="${EDITORIAL_TTS_CONCURRENCY:-1}" \
  -e EDITORIAL_TTS_VOICE_EN="${EDITORIAL_TTS_VOICE_EN:-}" \
  -e EDITORIAL_TTS_VOICE_ES="${EDITORIAL_TTS_VOICE_ES:-}" \
  -e DO_SPACES_ENDPOINT="${DO_SPACES_ENDPOINT:-}" \
  -e DO_SPACES_REGION="${DO_SPACES_REGION:-nyc3}" \
  -e DO_SPACES_BUCKET="${DO_SPACES_BUCKET:-}" \
  -e DO_SPACES_KEY="${DO_SPACES_KEY:-}" \
  -e DO_SPACES_SECRET="${DO_SPACES_SECRET:-}" \
  -e DO_SPACES_PUBLIC_BASE="${DO_SPACES_PUBLIC_BASE:-}" \
  inkbytes-editorial --generate "$@"
