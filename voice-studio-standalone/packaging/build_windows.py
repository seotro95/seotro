"""Build and verify a native Windows portable distribution from a clean directory."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
VERSION = '1.1.1'
ARCHIVE_NAME = f'Voice-Studio-Rieng-{VERSION}-Portable-Windows-x64.zip'
FFMPEG_BASE = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
FFMPEG_ASSET = 'ffmpeg-n8.1-latest-win64-gpl-8.1.zip'


def run(command, *, cwd=None, env=None, timeout=1800):
    subprocess.run([str(x) for x in command], cwd=cwd, env=env, check=True, timeout=timeout)


def bootstrap_module():
    spec = importlib.util.spec_from_file_location('portable_bootstrap', SOURCE / 'bootstrap.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def download_ffmpeg(target, downloads):
    """Verify the upstream SHA256 manifest before extracting any executable."""
    helper = bootstrap_module()
    downloads.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(FFMPEG_BASE + 'checksums.sha256', timeout=60) as response:
        expected = helper.checksum_for_asset(response.read(1024 * 1024).decode('utf-8'))
    archive = downloads / FFMPEG_ASSET
    if not archive.is_file() or digest(archive) != expected:
        temporary = archive.with_suffix('.partial')
        with urllib.request.urlopen(FFMPEG_BASE + FFMPEG_ASSET, timeout=60) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        if digest(temporary) != expected:
            temporary.unlink(missing_ok=True)
            raise RuntimeError('FFmpeg SHA256 mismatch; no downloaded executable was used.')
        temporary.replace(archive)
    target.mkdir(parents=True)
    helper.extract_ffmpeg(archive, target)
    (target / 'UPSTREAM-SHA256.txt').write_text(expected + '  ' + FFMPEG_ASSET + '\n' + FFMPEG_BASE, encoding='utf-8')


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def materialize_cache(hub):
    """Keep ordinary snapshot files instead of Windows-incompatible symlinks."""
    for repo in hub.glob('models--*'):
        for entry in (repo / 'snapshots').rglob('*'):
            if entry.is_symlink():
                if not entry.is_file():
                    raise RuntimeError('Unsupported model-cache directory symlink')
                temporary = entry.with_name(entry.name + '.portable-copy')
                shutil.copyfile(entry.resolve(strict=True), temporary)
                entry.unlink()
                temporary.replace(entry)
        shutil.rmtree(repo / 'blobs', ignore_errors=True)
    shutil.rmtree(hub / '.locks', ignore_errors=True)


def copy_runtime(destination):
    original = Path(sys.base_prefix)
    if Path(sys.prefix).resolve() != original.resolve() or (original / 'pyvenv.cfg').exists():
        raise RuntimeError('Build using base Windows Python, not a venv.')
    shutil.copytree(original, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pdb', 'pip-cache'))
    roots = [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Microsoft Visual Studio']
    candidates = [file for root in roots if root.exists()
                  for file in root.glob('*/*/VC/Redist/MSVC/*/x64/Microsoft.VC143.CRT/msvcp140.dll')
                  if 'onecore' not in str(file).lower()]
    if not candidates:
        raise RuntimeError('MSVC app-local redistributable was not found; stop rather than ship an incomplete runtime.')
    for file in sorted(candidates)[-1].parent.glob('*.dll'):
        shutil.copy2(file, destination / file.name)
    if (destination / 'pyvenv.cfg').exists():
        raise RuntimeError('Portable runtime accidentally contains venv metadata')


def write_launchers(root):
    shutil.copy2(SOURCE / 'packaging' / 'portable_launcher.py', root / 'portable_launcher.py')
    for name, args in [('MO_TOOL.bat', ''), ('KIEM_TRA.bat', '--check')]:
        content = ('@echo off\nsetlocal\ncd /d "%~dp0"\n'
                   '"%~dp0runtime\\python.exe" "%~dp0portable_launcher.py" ' + args + '\n'
                   'set "VOICE_EXIT=%ERRORLEVEL%"\n'
                   'if not "%VOICE_EXIT%"=="0" echo Loi. Xem thong bao ben tren.\n'
                   'if not "%VOICE_EXIT%"=="0" pause\n'
                   'exit /b %VOICE_EXIT%\n')
        if args:
            content = content.replace('exit /b %VOICE_EXIT%', 'pause\nexit /b %VOICE_EXIT%')
        (root / name).write_bytes(content.replace('\n', '\r\n').encode('ascii'))
    notices = '''VOICE STUDIO RIENG PORTABLE 1.1.1 - WINDOWS 10/11 X64

Giai nen TOAN BO ZIP vao thu muc duoc phep ghi, sau do mo MO_TOOL.bat.
Khong can cai Python, FFmpeg, thu vien, API key hoac tai mo hinh tieng Viet.
Giong Viet Nano, nhan ban Nano va Turbo tieu chuan da duoc kiem tra offline.

De nhan ban nhanh: them/chon mau giong cua ban, bam Uu tien toc do.
Giu cua so tool mo khi dung. Ctrl+C de tat. KIEM_TRA.bat xem trang thai.

Du lieu, mau giong va ban thu duoc luu trong app/.data.
Sao luu thu muc nay truoc khi cap nhat/xoa tool.
Goi moi khong chua giong ca nhan, lich su hay khoa API cua nguoi tao.
Chi nhan ban mau cua ban hoac duoc chu giong cho phep.

Goi nay chuan bi day du quy trinh tao va nhan ban TIENG VIET tren CPU.
Qwen quoc te khong nam trong goi. Toc do/chuan giong tuy CPU, RAM va mau.
Nano 4 buoc co the giam do tu nhien/do giong giong; nghe thu truoc khi dung.
Khong can Internet de tao voice voi cac mo hinh da dong goi.

THIRD-PARTY NOTICES
Python license: runtime/LICENSE.txt
Python package licenses: runtime/Lib/site-packages/*.dist-info
FFmpeg GPL build: tools/ffmpeg (upstream licenses/docs retained).
Upstream source: https://github.com/BtbN/FFmpeg-Builds
MSVC redistributable: Microsoft Visual Studio app-local CRT.
Model cards and licenses: MODEL-LICENSES/ and app/.data/models/cache/hub.
'''
    (root / 'DOC_TRUOC.txt').write_text(notices, encoding='utf-8-sig')


def retain_model_notices(data, destination):
    from huggingface_hub import hf_hub_download
    from importlib.metadata import distribution
    destination.mkdir()
    repos = ('pnnbao-ump/VieNeu-TTS-v3-Nano', 'pnnbao-ump/VieNeu-TTS-v3-Turbo',
             'OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX')
    for repo in repos:
        readme = Path(hf_hub_download(repo, 'README.md', cache_dir=str(data / 'models/cache/hub')))
        shutil.copy2(readme, destination / (repo.replace('/', '--') + '-README.md'))
    package = distribution('vieneu')
    license_files = [f for f in package.files if str(f).endswith('dist-info/licenses/LICENSE')]
    if not license_files:
        raise RuntimeError('Missing installed VieNeu package license')
    shutil.copy2(package.locate_file(license_files[0]), destination / 'VIENEU-APACHE-2.0-LICENSE.txt')
    (destination / 'MODEL-NOTICES.txt').write_text(
        'Model licensing and attribution are documented in the included upstream model cards.\n'
        'VieNeu v3 Nano/Turbo: Apache-2.0 (see cards).\n'
        'MOSS Audio Tokenizer Nano ONNX: see its included upstream README/model license.\n'
        'No personal voice samples are distributed.\n', encoding='utf-8')


def clean_qa(data):
    """This data root was just created by the builder; no user data is read."""
    for path in data.iterdir():
        if path.name == 'models':
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for folder in ('voices', 'audio', 'jobs', 'parts'):
        (data / folder).mkdir()


def verify(root):
    env = dict(os.environ, PYTHONHOME=str(root / 'runtime'), PYTHONNOUSERSITE='1', PYTHONUTF8='1',
               VOICE_STUDIO_DATA_DIR=str(root / 'app/.data'), HF_HOME=str(root / 'app/.data/models/cache'),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', VOICE_STUDIO_PORTABLE='1',
               PATH=str(root / 'tools/ffmpeg/bin') + os.pathsep + os.environ['PATH'])
    env.pop('PYTHONPATH', None)
    run([root / 'runtime/python.exe', SOURCE / 'packaging/smoke_portable.py', root],
        cwd=root, env=env, timeout=1200)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if os.name != 'nt' or sys.maxsize <= 2**32:
        raise RuntimeError('Build and validate on native 64-bit Windows.')
    root = args.output.resolve()
    if root.exists():
        raise ValueError('Use a new output directory to protect existing builds/data.')
    root.mkdir(parents=True)
    app = root / 'app'
    app.mkdir()
    for file in (SOURCE / 'app').iterdir():
        if file.is_file() and file.suffix in {'.py', '.ps1'}:
            shutil.copy2(file, app / file.name)
    shutil.copytree(SOURCE / 'app/static', app / 'static')
    data = app / '.data'
    data.mkdir()
    download_ffmpeg(root / 'tools/ffmpeg', root.parent / 'downloads')
    env = dict(os.environ, VOICE_STUDIO_DATA_DIR=str(data), HF_HOME=str(data / 'models/cache'),
               HF_HUB_DISABLE_XET='1', PATH=str(root / 'tools/ffmpeg/bin') + os.pathsep + os.environ['PATH'])
    env.pop('HF_HUB_OFFLINE', None)
    env.pop('TRANSFORMERS_OFFLINE', None)
    for engine in ('vieneu_nano_clone', 'vieneu'):
        run([sys.executable, app / 'prepare_models.py', engine], cwd=app, env=env)
    retain_model_notices(data, root / 'MODEL-LICENSES')
    materialize_cache(data / 'models/cache/hub')
    copy_runtime(root / 'runtime')
    write_launchers(root)
    freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (root / 'BUILD-DEPENDENCIES.txt').write_text(freeze, encoding='utf-8')
    info = {'version': VERSION, 'source_commit': os.environ.get('GITHUB_SHA'), 'python': sys.version,
            'target': 'Windows 10/11 x64', 'bundled_models': ['vieneu_nano', 'vieneu_nano_clone', 'vieneu'],
            'native_windows_offline_validation': False, 'qwen_bundled': False}
    (root / 'BUILD.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    # Move the assembled directory before testing to exercise interpreter relocation.
    relocated = root.with_name(root.name + ' test with spaces')
    root.rename(relocated)
    try:
        verify(relocated)
        clean_qa(relocated / 'app/.data')
    finally:
        relocated.rename(root)
    info['native_windows_offline_validation'] = True
    (root / 'BUILD.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    for path in root.rglob('*'):
        if path.is_symlink():
            raise RuntimeError('A symlink remains in portable output: ' + str(path.relative_to(root)))
        if path.is_file() and path.name in {'token', 'stored_tokens', '.env', 'pyvenv.cfg'}:
            raise RuntimeError('Forbidden developer configuration in portable output')
    archive = Path(shutil.make_archive(str(root.parent / ARCHIVE_NAME[:-4]), 'zip', root.parent, root.name))
    if archive.stat().st_size >= 2 * 1024**3:
        raise RuntimeError('Portable ZIP exceeds the 2 GiB release asset limit; do not publish.')
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError('Final ZIP CRC validation failed')
    Path(str(archive) + '.sha256').write_text(digest(archive) + '  ' + archive.name + '\n', encoding='ascii')
    print('BUILT AND NATIVE-WINDOWS VERIFIED:', archive, archive.stat().st_size, flush=True)


if __name__ == '__main__':
    main()
