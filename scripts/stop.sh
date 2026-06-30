#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_DIR/.uvicorn.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "chat-local-gemini is not running (PID file not found)."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [[ ! "$PID" =~ ^[0-9]+$ ]] || ! kill -0 "$PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Removed stale PID file."
  exit 0
fi

COMMAND="$(tr '\0' ' ' <"/proc/$PID/cmdline" 2>/dev/null || true)"
if [[ "$COMMAND" != *"uvicorn app.main:app"* ]]; then
  rm -f "$PID_FILE"
  echo "PID $PID does not belong to chat-local-gemini; process was not stopped." >&2
  exit 1
fi

kill "$PID"
for _ in {1..20}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "chat-local-gemini stopped."
    exit 0
  fi
  sleep 0.25
done

echo "Process $PID did not stop after 5 seconds; sending SIGKILL." >&2
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "chat-local-gemini stopped."
