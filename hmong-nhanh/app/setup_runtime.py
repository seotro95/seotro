"""Prepare dependencies and verified model files on the first launch."""
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def installed(name, version=None):
    try:
        value = importlib.metadata.version(name)
        return version is None or value.split('+')[0] == version
    except importlib.metadata.PackageNotFoundError:
        return False


def pip(*args):
    subprocess.run([sys.executable, '-m', 'pip', 'install', *args], check=True, cwd=BASE)


def main():
    if not all(installed(name) for name in ('fastapi', 'uvicorn', 'pydantic')):
        print('Dang cai giao dien doc van ban...', flush=True)
        pip('-r', str(BASE / 'requirements.txt'))
    if not all(installed(name, '2.6.0') for name in ('torch', 'torchaudio')):
        print('Dang cai PyTorch CPU. Lan dau can Internet va vai GB dia trong.', flush=True)
        pip('torch==2.6.0', 'torchaudio==2.6.0', '--index-url', 'https://download.pytorch.org/whl/cpu')
    if not installed('f5-tts', '1.1.22') or not all(installed(name) for name in ('soundfile', 'scipy', 'numpy')):
        print('Dang cai bo tao giong Hmong...', flush=True)
        pip('-r', str(BASE / 'requirements-voice.txt'))
    from model_files import EngineError, model_directory, verify_models
    try:
        verify_models()
        print('Mo hinh da duoc xac minh, dung lai ban da tai.', flush=True)
    except EngineError:
        print('Dang tai/kiem tra mo hinh Hmong (~1.4 GB). Khong dong cua so nay.', flush=True)
        from setup_voice import install
        install(model_directory())
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print('Chua chuan bi xong: ' + str(exc), file=sys.stderr)
        print('Mo lai MO_HMONG_NHANH.bat de thu lai; du lieu giu nguyen.', file=sys.stderr)
        sys.exit(1)
