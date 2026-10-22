#!/usr/bin/env bash
set -euo pipefail
export PYTHONUTF8=1
cd -- "$(dirname -- "$0")"
VOICE_ENV_DIR="${VOICE_STUDIO_VENV:-.venv}"
VOICE_PYTHON="${VOICE_STUDIO_PYTHON:-$VOICE_ENV_DIR/bin/python}"
if [ ! -x "$VOICE_PYTHON" ]; then
  echo 'Chạy bash install.sh trước, hoặc đặt VOICE_STUDIO_PYTHON tới Python đã cài thư viện.' >&2
  exit 1
fi
exec "$VOICE_PYTHON" portable_launcher.py
