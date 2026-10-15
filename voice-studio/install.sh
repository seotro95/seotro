#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
command -v ffmpeg >/dev/null || { echo 'Cần cài FFmpeg trước.' >&2; exit 1; }
command -v ffprobe >/dev/null
VOICE_ENV_DIR="${VOICE_STUDIO_VENV:-.venv}"
if [ ! -x "$VOICE_ENV_DIR/bin/python" ]; then python3.12 -m venv "$VOICE_ENV_DIR"; fi
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.data/pip-cache}"
if [ "$(uname -s)" = Linux ]; then
  "$VOICE_ENV_DIR/bin/python" -m pip install torch==2.14.1 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu
else
  "$VOICE_ENV_DIR/bin/python" -m pip install torch torchaudio
fi
"$VOICE_ENV_DIR/bin/python" -m pip install -r requirements-qwen.txt
"$VOICE_ENV_DIR/bin/python" -m pip check
printf '%s\n' 'Đã cài thư viện. Chạy python prepare_models.py all trong môi trường vừa tạo để tải mô hình, sau đó chạy start.sh.'
