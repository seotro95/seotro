#!/usr/bin/env python3
"""Build an unpacked desktop ZIP from verified Electron + the current app.

Build requirements: Node 24, npm ci, npm run build, Python 3. Windows users of
the resulting ZIP need none of those tools. No profiles or .env files are copied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--platform', choices=['win32', 'linux'], default='win32')
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--no-zip', action='store_true', help='Prepare an unpacked test bundle only.')
parser.add_argument('--runtime-zip', type=Path, help='Use a previously downloaded official Windows runtime; checksum is still required.')
args = parser.parse_args()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
manifest = json.loads((ROOT / 'package.json').read_text())
version = manifest['version']
label = 'Windows' if args.platform == 'win32' else 'Linux'
bundle = output / f'Muse-AI-Studio-{version}-{label}-x64'
if bundle.exists():
    raise SystemExit(f'Output directory already exists: {bundle}')
if not (ROOT / 'dist/index.html').is_file():
    raise SystemExit('Run npm run build first.')

if args.platform == 'win32':
    code = """
const {downloadArtifact} = require('@electron/get');
const electronPackage = require('electron/package.json');
downloadArtifact({version:electronPackage.version,artifactName:'electron',platform:'win32',arch:'x64',
 checksums:require('electron/checksums.json'),cacheRoot:process.argv[1]})
 .then(path=>console.log(path)).catch(error=>{console.error(error.message);process.exit(1)});
