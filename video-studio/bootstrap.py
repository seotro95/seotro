"""Install the release's pinned engines automatically inside the tool's venv."""
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import os
import subprocess
import sys


def ensure_runtime():
    requirements = Path(__file__).resolve().parent / 'requirements.txt'
    missing = []
    for line in requirements.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, expected = line.split('==', 1)
        try:
            if version(name) != expected:
                missing.append(name)
        except PackageNotFoundError:
            missing.append(name)
    if not missing:
        return False
    if sys.prefix == sys.base_prefix:
        raise ValueError('Hãy chạy khoi_dong.bat để cài vào môi trường riêng của tool.')
    print('Đang tự cài/cập nhật engine:', ', '.join(missing), flush=True)
    data = Path(os.environ.get('VIDEO_STUDIO_DATA', str(requirements.parent / 'data')))
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                    '--cache-dir', str(data / 'pip-cache'), '-r', str(requirements)], check=True)
    return True
