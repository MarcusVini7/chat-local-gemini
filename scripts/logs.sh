#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/api.log"

mkdir -p "$PROJECT_DIR/logs"
touch "$LOG_FILE"
exec tail -f "$LOG_FILE"
