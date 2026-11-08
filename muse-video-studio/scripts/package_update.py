#!/usr/bin/env python3
"""Make an in-place Windows update from a verified portable build, without data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

parser = argparse.ArgumentParser()
parser.add_argument('--bundle', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
manifest = json.loads((args.bundle / 'BUILD-MANIFEST.json').read_text())
assert manifest['electronVersion'] == '45.2.2', 'Revisit update compatibility if runtime changes.'
assert manifest['version'] == '1.9.0'
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
folder = output / 'Muse-AI-Studio-Update-1.9.0'
folder.mkdir()
app = args.bundle / 'resources/app'
files = {}
for name, checksum in manifest['appFiles'].items():
    if name.startswith(('node_modules/', 'THIRD_PARTY_LICENSES/')):
        continue
    assert '.data' not in Path(name).parts and '.env' not in Path(name).parts
    source = app / name
    assert hashlib.sha256(source.read_bytes()).hexdigest() == checksum
    destination = folder / 'app' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    files[name] = checksum
(folder / 'UPDATE-MANIFEST.json').write_text(json.dumps({'version': manifest['version'], 'appFiles': files}, indent=2) + '\n')
shutil.copyfile(root / 'scripts/update-windows.ps1', folder / 'update-windows.ps1')
(folder / 'CAP_NHAT.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0update-windows.ps1"\r\npause\r\n')
shutil.copyfile(root / 'CAP-NHAT-1.9.md', folder / 'HUONG_DAN.md')
archive = output / (folder.name + '.zip')
with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=9) as zipped:
    for source in sorted(folder.rglob('*')):
        if source.is_file():
            zipped.write(source, Path(folder.name) / source.relative_to(folder))
with ZipFile(archive) as zipped:
    assert zipped.testzip() is None
print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'files': len(files), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}))
