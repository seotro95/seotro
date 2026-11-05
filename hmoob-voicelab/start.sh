#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
unset PYTHONHOME PYTHONPATH
export PYTHONNOUSERSITE=1
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python bootstrap.py "$@"
fi
for hmoob_python in python3.12 python3.11 python3.10 python3; do
  if command -v "$hmoob_python" >/dev/null 2>&1; then
    if "$hmoob_python" -c 'import sys,struct; raise SystemExit(0 if sys.version_info.major == 3 and sys.version_info.minor in (10,11,12) and struct.calcsize("P") == 8 else 1)' >/dev/null 2>&1; then
      exec "$hmoob_python" bootstrap.py "$@"
    fi
  fi
done
echo 'Cần Python 3.10–3.12 64-bit. Cài Python 3.12 rồi mở lại start.sh.' >&2
exit 1
