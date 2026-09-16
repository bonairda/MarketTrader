#!/usr/bin/env bash
set -Eeuo pipefail

interval="${BACKUP_INTERVAL_SECONDS:-86400}"

if [[ "${BACKUP_ON_START:-false}" == "true" ]]; then
  /opt/markettracker/backup.sh
fi

while true; do
  sleep "$interval"
  /opt/markettracker/backup.sh || echo "[BACKUP] Error; se reintentará en $interval segundos" >&2
done
