#!/usr/bin/env bash
set -euo pipefail
LOCAL_ROOT="${MELO_VIET_ROOT:-$HOME/.local/share/melo-viet-local}"
if [[ ! -f "$LOCAL_ROOT/app/app.py" || ! -x /usr/bin/python3.10 ]]; then
  echo 'Chua cai xong. Chay CAI_DAT.bat truoc.' >&2
  exit 1
fi
if [[ "${1:-}" == 'offline' ]]; then
  if [[ ! -x "$LOCAL_ROOT/envs/viet/bin/python" || ! -x "$LOCAL_ROOT/envs/melo/bin/python" ]]; then
    echo 'Chua cai bo doc ngoai tuyen. Chay CAI_DAT.bat hoac mo MO_TOOL.bat de dung truc tuyen.' >&2
    exit 1
  fi
  exec /usr/bin/python3.10 "$LOCAL_ROOT/app/app.py" --root "$LOCAL_ROOT" --offline
fi
exec /usr/bin/python3.10 "$LOCAL_ROOT/app/app.py" --root "$LOCAL_ROOT"
