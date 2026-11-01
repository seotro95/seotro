#!/usr/bin/env bash
set -euo pipefail
SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_ROOT="${MELO_VIET_ROOT:-$HOME/.local/share/melo-viet-local}"
if [[ -e "$LOCAL_ROOT" && ! -f "$LOCAL_ROOT/.melo-viet-local-owner" ]]; then
  echo 'Thu muc dich da ton tai nhung khong thuoc bo cai. Dung thu muc trong bang MELO_VIET_ROOT.' >&2
  exit 1
fi
mkdir -p "$LOCAL_ROOT"
printf '%s\n' 'melo-viet-local-v1' > "$LOCAL_ROOT/.melo-viet-local-owner"
if [[ ! -x /usr/bin/python3.10 ]]; then
  echo 'Bo cai nay dung Ubuntu 22.04 / Python 3.10. Mo dung Ubuntu-22.04 trong WSL.' >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y python3.10-venv python3.10-dev build-essential git libsndfile1 mecab libmecab-dev mecab-ipadic-utf8 ffmpeg
mkdir -p "$LOCAL_ROOT/envs" "$LOCAL_ROOT/src" "$LOCAL_ROOT/models" "$LOCAL_ROOT/outputs" "$LOCAL_ROOT/logs"
for environment in melo viet; do
  if [[ ! -x "$LOCAL_ROOT/envs/$environment/bin/python" ]]; then
    /usr/bin/python3.10 -m venv "$LOCAL_ROOT/envs/$environment"
  fi
  "$LOCAL_ROOT/envs/$environment/bin/python" -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
done
MELO_PYTHON="$LOCAL_ROOT/envs/melo/bin/python"
VIET_PYTHON="$LOCAL_ROOT/envs/viet/bin/python"
"$MELO_PYTHON" -m pip install 'torch==2.2.2+cpu' 'torchaudio==2.2.2+cpu' --index-url https://download.pytorch.org/whl/cpu
"$MELO_PYTHON" -m pip install -r "$SOURCE_ROOT/melo-lock.txt"
MELO_REVISION='209145371cff8fc3bd60d7be902ea69cbdb7965a'
if [[ ! -d "$LOCAL_ROOT/src/MeloTTS/.git" ]]; then
  git clone --no-checkout https://github.com/myshell-ai/MeloTTS.git "$LOCAL_ROOT/src/MeloTTS"
fi
git -C "$LOCAL_ROOT/src/MeloTTS" fetch origin "$MELO_REVISION" --depth 1
git -C "$LOCAL_ROOT/src/MeloTTS" checkout --detach "$MELO_REVISION"
test "$(git -C "$LOCAL_ROOT/src/MeloTTS" rev-parse HEAD)" = "$MELO_REVISION"
"$MELO_PYTHON" -m pip install --no-deps --no-build-isolation -e "$LOCAL_ROOT/src/MeloTTS"
"$MELO_PYTHON" -m pip check
"$MELO_PYTHON" -m nltk.downloader -q averaged_perceptron_tagger averaged_perceptron_tagger_eng cmudict punkt punkt_tab
if ! "$MELO_PYTHON" -c 'import pathlib,unidic; raise SystemExit(not (pathlib.Path(unidic.DICDIR)/"sys.dic").is_file())'; then
  "$MELO_PYTHON" -m unidic download
fi
"$VIET_PYTHON" -m pip install -r "$SOURCE_ROOT/viet-lock.txt"
"$VIET_PYTHON" -m pip check
if [[ -d "$LOCAL_ROOT/app" ]]; then
  BACKUP_ROOT="$LOCAL_ROOT/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$"
  mkdir -p "$BACKUP_ROOT"
  cp -a "$LOCAL_ROOT/app" "$BACKUP_ROOT/app"
fi
mkdir -p "$LOCAL_ROOT/app"
for file in app.py worker.py index.html app.js style.css; do
  install -m 0644 "$SOURCE_ROOT/$file" "$LOCAL_ROOT/app/$file"
done
printf '\nDa cai xong thu vien. Mo MO_TOOL.bat, chon ngon ngu va bam Tai/chuan bi giong.\n'
printf 'Mo hinh se duoc tai khi dung lan dau. Chua xac minh 30x.\n'
