#!/usr/bin/env bash
set -euo pipefail
export PYTHONUTF8=1
cd -- "$(dirname -- "$0")"
VOICE_WITH_QWEN=0
VOICE_PREPARE_MODELS=1
for voice_arg in "$@"; do
  case "$voice_arg" in
    --qwen) VOICE_WITH_QWEN=1 ;;
    --no-models) VOICE_PREPARE_MODELS=0 ;;
    *) printf 'Tùy chọn không hợp lệ: %s\nDùng: bash install.sh [--qwen] [--no-models]\n' "$voice_arg" >&2; exit 2 ;;
  esac
done
command -v ffmpeg >/dev/null || { echo 'Cần cài FFmpeg trước.' >&2; exit 1; }
command -v ffprobe >/dev/null || { echo 'Cần cài ffprobe cùng FFmpeg trước.' >&2; exit 1; }
VOICE_ENV_DIR="${VOICE_STUDIO_VENV:-.venv}"
if [ ! -x "$VOICE_ENV_DIR/bin/python" ]; then
  command -v python3.12 >/dev/null || { echo 'Cần Python 3.12 để tạo môi trường. Không thay đổi dữ liệu hiện có.' >&2; exit 1; }
  python3.12 -m venv "$VOICE_ENV_DIR"
fi
"$VOICE_ENV_DIR/bin/python" -c 'import sys; assert (3,10) <= sys.version_info[:2] < (3,13), "Can Python 3.10-3.12. Sao luu .venv va tao lai bang Python 3.12; khong xoa .data."'
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.data/pip-cache}"
"$VOICE_ENV_DIR/bin/python" -m pip install -r requirements.txt
if [ "$VOICE_WITH_QWEN" = 1 ]; then
  if [ "$(uname -s)" = Linux ]; then
    "$VOICE_ENV_DIR/bin/python" -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
  else
    "$VOICE_ENV_DIR/bin/python" -m pip install torch==2.6.0 torchaudio==2.6.0
  fi
  "$VOICE_ENV_DIR/bin/python" -m pip install -r requirements-qwen.txt
fi
"$VOICE_ENV_DIR/bin/python" -m pip check
if [ "$VOICE_PREPARE_MODELS" = 1 ]; then
  "$VOICE_ENV_DIR/bin/python" prepare_models.py vieneu_nano
  "$VOICE_ENV_DIR/bin/python" prepare_models.py vieneu
  if [ "$VOICE_WITH_QWEN" = 1 ]; then
    "$VOICE_ENV_DIR/bin/python" prepare_models.py qwen
    "$VOICE_ENV_DIR/bin/python" prepare_models.py qwen_clone
  fi
fi
printf '%s\n' 'Đã cài xong. Chạy bash start.sh. Giọng quốc tế tùy chọn: bash install.sh --qwen.'
