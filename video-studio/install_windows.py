"""Choose a supported Windows Python before creating or repairing the private venv.

This bootstrap only imports the standard library, so Python 3.15 can run it
while application engines are installed with Python 3.11/3.12 x64.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SUPPORTED = {(3, 11), (3, 12)}
PROBE = """import json,sys,struct,sysconfig
print(json.dumps({'executable':sys.executable,'version':list(sys.version_info[:3]),
'bits':struct.calcsize('P')*8,'platform':sysconfig.get_platform(),
'implementation':sys.implementation.name,
'free_threaded':bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}))
"""


def compatible(info):
    return bool(info and tuple(info.get('version', [])[:2]) in SUPPORTED
                and info.get('bits') == 64 and info.get('platform') == 'win-amd64'
                and info.get('implementation') == 'cpython' and not info.get('free_threaded'))


def probe(command):
    try:
        result = subprocess.run([*command, '-c', PROBE], capture_output=True, text=True,
                                timeout=15, encoding='utf-8', errors='replace')
        if result.returncode == 0:
            info = json.loads(result.stdout.strip())
            if isinstance(info, dict) and info.get('executable'):
                return info
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


def registry_candidates():
    if os.name != 'nt':
        return []
    import winreg
    result = []
    for version in ('3.12', '3.11'):
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                for tag in (version, version + '-64'):
                    try:
                        with winreg.OpenKey(hive, 'Software\\Python\\PythonCore\\' + tag + '\\InstallPath',
                                            0, winreg.KEY_READ | view) as key:
                            try:
                                path = winreg.QueryValueEx(key, 'ExecutablePath')[0]
                            except OSError:
                                path = str(Path(winreg.QueryValueEx(key, '')[0]) / 'python.exe')
                            result.append([path])
                    except OSError:
                        continue
    return result


def launcher_candidates():
    # Enumerate installed paths; probing missing -3.x tags can trigger the new
    # Windows Python Manager's automatic runtime downloads.
    if not shutil.which('py'):
        return []
    try:
        result = subprocess.run(['py', '-0p'], capture_output=True, text=True,
                                timeout=15, encoding='utf-8', errors='replace')
        if result.returncode:
            return []
        paths = []
        for line in result.stdout.splitlines():
            match = re.search(r'((?:[A-Za-z]:[\\/]|\\\\)[^\r\n]*\.exe)', line, flags=re.IGNORECASE)
            if match:
                paths.append([match.group(1).strip()])
        return paths
    except (OSError, subprocess.TimeoutExpired):
        return []


def choose_python():
    commands = launcher_candidates()
    commands += [[sys.executable], *registry_candidates()]
    for name in ('python3.12', 'python3.11', 'python'):
        path = shutil.which(name)
        if path:
            commands.append([path])
    observed = []
    seen = set()
    for command in commands:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        info = probe(command)
        if info:
            observed.append('.'.join(map(str, info['version'])) + ' / ' + str(info['bits']) + '-bit')
        if compatible(info):
            return info
    versions = ', '.join(sorted(set(observed))) or 'không tìm thấy'
    raise ValueError('Chưa có Python 3.11 hoặc 3.12 bản Windows x64. Đã thấy: ' + versions +
                     '. Python 3.15/32-bit chưa dùng được cho các engine của tool. '
                     'Cài Python 3.11 hoặc 3.12 Windows installer (64-bit) từ python.org rồi chạy lại khoi_dong.bat.')


def preserve_incompatible_venv():
    path = ROOT / '.venv'
    if not path.exists():
        return None
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = ROOT / ('.venv-backup-' + stamp)
    try:
        path.rename(backup)
    except OSError:
        raise ValueError('Không chuyển được .venv cũ. Đóng các cửa sổ tool/Python dùng môi trường đó rồi chạy lại.') from None
    print('Đã giữ môi trường cũ tại:', backup.name, flush=True)
    return backup


def prepare_venv():
    python = ROOT / '.venv' / 'Scripts' / 'python.exe'
    existing = probe([str(python)]) if python.exists() else None
    if compatible(existing):
        print('Dùng môi trường hiện tại: Python ' + '.'.join(map(str, existing['version'])) + ' x64', flush=True)
        return python
    # Locate a usable interpreter before touching the previous environment.
    chosen = choose_python()
    print('Đã chọn Python ' + '.'.join(map(str, chosen['version'])) + ' x64: ' + chosen['executable'], flush=True)
    preserve_incompatible_venv()
    subprocess.run([chosen['executable'], '-m', 'venv', str(ROOT / '.venv')], check=True)
    actual = probe([str(python)])
    if not compatible(actual):
        raise ValueError('Môi trường mới không đúng Python 3.11/3.12 Windows x64; chưa cài engine.')
    return python


def check_runtime(python):
    script = 'import ctranslate2,piper,faster_whisper,av,onnxruntime;print("Engine imports: OK")'
    result = subprocess.run([str(python), '-c', script], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=90)
    if result.returncode:
        message = result.stderr[-1800:]
        if any(s in message.lower() for s in ('dll load failed', 'vcruntime', 'msvcp', 'winerror 126')):
            raise ValueError('Python đã phù hợp nhưng Windows không nạp được DLL của engine. '
                             'Cài Microsoft Visual C++ Redistributable x64 từ '
                             'https://aka.ms/vs/17/release/vc_redist.x64.exe rồi chạy lại khoi_dong.bat.')
        raise ValueError('Không nạp được engine sau khi cài:\n' + message)
    print(result.stdout.strip(), flush=True)


def install(ensure=False):
    port = int(os.environ.get('VIDEO_STUDIO_PORT', '8766'))
    with socket.socket() as connection:
        connection.settimeout(1)
        if connection.connect_ex(('127.0.0.1', port)) == 0:
            raise ValueError('Đóng cửa sổ tool đang chạy trước khi cài/cập nhật thư viện.')
    python = prepare_venv()
    requirements = ROOT / 'requirements.txt'
    data = Path(os.environ.get('VIDEO_STUDIO_DATA', str(ROOT / 'data')))
    if ensure:
        # This import runs in the supported venv, not in the bootstrap interpreter.
        subprocess.run([str(python), '-c', 'from bootstrap import ensure_runtime; ensure_runtime()'], cwd=ROOT, check=True)
    else:
        subprocess.run([str(python), '-m', 'pip', 'install', '--cache-dir', str(data / 'pip-cache'),
                        '-r', str(requirements)], check=True)
    check_runtime(python)
    print('Đã chuẩn bị engine. Đặt FFmpeg/FFprobe cạnh tool rồi chạy khoi_dong.bat.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ensure', action='store_true')
    parser.add_argument('--automatic', action='store_true')
    args = parser.parse_args()
    try:
        install(ensure=args.ensure)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('\nCÀI ĐẶT CHƯA HOÀN TẤT: ' + str(exc), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
