#!/usr/bin/env bash

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

stop_port() {
  local port="$1"
  local name="$2"
  local pids

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')"
  if [[ -z "${pids// }" ]]; then
    echo "$name is not running on port $port"
    return
  fi

  echo "Stopping $name on port $port: $pids"
  kill $pids >/dev/null 2>&1 || true
}

if ! command -v lsof >/dev/null 2>&1; then
  echo "Missing required command: lsof" >&2
  exit 1
fi

stop_port "$BACKEND_PORT" "backend"
stop_port "$FRONTEND_PORT" "frontend"

echo "Stop command complete."