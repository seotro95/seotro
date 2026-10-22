#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
VOICE_PYTHON="${VOICE_STUDIO_PYTHON:-${VOICE_STUDIO_VENV:-.venv}/bin/python}"
if [ -d .tools/ffmpeg/bin ]; then export PATH="$PWD/.tools/ffmpeg/bin:$PATH"; fi
VOICE_DATA_DIR="${VOICE_STUDIO_DATA_DIR:-$PWD/.data}"
if [ ! -x "$VOICE_PYTHON" ]; then
  if [ -n "${VOICE_STUDIO_PYTHON:-}" ]; then
    echo 'Không tìm thấy Python tại VOICE_STUDIO_PYTHON. Sửa đường dẫn hoặc bỏ biến này và chạy lại.' >&2
    exit 1
  fi
  ./install.sh
fi
if [ ! -f "$VOICE_DATA_DIR/models/vieneu_nano.ready" ] || [ ! -f "$VOICE_DATA_DIR/models/vieneu_nano_clone.ready" ]; then
  "$VOICE_PYTHON" prepare_models.py vi
fi
exec "$VOICE_PYTHON" portable_launcher.py
