#!/usr/bin/env bash
set -Eeuo pipefail

: "${POSTGRES_HOST:?}"
: "${POSTGRES_USER:?}"
: "${POSTGRES_PASSWORD:?}"
: "${POSTGRES_DB:?}"

export PGPASSWORD="$POSTGRES_PASSWORD"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
timestamp=$(date -u +'%Y%m%dT%H%M%SZ')
base="markettracker_${POSTGRES_DB}_${timestamp}"
tmp="/backups/.${base}.dump.tmp"
dump="/backups/${base}.dump"
checksum="${dump}.sha256"
metadata="${dump}.metadata"

cleanup() { rm -f "$tmp"; }
trap cleanup EXIT

pg_dump \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --format custom \
  --compress 6 \
  --no-owner \
  --no-acl \
  --file "$tmp"

test -s "$tmp"
pg_restore --list "$tmp" >/dev/null
mv "$tmp" "$dump"
(cd "$(dirname "$dump")" && sha256sum "$(basename "$dump")" > "$(basename "$checksum")")
cat > "$metadata" <<EOF
created_at_utc=$timestamp
database=$POSTGRES_DB
postgres_major=16
format=pg_dump_custom
EOF

if [[ -n "${RCLONE_REMOTE:-}" && -n "${RCLONE_DESTINATION:-}" ]]; then
  destination="${RCLONE_REMOTE}:${RCLONE_DESTINATION%/}/$base"
  rclone copy "$dump" "$destination"
  rclone copy "$checksum" "$destination"
  rclone copy "$metadata" "$destination"
fi

find /backups -maxdepth 1 -type f -name 'markettracker_*.dump*' \
  -mtime "+$BACKUP_RETENTION_DAYS" -delete

echo "[BACKUP] Completado: $dump"
