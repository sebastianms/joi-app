#!/usr/bin/env bash
# Levanta backend (uvicorn) y frontend (next dev) en local para desarrollo.
# Usage: ./dev.sh [KEY=VALUE ...]   — pasa overrides de env al backend
#
# Ctrl+C detiene ambos procesos.

set -euo pipefail
cd "$(dirname "$0")"

# ── Matar procesos previos ────────────────────────────────────────────────────
if pkill -f "next dev" 2>/dev/null; then
  echo "[dev.sh] Deteniendo next dev anterior…"
  sleep 1
fi
if lsof -ti:8000 &>/dev/null; then
  echo "[dev.sh] Deteniendo proceso existente en :8000…"
  kill $(lsof -ti:8000) 2>/dev/null || true
  sleep 1
fi

# ── Backend ───────────────────────────────────────────────────────────────────
echo "[dev.sh] Iniciando backend en :8000…"
(cd backend && bash dev.sh "$@") &
BACKEND_PID=$!

# Esperar a que el backend responda antes de arrancar el frontend
echo "[dev.sh] Esperando a que el backend esté listo…"
for i in $(seq 1 20); do
  if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "[dev.sh] Backend listo."
    break
  fi
  sleep 1
done

# ── Frontend ──────────────────────────────────────────────────────────────────
echo "[dev.sh] Iniciando frontend en :3000…"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

# ── Limpieza al salir ─────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "[dev.sh] Deteniendo procesos…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  echo "[dev.sh] Listo."
}
trap cleanup EXIT INT TERM

echo "[dev.sh] Todo corriendo. Ctrl+C para detener."
echo "  Backend:  http://127.0.0.1:8000"
echo "  Frontend: http://localhost:3000"
wait
