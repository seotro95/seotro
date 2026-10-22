"""Prepare verified Hmong files, then open the shared studio with its own data."""
import argparse
from importlib import metadata
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description='Voice Studio Hmong')
    parser.add_argument('--check', action='store_true', help='Verify prerequisites offline; do not download.')
    parser.add_argument('--setup-only', action='store_true', help='Prepare model files and exit.')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    os.environ['VOICE_STUDIO_VARIANT'] = 'hmong'
    os.environ.setdefault('VOICE_STUDIO_DATA_DIR', str(BASE / '.data-hmong'))
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    os.environ.setdefault('PYTHONUTF8', '1')
    versions = {name: metadata.version(name) for name in ('f5-tts', 'torch', 'torchaudio')}
    if versions['f5-tts'] != '1.1.22' or versions['torch'].split('+')[0] != versions['torchaudio'].split('+')[0]:
        raise RuntimeError('Thư viện F5/PyTorch không khớp. Giải nén lại gói đầy đủ hoặc cài requirements-hmong.txt.')
    from hmong_assets import reference
    reference('hmong-female')
    reference('hmong-male')
    command = [sys.executable, str(BASE / 'prepare_hmong.py')]
    print('Voice Studio Hmong · Kiểm tra tệp mô hình đã lưu...', flush=True)
    result = subprocess.run(command + ['--verify-only'], cwd=BASE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode:
        if args.check:
            print('Thiếu mô hình hoặc checksum không đạt. Mở tool để chuẩn bị lần đầu bằng mạng được phép.', flush=True)
            return 1
        print('Lần đầu cần tải khoảng 1,4 GB F5-Hmong/Vocos từ nguồn chính thức. Giữ cửa sổ này mở.', flush=True)
        subprocess.run(command, cwd=BASE, check=True)
    if args.check or args.setup_only:
        print('PASS: thư viện và checksum mô hình. Chưa chạy suy luận trong bước kiểm tra này.', flush=True)
        return 0
    from portable_launcher import main as launch
    launch(open_browser=not args.no_browser)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print('LOI: ' + str(exc), flush=True)
        sys.exit(1)