"""
    env = dict(os.environ)
    env.setdefault('ELECTRON_GET_USE_PROXY', '1')
    runtime = args.runtime_zip.resolve() if args.runtime_zip else Path(subprocess.check_output(['node', '-e', code, str(output / 'electron-cache')], cwd=ROOT, env=env, text=True).strip().splitlines()[-1])
    checksums = json.loads((ROOT / 'node_modules/electron/checksums.json').read_text())
    assert hashlib.sha256(runtime.read_bytes()).hexdigest() == checksums[runtime.name]
    bundle.mkdir()
    with ZipFile(runtime) as z:
        for name in z.namelist():
            target = (bundle / name).resolve()
            assert target.is_relative_to(bundle.resolve()), name
        z.extractall(bundle)
    executable = 'Muse AI Studio.exe'
    (bundle / 'electron.exe').rename(bundle / executable)
else:
    shutil.copytree(ROOT / 'node_modules/electron/dist', bundle)
    executable = 'Muse AI Studio'
    (bundle / 'electron').rename(bundle / executable)

resources = bundle / 'resources'
(resources / 'default_app.asar').unlink(missing_ok=True)
app = resources / 'app'
app.mkdir()
for name in ['desktop', 'dist']:
    shutil.copytree(ROOT / name, app / name)
for name in ['limits.mjs', 'server.mjs', 'muse-browser.mjs', 'muse-accounts.mjs', 'muse-balance.mjs', 'browser.mjs', '.env.example', 'README.md', 'VALIDATION.md', 'API-AUTOMATION.md', 'MCP-CODEX.md', 'CODEX-MCP.toml', 'CAP-NHAT-1.9.md', 'BAN-DAY-DU-1.10.md', 'BLACK-SCREEN-1.12.1.md', 'RECOVERY-1.12.2.md', 'LICENSE']:
    shutil.copyfile(ROOT / name, app / name)
modules = app / 'node_modules'
modules.mkdir()
shutil.copytree(ROOT / 'node_modules/playwright-core', modules / 'playwright-core')
(app / 'package.json').write_text(json.dumps({
    'name': 'muse-ai-studio', 'productName': 'Muse AI Studio', 'version': version,
    'private': True, 'license': manifest.get('license', 'UNLICENSED'), 'type': 'module', 'main': 'desktop/main.mjs',
    'dependencies': {'playwright-core': manifest['dependencies']['playwright-core']},
}, indent=2) + '\n')

licenses = app / 'THIRD_PARTY_LICENSES'
licenses.mkdir()
for name in ['react', 'react-dom', 'lucide-react']:
    source = ROOT / 'node_modules' / name
    for license_file in source.glob('LICENSE*'):
        shutil.copyfile(license_file, licenses / f'{name}-{license_file.name}')

(bundle / 'BAT_DAU.txt').write_text(f'''Muse AI Studio {version} - Ban day du {label} x64

1. Giai nen TOAN BO ZIP vao thu muc moi, vi du D:\\Muse-AI-Studio-{version}.
2. Mo "{executable}". Khong chay ung dung ngay trong cua so xem ZIP.
3. Dang nhap Muse trong tool, quay Ve Studio, bam Kiem tra phien.
4. Chon so o/luong 20, 30 hoac 40. Dung 1 tai khoan hoac nhieu tai khoan.
5. Quan ly toi da 40 tai khoan: nhap danh sach email/ten, dang nhap tung phien Muse.
6. Nhap prompt hoac TXT/SRT, chon anh/video va bam Tao theo so o da chon.

Khong can ban cu, Node.js, npm hoac Chrome cai rieng.
Can Internet va tai khoan Muse co quyen tao noi dung tuong ung.
Ban Windows moi luu ho so tai %LOCALAPPDATA%\\Muse AI Studio.
Neu da dung ban cu: dong ban cu; trong ban moi chon Tai khoan Muse -> Chuyen du lieu ban cu.
Chon thu muc co EXE cu. Tool sao chep tat ca ho so, thu vien va tu mo lai.
Bam Luu tat ca tai khoan de xem trang thai luu tung ho so.
Phien con hieu luc duoc khoi phuc khi mo lai; phien Muse da het han can dang nhap lai.
Neu Studio khong mo duoc: bam Tai lai Studio hoac Sao chep chan doan Studio.
Thu tuong thich hien thi: dong tool roi mo MO_STUDIO_KHONG_GPU.bat (Windows).
Neu van dung khi da tat GPU: dong tool roi mo MO_STUDIO_KHOI_PHUC.bat.
Che do khoi phuc giu tai khoan/kich ban va chua doc thu vien cu; khong xoa tep da luu.

Cau noi Muse khong chinh thuc. Co the bi anh huong khi Muse doi giao dien,
gioi han tai khoan, mo hinh hoac so tac vu dong thoi.
''', encoding='utf-8')
if args.platform == 'win32':
    (bundle / 'BAT_DAU.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0Muse AI Studio.exe"\r\n')
    (bundle / 'MO_STUDIO_KHONG_GPU.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0Muse AI Studio.exe" --disable-gpu\r\n')
    (bundle / 'MO_STUDIO_KHOI_PHUC.bat').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0Muse AI Studio.exe" --studio-recovery --disable-gpu\r\n')

for path in app.rglob('*'):
    assert not any(part in {'.data', '.env', 'test-results', 'playwright-report'} for part in path.relative_to(app).parts), path
build_manifest = {'version': version, 'platform': args.platform, 'arch': 'x64',
                  'electronVersion': json.loads((ROOT / 'node_modules/electron/package.json').read_text())['version'],
                  'appFiles': {str(path.relative_to(app)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted(app.rglob('*')) if path.is_file()}}
(bundle / 'BUILD-MANIFEST.json').write_text(json.dumps(build_manifest, indent=2) + '\n')
archive = output / f'{bundle.name}.zip'
if args.no_zip:
    print(json.dumps({'bundle': str(bundle), 'version': version}))
    raise SystemExit(0)
with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=9) as z:
    for path in sorted(bundle.rglob('*')):
        if path.is_file():
            z.write(path, str(Path(bundle.name) / path.relative_to(bundle)))
with ZipFile(archive) as z:
    assert z.testzip() is None
print(json.dumps({'archive': str(archive), 'bundle': str(bundle), 'version': version,
                  'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}))
