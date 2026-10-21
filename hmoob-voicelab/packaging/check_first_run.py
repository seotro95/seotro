"""Verify a final portable package needs only its model download on first run."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
app = root / 'hmoob-voicelab'
result = subprocess.run([str(root / 'runtime' / 'python.exe'), str(app / 'bootstrap.py'), '--check'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace')
if result.returncode != 1:
    raise RuntimeError('A weights-free first-run package must report only missing models: ' + result.stdout + result.stderr)
status = json.loads(result.stdout.strip().splitlines()[-1])
if not status['dependencies']['ready'] or status['models_verified'] or status['ready']:
    raise RuntimeError('The portable first-run state is not usable: ' + json.dumps(status))
if (app / '.data' / 'models').exists():
    raise RuntimeError('Model files must not be redistributed in the default package')
print('Verified final first-run package: native dependencies ready; models download automatically.', flush=True)
