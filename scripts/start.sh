#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PID_FILE="$PROJECT_DIR/.uvicorn.pid"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/api.log"
HEALTH_URL="http://127.0.0.1:8765/health"

cd "$PROJECT_DIR"

if [[ ! -x "$VENV_DIR/bin/uvicorn" ]]; then
  echo "Missing $VENV_DIR/bin/uvicorn. Run: make setup" >&2
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if [[ "$PID" =~ ^[0-9]+$ ]] && kill -0 "$PID" 2>/dev/null; then
    COMMAND="$(tr '\0' ' ' <"/proc/$PID/cmdline" 2>/dev/null || true)"
    if [[ "$COMMAND" == *"uvicorn app.main:app"* ]]; then
      echo "chat-local-gemini is already running (PID $PID)."
      exit 0
    fi
  fi
  rm -f "$PID_FILE"
fi

if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
  echo "Port 8765 already serves chat-local-gemini without a managed PID." >&2
  echo "Stop the systemd service or the other process before using start.sh." >&2
  exit 1
fi

mkdir -p "$LOG_DIR"
source "$VENV_DIR/bin/activate"

if command -v setsid >/dev/null 2>&1; then
  nohup setsid uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8765 \
    >>"$LOG_FILE" 2>&1 </dev/null &
else
  nohup uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8765 \
    >>"$LOG_FILE" 2>&1 </dev/null &
fi

PID=$!
printf '%s\n' "$PID" >"$PID_FILE"

for _ in {1..30}; do
  if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "chat-local-gemini started (PID $PID)."
    echo "UI: http://127.0.0.1:8765/app"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

echo "Failed to start chat-local-gemini. Last log lines:" >&2
tail -n 20 "$LOG_FILE" >&2 || true
kill "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
