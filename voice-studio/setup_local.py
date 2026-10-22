"""Install the local studio and prepare Vietnamese voices before reporting ready.

No user recordings/history are deleted. International models are an explicit,
optional download because they require substantially more disk space.
"""
import argparse
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys


BASE = Path(__file__).resolve().parent


def local_tools():
    for directory in (BASE / '.tools' / 'ffmpeg' / 'bin', BASE.parent / 'ffmpeg' / 'bin'):
        if directory.is_dir():
            os.environ['PATH'] = str(directory) + os.pathsep + os.environ.get('PATH', '')
            break


def run(command):
    subprocess.run([str(part) for part in command], cwd=BASE, check=True)


def main():
    parser = argparse.ArgumentParser(description='Cai dat va kiem tra Voice Studio cuc bo')
    parser.add_argument('--international', action='store_true', help='Them Qwen va nhan ban quoc te; can nhieu GB')
    parser.add_argument('--portable', action='store_true', help='Dung runtime Windows Portable co san, khong tao .venv')
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] <= (3, 13) or struct.calcsize('P') != 8:
        raise RuntimeError('Can Python 64-bit 3.10-3.13; khuyen dung Python 3.12 64-bit tu python.org.')
    local_tools()
    missing = [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        raise RuntimeError(
            'Chua co ' + ', '.join(missing) + '. Windows: cai FFmpeg (winget install --id Gyan.FFmpeg -e), '
            'dong/mo lai cua so roi chay MO_TOOL.bat. Ubuntu: sudo apt install ffmpeg. '
            'macOS: brew install ffmpeg. Co the dat ffmpeg va ffprobe trong .tools/ffmpeg/bin.'
        )
    if args.portable:
        executable = Path(sys.executable).resolve()
        expected = (BASE.parent / 'runtime' / 'python.exe').resolve()
        if executable != expected or not expected.is_file():
            raise RuntimeError('--portable chi dung voi runtime/python.exe cua ban Windows Portable nay.')
        print('1/3 Dung runtime Windows Portable hien tai...', flush=True)
    else:
        configured = os.environ.get('VOICE_STUDIO_VENV', '.venv')
        environment = (BASE / configured).resolve()
        executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not executable.is_file():
            print('1/3 Tao moi truong Python rieng...', flush=True)
            run([sys.executable, '-m', 'venv', environment])
        else:
            print('1/3 Dung lai moi truong Python; giu nguyen du lieu...', flush=True)
    print('2/3 Cai/kiem tra thu vien...', flush=True)
    # Reused environments may have been created by uv without pip.
    run([executable, '-m', 'ensurepip', '--upgrade'])
    run([executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    # Vietnamese ONNX engines do not require PyTorch. Resolve it only for Qwen.
    if args.international:
        torch_command = [executable, '-m', 'pip', 'install', 'torch==2.6.0', 'torchaudio==2.6.0']
        if sys.platform != 'darwin':
            torch_command += ['--index-url', 'https://download.pytorch.org/whl/cpu']
        run(torch_command)
    requirements = 'requirements-qwen.txt' if args.international else 'requirements.txt'
    run([executable, '-m', 'pip', 'install', '-r', requirements])
    run([executable, '-m', 'pip', 'check'])
    print('3/3 Tai va tao audio kiem tra model. Lan dau can Internet; khong tat cua so...', flush=True)
    if args.international:
        for engine in ('qwen', 'qwen_clone'):
            run([executable, BASE / 'prepare_models.py', engine])
    else:
        run([executable, BASE / 'prepare_models.py', 'vi'])
    print('DA SAN SANG. Chay MO_TOOL.bat (Windows) hoac ./start.sh (Linux/macOS).', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print('CAI DAT CHUA HOAN TAT: ' + str(error), file=sys.stderr, flush=True)
        print('Sua loi ben tren roi chay lai. Model da tai va du lieu ca nhan duoc giu nguyen.', file=sys.stderr)
        sys.exit(1)
