#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
VOICE_HMONG_ENV="${VOICE_STUDIO_HMONG_VENV:-.venv-hmong}"
exec "$VOICE_HMONG_ENV/bin/python" hmong_launcher.py "$@"
