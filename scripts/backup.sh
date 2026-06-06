#!/usr/bin/env bash
# InkBytes — daily Postgres backup with 30-day rotation.
# Cron: 0 2 * * * /opt/inkbytes/scripts/backup.sh
set -euo pipefail

BACKUP_DIR="${1:-/var/backups/inkbytes}"
TS=$(date +%Y%m%d-%H%M%S)
FILE="inkbytes-${TS}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] Dumping inkbytes database..."
docker exec inkbytes-postgres pg_dump -U inkbytes inkbytes | gzip > "$BACKUP_DIR/$FILE"

# Verify backup is non-empty
[ -s "$BACKUP_DIR/$FILE" ] || {
    echo "[backup] ERROR: empty backup file — aborting"
    rm -f "$BACKUP_DIR/$FILE"
    exit 1
}

SIZE=$(du -h "$BACKUP_DIR/$FILE" | cut -f1)
echo "[backup] Saved: $BACKUP_DIR/$FILE ($SIZE)"

# Rotate backups older than 30 days
ROTATED=$(find "$BACKUP_DIR" -name "inkbytes-*.sql.gz" -mtime +30 -delete -print | wc -l)
echo "[backup] Rotated ${ROTATED} old backup(s)"

# Install cron line (idempotent):
# (crontab -l 2>/dev/null; echo "0 2 * * * /opt/inkbytes/scripts/backup.sh") | crontab -
