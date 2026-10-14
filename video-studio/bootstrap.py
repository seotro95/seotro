"""Install the release's pinned engines automatically inside the tool's venv."""
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import os
import subprocess
import sys
import struct
import sysconfig


def ensure_runtime():
    if sys.platform == 'win32':
        from install_windows import compatible
        info = {'version':list(sys.version_info[:3]), 'bits':struct.calcsize('P') * 8,
                'platform':sysconfig.get_platform(), 'implementation':sys.implementation.name,
                'free_threaded':bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}
        if not compatible(info):
            raise ValueError('Engine Windows cần Python 3.11/3.12 x64. Chạy khoi_dong.bat hoặc cai_dat.bat để chọn đúng Python; chưa cài thư viện bằng Python này.')
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
