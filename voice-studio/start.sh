#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
VOICE_PYTHON="${VOICE_STUDIO_PYTHON:-.venv/bin/python}"
exec "$VOICE_PYTHON" -m uvicorn app:app --host 127.0.0.1 --port 8770 --no-access-log
