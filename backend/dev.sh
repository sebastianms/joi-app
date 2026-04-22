#!/usr/bin/env bash
# Usage:
#   ./dev.sh                          # normal start, uses .env
#   ./dev.sh MAX_ROWS_PER_EXTRACTION=5
#   ./dev.sh QUERY_TIMEOUT_SECONDS=1 MOCK_LLM_RESPONSES=true
#
# Any KEY=VALUE arguments are injected as env overrides on top of .env.

set -euo pipefail
cd "$(dirname "$0")"

# Kill any previous uvicorn on port 8000
if lsof -ti:8000 &>/dev/null; then
  echo "[dev.sh] Stopping existing process on :8000…"
  kill "$(lsof -ti:8000)" 2>/dev/null || true
  sleep 1
fi

echo "[dev.sh] Starting backend${*:+ with overrides: $*}…"
env "$@" .venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --reload --env-file .env
