from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import zipfile

ROOT = Path(__file__).parent
DOCS = ROOT / 'documents'
REPO = 'seotro95/seotro'
TAG = '100-chu-de-moi-20261116'

manifest = json.loads((DOCS / 'DOWNLOAD_MANIFEST.json').read_text(encoding='utf-8'))
for asset in manifest['files']:
    path = DOCS / asset['name']
    assert path.name == asset['name']
    assert path.stat().st_size == asset['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == asset['sha256']
    if path.suffix == '.txt':
        text = path.read_text(encoding='utf-8')
        assert '\ufffd' not in text
text = (DOCS / '100_CHU_DE_MOI.txt').read_text(encoding='utf-8')
assert len(re.findall(r'^\d{3}\.', text, re.M)) == 100
with zipfile.ZipFile(DOCS / '100_CHU_DE_VA_QUY_TRINH_20261116.zip') as archive:
    assert archive.testzip() is None

exists = subprocess.run(['gh', 'release', 'view', TAG, '--repo', REPO], capture_output=True)
assert exists.returncode != 0, 'Release already exists: inspect it before making changes'
subprocess.run(['gh', 'release', 'create', TAG, '--repo', REPO,
                '--target', os.environ['GITHUB_SHA'],
                '--title', '100 chủ đề mới và quy trình làm video — TXT tải trực tiếp',
                '--notes-file', str(ROOT / 'RELEASE_NOTES.md'), '--latest=false'], check=True)
for name in [asset['name'] for asset in manifest['files']] + ['DOWNLOAD_MANIFEST.json']:
    subprocess.run(['gh', 'release', 'upload', TAG, str(DOCS / name), '--repo', REPO], check=True)
    print('PUBLISHED', name, flush=True)
print('DOWNLOADS_READY', flush=True)
