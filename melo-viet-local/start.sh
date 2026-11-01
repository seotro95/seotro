#!/usr/bin/env bash
set -euo pipefail
LOCAL_ROOT="${MELO_VIET_ROOT:-$HOME/.local/share/melo-viet-local}"
if [[ ! -f "$LOCAL_ROOT/app/app.py" || ! -x "$LOCAL_ROOT/envs/viet/bin/python" || ! -x "$LOCAL_ROOT/envs/melo/bin/python" ]]; then
  echo 'Chua cai xong. Chay CAI_DAT.bat truoc.' >&2
  exit 1
fi
if [[ "${1:-}" == 'offline' ]]; then
  exec /usr/bin/python3.10 "$LOCAL_ROOT/app/app.py" --root "$LOCAL_ROOT" --offline
fi
exec /usr/bin/python3.10 "$LOCAL_ROOT/app/app.py" --root "$LOCAL_ROOT"
