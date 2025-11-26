#!/usr/bin/env bash
# Copyright (c) 2025 Zabbix-MCP
# Licensed under the Apache License, Version 2.0

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
BASE_URL="${BASE_URL:-http://127.0.0.1:5656}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

READ_TOKEN="${MCP_AUTH_TOKEN_READ:-}"
ADMIN_TOKEN="${MCP_AUTH_TOKEN_ADMIN:-}"
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
REPORT="$LOG_DIR/smoke_$(date +%Y%m%d_%H%M%S).log"

get() {
  local path="$1"; local token="$2"
  local start_ms=$(python - <<'PY'
import time
print(int(time.time()*1000))
PY
)
  set +e
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $token" "$BASE_URL$path")
  set -e
  end_ms=$(python - <<'PY'
import time
print(int(time.time()*1000))
PY
)
  echo "GET $path $http_code $((end_ms-start_ms))ms" | tee -a "$REPORT"
}

post() {
  local path="$1"; shift
  local token="$1"; shift
  local data="$1"
  local start_ms=$(python - <<'PY'
import time
print(int(time.time()*1000))
PY
)
  set +e
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d "$data" "$BASE_URL$path")
  set -e
  end_ms=$(python - <<'PY'
import time
print(int(time.time()*1000))
PY
)
  echo "POST $path $http_code $((end_ms-start_ms))ms" | tee -a "$REPORT"
}

get "/health" "$READ_TOKEN"
get "/metrics" "$READ_TOKEN"
get "/version" "$READ_TOKEN"
get "/alerts/today?limit=5" "$READ_TOKEN"
get "/alerts/top?by=severity&limit=5" "$READ_TOKEN"

post "/alerts/query" "$READ_TOKEN" '{"severities":[4],"limit":5}'
post "/alerts/nl" "$READ_TOKEN" '{"text":"今日告警 top5 按严重"}'
post "/logs/associate" "$READ_TOKEN" '{"keywords":["Processor","load"],"limit":5}'

# Admin endpoints expected forbidden in READ_ONLY
post "/config/reload" "$ADMIN_TOKEN" '{}'
post "/queue/enqueue" "$ADMIN_TOKEN" '{}'
get "/queue/stats" "$ADMIN_TOKEN"
