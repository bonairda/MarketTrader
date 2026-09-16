#!/usr/bin/env bash
set -Eeuo pipefail

backup="${1:?Uso: CONFIRM_RESTORE=<db> restore.sh /backups/archivo.dump}"
: "${POSTGRES_HOST:?}"
: "${POSTGRES_USER:?}"
: "${POSTGRES_PASSWORD:?}"
: "${POSTGRES_DB:?}"

if [[ "${CONFIRM_RESTORE:-}" != "$POSTGRES_DB" ]]; then
  echo "Restauración cancelada. Define CONFIRM_RESTORE=$POSTGRES_DB" >&2
  exit 2
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
restore_mode=false

finish_restore_mode() {
  local status="$1"
  trap - EXIT
  if [[ "$restore_mode" == "true" ]]; then
    psql --host "$POSTGRES_HOST" --port "$POSTGRES_PORT" \
      --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      --set ON_ERROR_STOP=1 --command "SELECT timescaledb_post_restore();" \
      || echo "[RESTORE] ERROR: ejecuta SELECT timescaledb_post_restore() manualmente" >&2
  fi
  exit "$status"
}
trap 'finish_restore_mode $?' EXIT

"/opt/markettracker/verify-backup.sh" "$backup"

psql --host "$POSTGRES_HOST" --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set ON_ERROR_STOP=1 --command "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# API y worker deben estar detenidos antes de ejecutar este script.
psql --host "$POSTGRES_HOST" --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set ON_ERROR_STOP=1 --command "SELECT timescaledb_pre_restore();"
restore_mode=true

pg_restore \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --clean --if-exists --no-owner --no-acl --exit-on-error \
  "$backup"

psql --host "$POSTGRES_HOST" --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set ON_ERROR_STOP=1 --command "SELECT timescaledb_post_restore();"
restore_mode=false
trap - EXIT

echo "[RESTORE] Restauración completada. Ejecuta migraciones y smoke test."
