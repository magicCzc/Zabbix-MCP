#!/usr/bin/env bash
# Copyright (c) 2025 Zabbix-MCP
# Licensed under the Apache License, Version 2.0

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
PORT="${PORT:-5656}"
HOST="${HOST:-0.0.0.0}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

PY=python3.8
if ! command -v $PY >/dev/null 2>&1; then
  PY=python3
fi

if [ ! -d ".venv" ]; then
  $PY -m venv .venv
fi
. .venv/bin/activate

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/service_$(date +%Y%m%d_%H%M%S).log"

echo "Python version" | tee -a "$LOG_FILE"
python --version 2>&1 | tee -a "$LOG_FILE"

echo "Installing dependencies (pip upgrade)" | tee -a "$LOG_FILE"
python -m pip install -U pip 2>&1 | tee -a "$LOG_FILE"
if [ -f requirements.txt ]; then
  echo "Installing dependencies from requirements.txt" | tee -a "$LOG_FILE"
  python -m pip install -r requirements.txt 2>&1 | tee -a "$LOG_FILE"
else
  echo "requirements.txt not found; installing project editable" | tee -a "$LOG_FILE"
  python -m pip install -e . 2>&1 | tee -a "$LOG_FILE"
fi

echo "Starting server on $HOST:$PORT" | tee -a "$LOG_FILE"
uvicorn zabbix_mcp.api:app --host "$HOST" --port "$PORT" 2>&1 | tee -a "$LOG_FILE"
