#!/usr/bin/env bash
set -euo pipefail
MODE="${1:---install}"
case "$MODE" in --install|--update|--online-only|--fast-only) ;; *) echo "Tham so cai dat khong hop le." >&2; exit 1;; esac
SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_ROOT="${MELO_VIET_ROOT:-$HOME/.local/share/melo-viet-local}"
if [[ -e "$LOCAL_ROOT" && ! -f "$LOCAL_ROOT/.melo-viet-local-owner" ]]; then
  echo 'Thu muc dich da ton tai nhung khong thuoc bo cai. Dung thu muc trong bang MELO_VIET_ROOT.' >&2
  exit 1
fi
mkdir -p "$LOCAL_ROOT"
printf '%s\n' 'melo-viet-local-v1' > "$LOCAL_ROOT/.melo-viet-local-owner"
if [[ ! -x /usr/bin/python3.10 ]]; then
  echo 'Bo cai nay dung Ubuntu 22.04 / Python 3.10. Kiem tra phien ban ben trong Ubuntu bang cat /etc/os-release.' >&2
  exit 1
fi
if [[ "$MODE" == '--install' ]]; then
  sudo apt-get update
  sudo apt-get install -y python3.10-venv python3.10-dev build-essential git libsndfile1 mecab libmecab-dev mecab-ipadic-utf8 ffmpeg
elif [[ "$MODE" == '--online-only' || "$MODE" == '--fast-only' ]]; then
  sudo apt-get update
  sudo apt-get install -y python3.10-venv ffmpeg
elif [[ ! -f "$LOCAL_ROOT/app/app.py" ]]; then
  echo 'Chua co ban cu. Chay CAI_DAT.bat hoac CAI_TRUC_TUYEN.bat truoc.' >&2
  exit 1
elif ! command -v ffmpeg >/dev/null; then
  echo 'Thieu ffmpeg. Chay CAI_DAT.bat de bo sung.' >&2
  exit 1
fi
mkdir -p "$LOCAL_ROOT/envs" "$LOCAL_ROOT/src" "$LOCAL_ROOT/models" "$LOCAL_ROOT/outputs" "$LOCAL_ROOT/logs"
if [[ "$MODE" == '--install' ]]; then
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
fi
# Piper is isolated from Melo/VieNeu and uses CPU FP32, no CUDA or Torch.
if [[ "$MODE" != '--online-only' ]]; then
  if [[ ! -x "$LOCAL_ROOT/envs/piper/bin/python" ]]; then
    /usr/bin/python3.10 -m venv "$LOCAL_ROOT/envs/piper"
  fi
  "$LOCAL_ROOT/envs/piper/bin/python" -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
  "$LOCAL_ROOT/envs/piper/bin/python" -m pip install -r "$SOURCE_ROOT/fast-lock.txt"
  "$LOCAL_ROOT/envs/piper/bin/python" -m pip check
fi
# Tiny third environment adds many online languages without touching the two SDKs.
if [[ ! -x "$LOCAL_ROOT/envs/online/bin/python" ]]; then
  /usr/bin/python3.10 -m venv "$LOCAL_ROOT/envs/online"
fi
"$LOCAL_ROOT/envs/online/bin/python" -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
"$LOCAL_ROOT/envs/online/bin/python" -m pip install -r "$SOURCE_ROOT/online-lock.txt"
"$LOCAL_ROOT/envs/online/bin/python" -m pip check
if [[ -d "$LOCAL_ROOT/app" ]]; then
  BACKUP_ROOT="$LOCAL_ROOT/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$"
  mkdir -p "$BACKUP_ROOT"
  cp -a "$LOCAL_ROOT/app" "$BACKUP_ROOT/app"
fi
mkdir -p "$LOCAL_ROOT/app"
for file in app.py worker.py documents.py online_backend.py fast_backend.py fast_catalog.json samples.json index.html app.js style.css; do
  install -m 0644 "$SOURCE_ROOT/$file" "$LOCAL_ROOT/app/$file"
done
# Full edition carries model weights. Verify before copying; preserve all old readers/recordings.
if [[ -d "$SOURCE_ROOT/voice-pack/models/piper" ]]; then
  /usr/bin/python3.10 - "$SOURCE_ROOT" "$LOCAL_ROOT" <<'COPY_PACK'
import hashlib,json,sys,shutil
from pathlib import Path
source,root=map(Path,sys.argv[1:])
catalog=json.loads((source/'fast_catalog.json').read_text())['models']
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()
for record in catalog:
    src=source/'voice-pack/models/piper'/record['id'];dst=root/'models/piper'/record['id']
    for name,sha in record['files'].items():
        if not (src/name).is_file() or digest(src/name)!=sha:
            raise SystemExit('Sai/thieu mo hinh trong ban day du: '+record['id']+'/'+name)
    dst.mkdir(parents=True,exist_ok=True)
    for name,sha in record['files'].items():
        target=dst/name
        if target.is_file() and digest(target)==sha:continue
        temporary=target.with_name(target.name+'.install.partial')
        shutil.copyfile(src/name,temporary);temporary.replace(target)
    print('Da san sang mo hinh CPU:',record['id'],flush=True)
COPY_PACK
fi
printf '\nDa cai/cap nhat xong. Mo MO_TOOL.bat, chon bo doc va bam Tai / chuan bi danh sach giong.\n'
printf 'Mo hinh se duoc tai khi dung lan dau. Chua xac minh 30x.\n'
