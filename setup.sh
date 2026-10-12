#!/usr/bin/env bash
# One-time setup: downloads OMRChecker (pinned version) and installs everything into ./.venv
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
cd "$KIT"
COMMIT=5cf44a5a9c7a49e2e541c6e19aefd09a41a4d494

# 1. Find a Python 3.10+ (newest first)
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "ERROR: Python 3.10 or newer not found."
  echo "Install it from https://www.python.org/downloads/macos/ (or: brew install python@3.12), then run this again."
  exit 1
fi
echo "Using $($PY --version) at $(command -v $PY)"

# 2. Download OMRChecker
if [ ! -f "$KIT/OMRChecker/main.py" ]; then
  echo "Downloading OMRChecker..."
  rm -rf OMRChecker
  if curl -fsSL -o omrchecker.zip "https://github.com/udayraj123/OMRChecker/archive/$COMMIT.zip"; then
    unzip -q omrchecker.zip && mv "OMRChecker-$COMMIT" OMRChecker && rm omrchecker.zip
  else
    echo "Zip download failed, trying git..."
    git clone -q https://github.com/udayraj123/OMRChecker.git OMRChecker
    git -C OMRChecker checkout -q "$COMMIT"
  fi
fi

# 3. Virtual environment + packages
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
echo "Installing packages (takes a minute or two the first time)..."
.venv/bin/python -m pip install --quiet -r OMRChecker/requirements.txt opencv-python
.venv/bin/python -c "import cv2, numpy, pandas, pymupdf; print('Setup OK - OpenCV', cv2.__version__)"
echo
echo "Done. Put your scans in the 'scans' folder and run:  bash run.sh"
