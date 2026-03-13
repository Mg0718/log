#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
FRONTEND_DIR="$ROOT_DIR/frontend"

backend_pid=""
frontend_pid=""

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

free_port_if_busy() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')"
  if [[ -n "${pids// }" ]]; then
    echo "Port $port is in use. Stopping existing listener(s): $pids"
    kill $pids >/dev/null 2>&1 || true
    sleep 1
  fi
}

cleanup() {
  echo
  echo "Shutting down development servers..."
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" >/dev/null 2>&1; then
    kill "$backend_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" >/dev/null 2>&1; then
    kill "$frontend_pid" >/dev/null 2>&1 || true
  fi
  wait >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

require_cmd lsof
require_cmd npm

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found at $PYTHON_BIN" >&2
  echo "Create it first, then rerun this script." >&2
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "Frontend directory not found at $FRONTEND_DIR" >&2
  exit 1
fi

free_port_if_busy "$BACKEND_PORT"
free_port_if_busy "$FRONTEND_PORT"

echo "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT ..."
cd "$ROOT_DIR"
"$PYTHON_BIN" -m uvicorn backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload &
backend_pid=$!

echo "Starting frontend on http://localhost:$FRONTEND_PORT ..."
cd "$FRONTEND_DIR"
npm run dev -- --port "$FRONTEND_PORT" &
frontend_pid=$!

echo
echo "LogosGotham is starting."
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
echo "Health:   http://$BACKEND_HOST:$BACKEND_PORT/api/health"
echo
echo "Demo logins:"
echo "  admin / admin123"
echo "  seller / seller123"
echo "  receiver / receiver123"
echo
echo "Press Ctrl-C to stop both servers."

wait