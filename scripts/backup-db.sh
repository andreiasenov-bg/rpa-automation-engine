#!/bin/bash
# Automated PostgreSQL backup script
# Runs via cron: daily at 3:00 AM

set -euo pipefail

BACKUP_DIR="/opt/rpa-engine/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/rpa_db_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Run pg_dump inside the postgres container and compress
docker exec rpa-postgres pg_dump -U rpa_user -d rpa_engine --no-owner --no-privileges | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup OK: $BACKUP_FILE ($SIZE)"

    # Clean old backups
    find "$BACKUP_DIR" -name "rpa_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    REMAINING=$(ls -1 "$BACKUP_DIR"/rpa_db_*.sql.gz 2>/dev/null | wc -l)
    echo "[$(date)] Retention: keeping $REMAINING backups (last $RETENTION_DAYS days)"
else
    echo "[$(date)] ERROR: Backup failed!" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi
