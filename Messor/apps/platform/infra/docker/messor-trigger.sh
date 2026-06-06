#!/bin/sh
# messor-trigger.sh — called by RunScrapingWorker as SCRAPING_COMMAND.
#
# Receives {SCRAPE_ARGS} from the worker, e.g.:
#   --scrape=--outlets=aljazeera,bbc --limit=50
#   --scrape                         (all outlets)
#
# Parses outlets + limit, POSTs to Messor's trigger endpoint over the
# internal Docker network, then tails the outcome.

set -e

ARGS="${*}"

# ── Extract --outlets=X from the scrape args string ──────────────────────────
OUTLETS=""
LIMIT=""

# The args look like: --scrape='--outlets=aljazeera,bbc --limit=50'
# or just: --scrape
INNER=$(echo "$ARGS" | sed -n "s/.*--scrape[= ]*'\{0,1\}\(.*\)'\{0,1\}/\1/p" | tr -d "'\"")

if [ -n "$INNER" ]; then
    OUTLETS=$(echo "$INNER" | grep -oE '\-\-outlets=[^ ]+' | sed 's/--outlets=//' || true)
    LIMIT=$(echo "$INNER" | grep -oE '\-\-limit=[0-9]+' | sed 's/--limit=//' || true)
fi

# ── Build JSON body ───────────────────────────────────────────────────────────
if [ -n "$OUTLETS" ] && [ -n "$LIMIT" ]; then
    SLUGS=$(echo "$OUTLETS" | sed 's/,/","/g')
    BODY="{\"outlet_slugs\":[\"${SLUGS}\"],\"limit\":${LIMIT}}"
elif [ -n "$OUTLETS" ]; then
    SLUGS=$(echo "$OUTLETS" | sed 's/,/","/g')
    BODY="{\"outlet_slugs\":[\"${SLUGS}\"]}"
elif [ -n "$LIMIT" ]; then
    BODY="{\"limit\":${LIMIT}}"
else
    BODY="{}"
fi

# ── Trigger ───────────────────────────────────────────────────────────────────
echo "[messor-trigger] Triggering Messor harvest"
echo "[messor-trigger] Outlets: ${OUTLETS:-all}"
echo "[messor-trigger] Limit:   ${LIMIT:-none}"
echo "[messor-trigger] Sending: POST http://inkbytes-messor:8050/api/scrape/trigger"

RESPONSE=$(curl -sf -X POST http://inkbytes-messor:8050/api/scrape/trigger \
    -H "Content-Type: application/json" \
    -d "$BODY" 2>&1) || {
    echo "[messor-trigger] ERROR: could not reach Messor API"
    exit 1
}

echo "[messor-trigger] Response: $RESPONSE"
echo "[messor-trigger] Scrape started — Messor harvesting in background."
echo "[messor-trigger] Articles will appear in Curator within a few minutes."
