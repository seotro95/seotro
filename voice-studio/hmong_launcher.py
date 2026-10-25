"""Prepare verified Hmong files, then open the shared studio with its own data."""
import argparse
from importlib import metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def selected_backend():
    backend = os.getenv('HMOOB_BACKEND', 'f5').lower()
    if backend not in {'f5', 'native'}:
        raise RuntimeError('HMOOB_BACKEND chỉ nhận f5 hoặc native. '
                           'Mở MO_VOICE_STUDIO_HMONG.bat của gói đầy đủ; F5 nằm trong tools/MO_F5_HMONG.bat.')
    return backend


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


def select_interpreter(preferred_interpreter, backend):
    """Recover an inherited CUDA preference when its runtime cannot run."""
    if backend == 'native':
        from hmong_native import runtime_settings
        settings = runtime_settings()
        if settings['compatibility_note']:
            print(settings['compatibility_note'], flush=True)
        os.environ['HMOOB_PRECISION'] = 'fp32'
    try:
        return preferred_interpreter(BASE)
    except RuntimeError:
        if os.getenv('HMOOB_DEVICE', 'auto').strip().lower() != 'cuda':
            raise
        os.environ['HMOOB_DEVICE'] = 'cpu'
        print('Bộ NVIDIA được chọn trước đây chưa chạy được. Đang dùng bộ CPU để tạo giọng. '
              'Có thể cài lại bộ NVIDIA trong tools khi cần.', flush=True)
        return preferred_interpreter(BASE)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Voice Studio Hmong')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='Verify prerequisites offline; do not download.')
    action.add_argument('--setup-only', action='store_true', help='Prepare model files and exit.')
    action.add_argument('--probe-runtime', action='store_true', help='Check actual imports and tensor operations offline.')
    action.add_argument('--test-voice', action='store_true', help='Create real male/female test WAVs and a diagnostic report.')
    parser.add_argument('--no-browser', action='store_true')
    action.add_argument('--install-cuda', action='store_true', help='Install a separate NVIDIA runtime explicitly.')
    args = parser.parse_args(argv)
    backend = selected_backend()
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
    if not any((args.check, args.setup_only, args.install_cuda, args.probe_runtime, args.test_voice)):
        # Reopening a proven running instance must not import a second Torch
        # stack while its active speech job already owns the available memory.
        from portable_launcher import _existing_studio, main as launch
        if _existing_studio(Path(os.environ['VOICE_STUDIO_DATA_DIR']).resolve(), BASE):
            return launch(open_browser=not args.no_browser)
    from hmong_acceleration import install_cuda, preferred_interpreter
    if args.install_cuda:
        install_cuda(BASE)
        return 0
    interpreter = select_interpreter(preferred_interpreter, backend)
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
    from hmong_health import run_runtime_probe, test_voices
    print('Đang thử bộ chạy tạo giọng (thư viện và phép tính thực tế)…', flush=True)
    runtime_report = run_runtime_probe(BASE)
    if not runtime_report.get('ok'):
        raise RuntimeError(runtime_report.get('message', 'Bộ chạy tạo giọng chưa sẵn sàng.')
                           + ' Xem .data/diagnostics/runtime-check.json và hướng dẫn đầy đủ.')
    if args.probe_runtime:
        print('PASS: bộ chạy đã thực hiện được phép thử thư viện/tensor. Chưa tạo lời đọc.', flush=True)
        return 0
    prepare_script = 'prepare_hmong_native.py' if backend == 'native' else 'prepare_hmong.py'
    command = [sys.executable, str(BASE / prepare_script)]
    label = 'Hmong nhanh thử nghiệm' if backend == 'native' else 'F5-Hmong'
    print('Voice Studio Hmong · ' + label + ' · Kiểm tra tệp mô hình đã lưu...', flush=True)
    result = subprocess.run(command + ['--verify-only'], cwd=BASE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode:
        if args.check:
            print('Thiếu mô hình hoặc checksum không đạt. Mở tool để chuẩn bị lần đầu bằng mạng được phép.', flush=True)
            return 1
        if backend == 'native':
            print('Lần đầu cần tải khoảng 580 MB mô hình đọc Hmong, chuyển giọng và dấu nhận diện âm thanh AI. '
                  'Chưa kiểm chứng mục tiêu 30×. '
                  'Giữ cửa sổ này mở.', flush=True)
        else:
            print('Lần đầu cần tải khoảng 1,4 GB F5-Hmong/Vocos từ nguồn chính thức. Giữ cửa sổ này mở.', flush=True)
        subprocess.run(command, cwd=BASE, check=True)
    if args.test_voice:
        report = test_voices(BASE)
        if not report.get('ok'):
            raise RuntimeError(report.get('message', 'Chưa tạo được voice thử.'))
        print('PASS: đã tạo WAV nam và nữ thật. Mở .data/diagnostics để nghe; '
              'xem speech-check.json để đối chiếu kết quả.', flush=True)
        return 0
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
