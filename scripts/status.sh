#!/usr/bin/env bash
set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_DIR/.uvicorn.pid"
LOG_FILE="$PROJECT_DIR/logs/api.log"
HEALTH_URL="http://127.0.0.1:8765/health"
RUNNING=false

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  echo "PID: $PID"
  if [[ "$PID" =~ ^[0-9]+$ ]] && kill -0 "$PID" 2>/dev/null; then
    COMMAND="$(tr '\0' ' ' <"/proc/$PID/cmdline" 2>/dev/null || true)"
    if [[ "$COMMAND" == *"uvicorn app.main:app"* ]]; then
      RUNNING=true
      echo "Process: running"
    else
      echo "Process: PID belongs to another command"
    fi
  else
    echo "Process: not running (stale PID file)"
  fi
else
  echo "PID: not found"
  echo "Process: not running"
fi

if HEALTH="$(curl -fsS --max-time 3 "$HEALTH_URL" 2>/dev/null)"; then
  echo "Health: ok $HEALTH"
else
  echo "Health: unavailable"
fi

if [[ -s "$LOG_FILE" ]]; then
  echo "Last log: $(tail -n 1 "$LOG_FILE")"
else
  echo "Last log: unavailable"
fi

if [[ "$RUNNING" == true ]]; then
  exit 0
fi
exit 1
