#!/bin/sh
set -eu

: "${PUBLIC_API_BASE_URL:?PUBLIC_API_BASE_URL es obligatorio}"

case "$PUBLIC_API_BASE_URL" in
  https://*) ;;
  http://*)
    if [ "${REQUIRE_HTTPS:-false}" = "true" ]; then
      echo "PUBLIC_API_BASE_URL debe usar https:// en producción" >&2
      exit 1
    fi
    ;;
  *)
    echo "PUBLIC_API_BASE_URL debe comenzar por http:// o https://" >&2
    exit 1
    ;;
esac

escaped_url=$(printf '%s' "$PUBLIC_API_BASE_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')
escaped_revision=$(printf '%s' "${APP_REVISION:-unknown}" | sed 's/\\/\\\\/g; s/"/\\"/g')
printf '{"apiBaseUrl":"%s","revision":"%s"}\n' "$escaped_url" "$escaped_revision" \
  > /usr/share/nginx/html/config.json
