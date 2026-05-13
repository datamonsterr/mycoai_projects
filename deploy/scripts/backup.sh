#!/usr/bin/env bash
set -euo pipefail

MONOREPO_ROOT="${MYCOAI_ROOT:-/opt/mycoai}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

# ── PostgreSQL ──
echo "Backing up PostgreSQL..."
docker compose -f "$MONOREPO_ROOT/docker-compose.yml" exec -T postgres \
  pg_dump -U mycoai mycoai > "$BACKUP_DIR/pg_dump-$TIMESTAMP.sql"
gzip -f "$BACKUP_DIR/pg_dump-$TIMESTAMP.sql"

# ── Qdrant snapshot ──
echo "Backing up Qdrant..."
QDRANT_PORT="${QDRANT_PORT:-6333}"
curl -s -X POST "http://qdrant:$QDRANT_PORT/collections/mycoai/snapshots" \
  -H "Content-Type: application/json" \
  -d '{"snapshot_name": "backup-snapshot"}' || echo "Warning: Qdrant snapshot failed"

# ── File storage (uploads, weights) ──
echo "Backing up files..."
if command -v rclone &>/dev/null; then
  rclone sync "$MONOREPO_ROOT/weights/" "mydrive:mycoai-backups/weights/" --create-empty-src-dirs
  rclone sync "$MONOREPO_ROOT/uploads/" "mydrive:mycoai-backups/uploads/" --create-empty-src-dirs
else
  echo "Warning: rclone not installed, skipping file sync"
fi

# ── Retain last 7 PostgreSQL dumps ──
echo "Cleaning old backups..."
find "$BACKUP_DIR" -name "pg_dump-*.sql.gz" -type f | sort -r | tail -n +8 | xargs -r rm

echo "Backup complete: $TIMESTAMP"
