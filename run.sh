#!/usr/bin/env bash
# Usage: bash run.sh [scans_folder]      (default: ./scans)
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$KIT/.venv/bin/python" ] || [ ! -f "$KIT/OMRChecker/main.py" ]; then
  echo "Run setup first:  bash setup.sh"; exit 1
fi
exec "$KIT/.venv/bin/python" "$KIT/omr.py" "$@"
