#!/usr/bin/env bash
set -Eeuo pipefail

: "${APP_URL:?APP_URL es obligatorio}"
: "${API_URL:?API_URL es obligatorio}"
: "${EXPECTED_REVISION:?EXPECTED_REVISION es obligatorio}"
command -v jq >/dev/null || { echo "jq es obligatorio" >&2; exit 1; }

APP_URL="${APP_URL%/}"
API_URL="${API_URL%/}"
CURL=(curl --fail --silent --show-error --retry 5 --retry-delay 3 --retry-all-errors)

# Espera al release exacto, no acepta que siga respondiendo la versión anterior.
ready=false
for _ in $(seq 1 60); do
  config=$(curl --silent --show-error "$APP_URL/config.json" 2>/dev/null || true)
  health=$(curl --silent --show-error "$API_URL/health/system" 2>/dev/null || true)
  config_api=$(printf '%s' "$config" | jq -r '.apiBaseUrl // empty' 2>/dev/null || true)
  config_revision=$(printf '%s' "$config" | jq -r '.revision // empty' 2>/dev/null || true)
  api_revision=$(printf '%s' "$health" | jq -r '.revision // empty' 2>/dev/null || true)
  status=$(printf '%s' "$health" | jq -r '.status // empty' 2>/dev/null || true)
  worker=$(printf '%s' "$health" | jq -r '.checks.worker // false' 2>/dev/null || true)
  if [[ "$config_api" == "$API_URL" \
        && "$config_revision" == "$EXPECTED_REVISION" \
        && "$api_revision" == "$EXPECTED_REVISION" \
        && "$status" == "ok" \
        && "$worker" == "true" ]]; then
    ready=true
    break
  fi
  sleep 5
done

[[ "$ready" == "true" ]] || {
  echo "El release $EXPECTED_REVISION no quedó saludable en 5 minutos" >&2
  exit 1
}

"${CURL[@]}" "$APP_URL/healthz" | grep -q '^ok'
"${CURL[@]}" "$APP_URL/" >/dev/null

cors_headers=$(mktemp)
trap 'rm -f "$cors_headers"' EXIT
curl --fail --silent --show-error --request OPTIONS \
  --header "Origin: $APP_URL" \
  --header "Access-Control-Request-Method: POST" \
  --dump-header "$cors_headers" --output /dev/null \
  "$API_URL/auth/login"
grep -Eiq "^access-control-allow-origin:[[:space:]]*$APP_URL" "$cors_headers"

if [[ -n "${SMOKE_EMAIL:-}" && -n "${SMOKE_PASSWORD:-}" ]]; then
  body=$(jq -n --arg email "$SMOKE_EMAIL" --arg password "$SMOKE_PASSWORD" \
    '{email: $email, password: $password}')
  login=$("${CURL[@]}" --header 'Content-Type: application/json' \
    --data "$body" "$API_URL/auth/login")
  token=$(printf '%s' "$login" | jq -er '.token')
  "${CURL[@]}" --header "Authorization: Bearer $token" "$API_URL/auth/me" >/dev/null
  "${CURL[@]}" --header "Authorization: Bearer $token" "$API_URL/watchlist" >/dev/null
fi

echo "[SMOKE] Release $EXPECTED_REVISION, app, API, worker y CORS correctos"
