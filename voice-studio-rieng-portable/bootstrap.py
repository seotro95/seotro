"""Install and launch the standalone voice studio. Python 3.12, no admin needed."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv
import zipfile

ROOT = Path(__file__).resolve().parent
APP = ROOT / 'app'
VENV = ROOT / '.venv'
PYTHON = VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
FFMPEG_URL = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
FFMPEG_ASSET = 'ffmpeg-n8.1-latest-win64-gpl-8.1.zip'


def run(command, *, cwd=ROOT):
    subprocess.run([str(item) for item in command], cwd=cwd, env=runtime_environment(), check=True)


def runtime_environment():
    result = dict(os.environ)
    result.pop('PYTHONHOME', None)
    result.pop('PYTHONPATH', None)
    result.update(PYTHONUTF8='1', PYTHONNOUSERSITE='1',
                  VOICE_STUDIO_DATA_DIR=str(APP / '.data'),
                  HF_HOME=str(APP / '.data/models/cache'), HF_HUB_DISABLE_XET='1',
                  PIP_CACHE_DIR=str(ROOT / '.cache/pip'))
    result['PATH'] = str(ROOT / 'tools/ffmpeg/bin') + os.pathsep + result.get('PATH', '')
    return result


def verify_python():
    if sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
        raise RuntimeError('Can Python 3.12 ban 64-bit. Cai tu https://www.python.org/downloads/windows/.')
    if os.name == 'nt' and platform.machine().lower() not in {'amd64', 'x86_64'}:
        raise RuntimeError('Goi nay danh cho Windows x64. Windows ARM chua duoc kiem thu.')


def checksum_for_asset(manifest, asset=FFMPEG_ASSET):
    for line in manifest.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip('*') == asset:
            if re.fullmatch(r'[a-fA-F0-9]{64}', fields[0]):
                return fields[0].lower()
    raise RuntimeError('Khong tim thay SHA256 hop le cua FFmpeg. Khong su dung tep tai ve.')


def extract_ffmpeg(archive, target):
    """Keep upstream licenses and docs; reject paths escaping the installation."""
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename:
                raise RuntimeError('Duong dan ZIP FFmpeg khong an toan.')
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError('Khong chap nhan symlink trong ZIP FFmpeg.')
            parts = path.parts[1:]
            if not parts or entry.is_dir() or parts[-1].lower() == 'ffplay.exe':
                continue
            destination = target.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, destination.open('wb') as output:
                shutil.copyfileobj(source, output)
    if not all((target / 'bin' / name).is_file() for name in ('ffmpeg.exe', 'ffprobe.exe')):
        raise RuntimeError('Goi FFmpeg thieu ffmpeg.exe hoac ffprobe.exe.')


def ensure_ffmpeg():
    env = runtime_environment()
    if all(shutil.which(name, path=env['PATH']) for name in ('ffmpeg', 'ffprobe')):
        return
    if os.name != 'nt':
        raise RuntimeError('Hay cai FFmpeg va ffprobe bang trinh quan ly goi cua he dieu hanh truoc.')
    tools = ROOT / 'tools'
    tools.mkdir(exist_ok=True)
    destination = tools / 'ffmpeg'
    if destination.exists():
        raise RuntimeError('tools/ffmpeg da ton tai nhung thieu tep. Kiem tra thu muc nay truoc khi cai lai.')
    print('Dang tai FFmpeg tu BtbN va kiem tra SHA256...', flush=True)
    with urllib.request.urlopen(FFMPEG_URL + 'checksums.sha256', timeout=60) as response:
        manifest = response.read(1024 * 1024).decode('utf-8')
    expected = checksum_for_asset(manifest)
    with tempfile.TemporaryDirectory(prefix='ffmpeg-', dir=tools) as temporary:
        temporary = Path(temporary)
        archive = temporary / FFMPEG_ASSET
        with urllib.request.urlopen(FFMPEG_URL + FFMPEG_ASSET, timeout=60) as source, archive.open('wb') as output:
            shutil.copyfileobj(source, output)
        with archive.open('rb') as source:
            actual = hashlib.file_digest(source, 'sha256').hexdigest()
        if actual != expected:
            raise RuntimeError('SHA256 FFmpeg khong khop. Dung cai dat; khong su dung tep nay.')
        stage = temporary / 'verified'
        stage.mkdir()
        extract_ffmpeg(archive, stage)
        (stage / 'UPSTREAM-SHA256.txt').write_text(expected + '  ' + FFMPEG_ASSET + '\n' + FFMPEG_URL, encoding='utf-8')
        stage.rename(destination)


def require_runtime():
    if not PYTHON.is_file():
        raise RuntimeError('Chua cai tool. Hay chay CAI_DAT.bat truoc.')


def install():
    verify_python()
    if not PYTHON.is_file():
        venv.EnvBuilder(with_pip=True).create(VENV)
    run([PYTHON, '-m', 'pip', 'install', '-r', ROOT / 'requirements-runtime.txt'])
    # Keep international dependencies working when refreshing an existing install.
    if (VENV / '.international-installed').is_file():
        run([PYTHON, '-m', 'pip', 'install', '-r', ROOT / 'requirements-qwen.txt'])
    ensure_ffmpeg()
    run([PYTHON, '-m', 'pip', 'check'])
    run([PYTHON, '-c', 'import fastapi, uvicorn, soundfile, onnxruntime, vieneu; print("Thu vien voice: OK")'])
    run(['ffmpeg', '-version'])
    run(['ffprobe', '-version'])
    print('Cai dat xong. Chay TAI_GIONG_VIET.bat de tai giong Nano, sau do MO_TOOL.bat.', flush=True)


def models(engine):
    require_runtime()
    ensure_ffmpeg()
    if engine in {'qwen', 'qwen_clone', 'international'}:
        # Matching releases with official Python 3.12 Windows x64 CPU wheels.
        run([PYTHON, '-m', 'pip', 'install', 'torch==2.9.1', 'torchaudio==2.9.1',
             '--index-url', 'https://download.pytorch.org/whl/cpu'])
        run([PYTHON, '-m', 'pip', 'install', '-r', ROOT / 'requirements-qwen.txt'])
        run([PYTHON, '-m', 'pip', 'check'])
        (VENV / '.international-installed').write_text('Installed Qwen CPU dependencies\n', encoding='utf-8')
    targets = ('qwen', 'qwen_clone') if engine == 'international' else (engine,)
    for target in targets:
        run([PYTHON, APP / 'prepare_models.py', target], cwd=APP)
    print('Da chuan bi mo hinh. Mo tool de tao va nghe thu voice.', flush=True)


def check():
    require_runtime()
    ensure_ffmpeg()
    run([PYTHON, '-m', 'pip', 'check'])
    run([PYTHON, '-c', 'import sys; sys.path.insert(0, "app"); import app; '
         'print("Voice API:", app.app.version); '
         'print("Gioi han ky tu:", app.MAX_CHARACTERS); '
         'print("Mo hinh:", app._config_values()["models"]); '
         'print("Nano:", app._config_values()["nano_ready"])'])


def main():
    parser = argparse.ArgumentParser(description='Voice Studio Rieng - cai dat, tai giong, mo tool')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--install', action='store_true')
    action.add_argument('--check', action='store_true')
    action.add_argument('--start', action='store_true')
    action.add_argument('--models', choices=['vieneu_nano', 'vieneu', 'qwen', 'qwen_clone', 'international'])
    args = parser.parse_args()
    if args.install:
        install()
    elif args.models:
        models(args.models)
    elif args.check:
        check()
    else:
        require_runtime()
        ensure_ffmpeg()
        run([PYTHON, APP / 'launcher.py'], cwd=APP)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('LOI: ' + str(exc), file=sys.stderr, flush=True)
        sys.exit(1)
