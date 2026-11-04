#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if ! command -v node >/dev/null || ! node -e "if(Number(process.versions.node.split('.')[0])<24)process.exit(1)"; then
  echo 'Cần Node.js 24 trở lên: https://nodejs.org/' >&2
  exit 1
fi
if [[ ! -f node_modules/react/package.json || ! -f node_modules/electron/package.json ]]; then npm ci; fi
if [[ ! -f dist/index.html ]]; then npm run build; fi
exec node desktop-launcher.mjs
