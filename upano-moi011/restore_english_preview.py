import hashlib
import json
import shutil
from pathlib import Path

R = Path(__file__).parent
rows = json.loads((R / 'voice/scripts/en-US.json').read_text())
source = next(Path('preflight/en-US').rglob('group-001.request.json')).parent
request = json.loads((source / 'group-001.request.json').read_text())
body = ' '.join(r['voice'] for r in rows[:3])
assert request['request_signature'] == hashlib.sha256((body + '\0en-US-AndrewNeural\0+0%').encode()).hexdigest()
out = R / 'voice/audio/en-US'
out.mkdir(parents=True, exist_ok=True)
for path in source.glob('group-001*'):
    shutil.copyfile(path, out / path.name)
print('VERIFIED_ENGLISH_OPENING_RESTORED', flush=True)
