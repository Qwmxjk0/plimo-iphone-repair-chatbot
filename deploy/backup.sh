#!/usr/bin/env bash
# Daily backup: consistent SQLite copy (members, cases, payments) + LightRAG index. Keeps 7 days.
set -euo pipefail
cd "${PLIMO_DIR:-$(pwd)}"
COMPOSE="docker compose -f compose.yaml -f compose.prod.yaml --profile rag"
DEST="${PLIMO_BACKUP_DIR:-/var/backups/plimo}"; STAMP="$(date +%Y%m%d-%H%M)"
mkdir -p "$DEST" && chmod 700 "$DEST"
$COMPOSE exec -T api python -c "import sqlite3;s=sqlite3.connect('/app/data/members.sqlite3');d=sqlite3.connect('/app/data/.backup.sqlite3');s.backup(d);d.close()"
$COMPOSE exec -T api cat /app/data/.backup.sqlite3 > "$DEST/members-$STAMP.sqlite3"
$COMPOSE exec -T api rm -f /app/data/.backup.sqlite3
$COMPOSE exec -T lightrag tar czf - -C /app/data/rag_storage . > "$DEST/rag-$STAMP.tgz"
# Chat images kept on disk (when R2 is not configured; R2 has its own durability).
$COMPOSE exec -T api sh -c 'test -d /app/data/images && tar czf - -C /app/data images || true' > "$DEST/images-$STAMP.tgz"
find "$DEST" -type f -mtime +7 -delete
echo "backup ok $STAMP $(du -sh "$DEST" | cut -f1)"
