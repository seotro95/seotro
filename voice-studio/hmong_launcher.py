"""Prepare verified Hmong files, then open the shared studio with its own data."""
import argparse
from importlib import metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def check_dependencies():
    packages = ('f5-tts', 'torch', 'torchaudio', 'fastapi', 'uvicorn', 'httpx',
                'python-multipart', 'pydantic', 'psutil', 'soundfile', 'soxr')
    versions, missing = {}, []
    for name in packages:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
    if missing:
        raise RuntimeError('Thiếu thư viện trong Python đang chạy: ' + ', '.join(missing)
                           + '. Mở gói Windows đầy đủ bằng MO_VOICE_STUDIO_HMONG.bat, '
                           'hoặc chạy install_hmong.bat để cài môi trường mã nguồn riêng.')
    if (versions['f5-tts'] != '1.1.22'
            or versions['torch'].split('+')[0] != versions['torchaudio'].split('+')[0]):
        raise RuntimeError('Thư viện F5/PyTorch không khớp. Giải nén lại gói Windows đầy đủ '
                           'hoặc chạy install_hmong.bat trong bộ mã nguồn đầy đủ.')


def check_audio_tools():
    # Support both the portable root and a source installation's verified tools.
    candidates = (BASE.parent / 'ffmpeg' / 'bin', BASE / 'ffmpeg' / 'bin')
    existing = [str(folder) for folder in candidates if folder.is_dir()]
    if existing:
        os.environ['PATH'] = os.pathsep.join(existing + [os.environ.get('PATH', '')])
    binaries = [shutil.which(name) for name in ('ffmpeg', 'ffprobe')]
    if not all(binaries):
        raise RuntimeError('Thiếu FFmpeg hoặc ffprobe. Giải nén toàn bộ gói Windows '
                           'và mở MO_VOICE_STUDIO_HMONG.bat; với mã nguồn, chạy install_hmong.bat.')
    try:
        for binary in binaries:
            subprocess.run([binary, '-version'], check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise RuntimeError('FFmpeg hoặc ffprobe không chạy được. Giải nén lại toàn bộ gói Windows '
                           'hoặc chạy install_hmong.bat để chuẩn bị công cụ đã xác minh.') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description='Voice Studio Hmong')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='Verify prerequisites offline; do not download.')
    action.add_argument('--setup-only', action='store_true', help='Prepare model files and exit.')
    parser.add_argument('--no-browser', action='store_true')
    action.add_argument('--install-cuda', action='store_true', help='Install a separate NVIDIA runtime explicitly.')
    args = parser.parse_args(argv)
    try:
        from bundle_check import validate_bundle
    except ModuleNotFoundError:
        raise RuntimeError('Thiếu bundle_check.py. Giải nén TOÀN BỘ ZIP Voice Studio Hmong '
                           'và mở MO_VOICE_STUDIO_HMONG.bat; các tệp .py rời không đủ để chạy.') from None
    validate_bundle(BASE)
    os.environ['VOICE_STUDIO_VARIANT'] = 'hmong'
    os.environ.setdefault('VOICE_STUDIO_DATA_DIR', str(BASE / '.data-hmong'))
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    os.environ.setdefault('PYTHONUTF8', '1')
    from hmong_acceleration import install_cuda, preferred_interpreter
    if args.install_cuda:
        install_cuda(BASE)
        return 0
    interpreter = preferred_interpreter(BASE)
    if interpreter is not None:
        # Worker children inherit this interpreter through sys.executable.
        environment = dict(os.environ)
        environment.pop('PYTHONHOME', None)
        environment.pop('PYTHONPATH', None)
        forwarded = list(sys.argv[1:] if argv is None else argv)
        return subprocess.call([str(interpreter), str(BASE / 'hmong_launcher.py'), *forwarded],
                               cwd=BASE, env=environment)
    check_dependencies()
    check_audio_tools()
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
        print('PASS: đủ ứng dụng/giao diện, giọng mặc định, FFmpeg, thư viện và checksum mô hình. '
              'Chưa chạy suy luận trong bước kiểm tra này.', flush=True)
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
