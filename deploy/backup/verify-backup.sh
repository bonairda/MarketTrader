#!/usr/bin/env bash
set -Eeuo pipefail

backup="${1:?Uso: verify-backup.sh /backups/archivo.dump}"
test -s "$backup"
pg_restore --list "$backup" >/dev/null

checksum="${backup}.sha256"
[[ -f "$checksum" ]] || {
  echo "Falta el checksum obligatorio: $checksum" >&2
  exit 1
}
(cd "$(dirname "$backup")" && sha256sum --check "$(basename "$checksum")")

echo "[BACKUP] Verificación correcta: $backup"
