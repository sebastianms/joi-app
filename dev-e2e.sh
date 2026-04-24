#!/usr/bin/env bash
# dev-e2e.sh — arranca backend con MOCK_LLM_RESPONSES=true + frontend + corre Playwright.
#
# Uso:
#   ./dev-e2e.sh                              # corre toda la suite E2E
#   ./dev-e2e.sh e2e/quickstart-scenarios.spec.ts   # un spec específico
#
# No consume tokens LLM — todas las respuestas salen del MockLLMRouter.

set -euo pipefail
cd "$(dirname "$0")"

BACKEND_PORT=8000
FRONTEND_PORT=3000
QDRANT_PORT=6333
BACKEND_LOG=".e2e-backend.log"
FRONTEND_LOG=".e2e-frontend.log"
QDRANT_LOG=".e2e-qdrant.log"

cleanup() {
  echo "[dev-e2e] Cleanup…"
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
  if lsof -ti:$BACKEND_PORT &>/dev/null; then kill "$(lsof -ti:$BACKEND_PORT)" 2>/dev/null || true; fi
  if lsof -ti:$FRONTEND_PORT &>/dev/null; then kill "$(lsof -ti:$FRONTEND_PORT)" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

# Kill stragglers from previous runs
if lsof -ti:$BACKEND_PORT &>/dev/null; then
  echo "[dev-e2e] Stopping existing process on :$BACKEND_PORT…"
  kill "$(lsof -ti:$BACKEND_PORT)" 2>/dev/null || true
  sleep 1
fi
if lsof -ti:$FRONTEND_PORT &>/dev/null; then
  echo "[dev-e2e] Stopping existing process on :$FRONTEND_PORT…"
  kill "$(lsof -ti:$FRONTEND_PORT)" 2>/dev/null || true
  sleep 1
fi

echo "[dev-e2e] Building widget runtime bundle…"
(cd frontend && npm run build:widget-runtime --silent)

# Qdrant: reuse if already listening; otherwise launch via docker compose.
if curl -fsS "http://127.0.0.1:$QDRANT_PORT/readyz" &>/dev/null; then
  echo "[dev-e2e] Qdrant already reachable on :$QDRANT_PORT — reusing."
else
  echo "[dev-e2e] Starting Qdrant on :$QDRANT_PORT via docker compose…"
  if ! docker compose up -d qdrant >"$QDRANT_LOG" 2>&1; then
    echo "[dev-e2e] docker compose failed (see $QDRANT_LOG). Start Qdrant manually and re-run."
    tail -10 "$QDRANT_LOG"
    exit 1
  fi
  echo "[dev-e2e] Waiting for Qdrant…"
  for i in {1..30}; do
    if curl -fsS "http://127.0.0.1:$QDRANT_PORT/readyz" &>/dev/null; then
      echo "[dev-e2e] Qdrant ready."
      break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
      echo "[dev-e2e] Qdrant failed to start. Tail of $QDRANT_LOG:"
      tail -30 "$QDRANT_LOG"
      exit 1
    fi
  done
fi

echo "[dev-e2e] Starting backend on :$BACKEND_PORT with MOCK_LLM_RESPONSES=true…"
(cd backend && MOCK_LLM_RESPONSES=true \
  VECTOR_STORE_ENCRYPTION_KEY="${VECTOR_STORE_ENCRYPTION_KEY:-0000000000000000000000000000000000000000000000000000000000000000}" \
  .venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port $BACKEND_PORT --env-file .env >"../$BACKEND_LOG" 2>&1) &
BACKEND_PID=$!

echo "[dev-e2e] Starting frontend on :$FRONTEND_PORT…"
(cd frontend && npm run dev --silent >"../$FRONTEND_LOG" 2>&1) &
FRONTEND_PID=$!

# Wait for backend
echo "[dev-e2e] Waiting for backend…"
for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/docs" &>/dev/null; then
    echo "[dev-e2e] Backend ready."
    break
  fi
  sleep 1
  if [[ $i -eq 30 ]]; then
    echo "[dev-e2e] Backend failed to start. Tail of $BACKEND_LOG:"
    tail -30 "$BACKEND_LOG"
    exit 1
  fi
done

# Wait for frontend
echo "[dev-e2e] Waiting for frontend…"
for i in {1..60}; do
  if curl -fsS "http://127.0.0.1:$FRONTEND_PORT/" &>/dev/null; then
    echo "[dev-e2e] Frontend ready."
    break
  fi
  sleep 1
  if [[ $i -eq 60 ]]; then
    echo "[dev-e2e] Frontend failed to start. Tail of $FRONTEND_LOG:"
    tail -30 "$FRONTEND_LOG"
    exit 1
  fi
done

echo "[dev-e2e] Running Playwright…"
cd frontend
if [[ $# -gt 0 ]]; then
  npx playwright test "$@"
else
  npx playwright test
fi
