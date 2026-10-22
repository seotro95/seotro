#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.data/pip-cache}"
if command -v python3.12 >/dev/null; then
  VOICE_BOOTSTRAP_PYTHON=python3.12
elif command -v python3 >/dev/null; then
  VOICE_BOOTSTRAP_PYTHON=python3
else
  echo 'Cần Python 3.12 64-bit (và gói python3-venv trên Ubuntu), rồi chạy lại ./install.sh.' >&2
  exit 1
fi
exec "$VOICE_BOOTSTRAP_PYTHON" setup_local.py "$@"
