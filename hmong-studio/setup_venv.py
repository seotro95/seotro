"""Create/reuse a supported venv, preserving incompatible environments intact."""
from datetime import datetime
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import uuid
import venv


def supported(version, bits):
    return (3, 10) <= tuple(version[:2]) < (3, 13) and bits == 64


def interpreter_info(executable):
    code = "import json,struct,sys;print(json.dumps({'version':list(sys.version_info[:3]),'bits':struct.calcsize('P')*8,'implementation':sys.implementation.name}))"
    try:
        result = subprocess.run([str(executable), '-I', '-c', code], check=True,
                                capture_output=True, text=True, timeout=20)
        info = json.loads(result.stdout)
        if info['implementation'] == 'cpython' and supported(info['version'], info['bits']):
            return info
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        pass
    return None


def ensure_venv(root):
    if sys.implementation.name != 'cpython' or not supported(sys.version_info, struct.calcsize('P')*8):
        raise RuntimeError('Can Python 3.10-3.12 64-bit de tao moi truong. Khuyen dung 3.12.')
    root = Path(root)
    environment = root / '.venv'
    executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    info = interpreter_info(executable) if executable.exists() else None
    if info:
        pip_check = subprocess.run([str(executable), '-m', 'pip', '--version'], capture_output=True, timeout=20)
        if pip_check.returncode != 0:
            subprocess.run([str(executable), '-m', 'ensurepip', '--upgrade'], check=True, timeout=120)
        print('Dung moi truong Python ' + '.'.join(map(str, info['version'])) + ' 64-bit.')
        return executable
    if environment.exists() or environment.is_symlink():
        backup = root / ('.venv-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
        environment.rename(backup)
        print('Da giu nguyen moi truong cu tai: ' + backup.name)
    print('Dang tao moi truong Python tu: ' + sys.executable)
    venv.EnvBuilder(with_pip=True).create(environment)
    if not interpreter_info(executable):
        raise RuntimeError('Moi truong moi khong khoi dong duoc. Giu thong bao loi de kiem tra.')
    print('Da tao moi truong tuong thich. Du lieu .data va mau giong duoc giu nguyen.')
    return executable


if __name__ == '__main__':
    try:
        ensure_venv(Path(__file__).resolve().parent)
    except Exception as exc:
        print('Khong tao duoc moi truong: ' + str(exc), file=sys.stderr)
        sys.exit(1)
