"""Explicit first-run preparation in a separate portable CPU Python runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from voxcpm_backend import data_directory, isolated_environment, prepared_model

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent


def prepare_runtime(data, runtime=None):
    if os.name != 'nt' or sys.maxsize <= 2**32:
        raise ValueError('Bộ chuẩn bị Portable này cần Windows x64; không thay đổi Python chính.')
    source = Path(sys.executable).resolve().parent
    target = Path(runtime or ROOT/'runtime-international').resolve()
    if target == source or source in target.parents or target in source.parents:
        raise ValueError('Runtime quốc tế phải là thư mục riêng với Python chính.')
    if not (source/'Lib/os.py').is_file() or not (source/'python.exe').is_file():
        raise ValueError('Chạy bằng runtime/python.exe đi kèm bản Portable đầy đủ.')
    if not (target/'python.exe').is_file():
        shutil.copytree(source, target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('site-packages', '__pycache__', '*.pyc',
                                                     'Scripts', 'Tools', 'test', '.git', '.agents', '.codex', '.aws'))
    python = target/'python.exe'
    env = isolated_environment(data, offline=False)
    subprocess.run([str(python), '-s', '-c',
                    'import sys; from pathlib import Path; '
                    'assert sys.version_info[:2]==(3,12); '
                    'assert Path(sys.prefix).resolve()==Path(sys.executable).resolve().parent'],
                   env=env, check=True, timeout=30)
    subprocess.run([str(python), '-s', '-m', 'ensurepip', '--upgrade'], env=env, check=True, timeout=120)
    subprocess.run([str(python), '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check',
                    '--no-cache-dir', '--index-url', 'https://download.pytorch.org/whl/cpu',
                    'torch==2.8.0+cpu', 'torchaudio==2.8.0+cpu'], env=env, check=True, timeout=1800)
    manifest = ROOT/'requirements-international.txt'
    subprocess.run([str(python), '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check',
                    '--no-cache-dir', '--prefer-binary', '--index-url', 'https://pypi.org/simple',
                    '-r', str(manifest)], env=env, check=True, timeout=1800)
    subprocess.run([str(python), '-m', 'pip', 'check'], env=env, check=True, timeout=60)
    subprocess.run([str(python), '-s', str(BASE/'voxcpm_backend.py'), '--check', '--data-dir', str(data)],
                   env=env, check=True, timeout=120)
    recipe = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (target/'VOICE-STUDIO-INTERNATIONAL.json').write_text(
        json.dumps({'package': 'voxcpm', 'version': '2.0.3', 'requirements_sha256': recipe,
                    'torch': '2.8.0+cpu', 'separate_runtime': True}, indent=2)+'\n', encoding='utf-8')
    return python


def main():
    parser = argparse.ArgumentParser(description='Chuẩn bị bộ giọng quốc tế gồm tiếng Thái, chạy riêng với Nano/Turbo')
    parser.add_argument('--runtime-only', action='store_true', help='Chỉ cài thư viện, chưa tải model')
    parser.add_argument('--check', action='store_true', help='Kiểm tra ngoại tuyến, không cài hoặc tải thêm')
    parser.add_argument('--data-dir')
    parser.add_argument('--runtime-dir', type=Path)
    parser.add_argument('--model-source', type=Path, help='Thư mục voxcpm2-original đã tải sẵn và có manifest SHA256')
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    data = data_directory(args.data_dir)
    runtime = args.runtime_dir or ROOT/'runtime-international'
    python = runtime/'python.exe'
    if args.check:
        if not python.is_file():
            raise ValueError('Chưa có runtime-international. Chạy TAI_GIONG_DA_NGON_NGU.bat để chuẩn bị.')
    else:
        print('Đang chuẩn bị bộ giọng quốc tế trong runtime riêng. Python và giọng Nano/Turbo hiện có được giữ nguyên.', flush=True)
        python = prepare_runtime(data, runtime)
    model_source = args.model_source
    if not args.check and not args.runtime_only and model_source is None:
        try:
            prepared_model(data)
        except (OSError, ValueError, KeyError):
            from public_modelpack import ensure_model_source
            print('Đang tải và kiểm tra model đa ngôn ngữ từ GitHub, khoảng 5 GB. Có thể chạy lại nếu mất mạng.', flush=True)
            model_source = ensure_model_source(data)
    command = [str(python), '-s', str(BASE/'voxcpm_backend.py'), '--check' if args.check or args.runtime_only else '--prepare-model',
               '--data-dir', str(data), '--threads', str(max(1, min(8, args.threads)))]
    if model_source:
        command.extend(['--model-source', str(model_source.resolve())])
    env = isolated_environment(data, args.threads, offline=True)
    subprocess.run(command, env=env, check=True, timeout=1800)
    if not args.check and not args.runtime_only:
        from public_modelpack import cleanup_download_parts
        try:
            cleanup_download_parts(data)
        except OSError:
            print('Model đã sẵn sàng. Một số phần tải đang được sử dụng nên chưa dọn được.', flush=True)
        print('Đã kiểm tra tạo lời tiếng Thái và chuẩn bị bộ giọng quốc tế. Mở lại Voice Studio.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print('Không chuẩn bị xong bộ giọng quốc tế: '+str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
