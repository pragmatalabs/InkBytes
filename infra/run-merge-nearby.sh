#!/usr/bin/env bash
# InkBytes — near-duplicate event merge pass (ADR-0040), scheduled.
#
# Consolidates published events whose centroids are within MERGE_DISTANCE
# (default 0.12 — the precision-safe threshold validated on prod: it catches
# true dups like the Venezuela-earthquake / US-Iran / World-Cup fragments while
# leaving genuinely distinct-but-similar events alone). Each run merges the new
# near-dups that formed since last time and re-synthesizes the survivors.
#
# Runs a few times a day via cron (a one-shot container; the running Curator
# services are untouched):
#   crontab -e →
#   20 */6 * * * /opt/inkbytes/infra/run-merge-nearby.sh >> /var/log/inkbytes-merge.log 2>&1
#
# Contains NO secrets — reads them from infra/.env at runtime. To pause the pass,
# comment out the crontab line (or set MERGE_DISTANCE=0 to make it a no-op).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

exec docker compose \
  -f infra/docker-compose.prod.yml -f infra/docker-compose.do.yml \
  --env-file infra/.env run --rm --no-deps inkbytes-curator-worker \
  python main.py --config env.yaml --merge-nearby --merge-apply \
  --merge-distance "${MERGE_DISTANCE:-0.12}" \
  --since-hours "${MERGE_SINCE_HOURS:-48}"
