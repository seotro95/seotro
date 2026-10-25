"""Prepare dependencies and verified model files on the first launch."""
import argparse
import importlib.metadata
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def installed(name, version=None):
    value = package_version(name)
    return value is not None and (version is None or value.split('+')[0] == version)


def pip(*args):
    subprocess.run([sys.executable, '-m', 'pip', 'install', *args], check=True, cwd=BASE)


def prepare_torch(gpu=False, cpu=False):
    from hardware import detect_nvidia, probe_torch, TORCH_VERSION
    versions = [package_version(name) for name in ('torch', 'torchaudio')]
    paired = all(version and version.split('+')[0] == TORCH_VERSION for version in versions) and versions[0] == versions[1]
    # Preserve an existing matched build; --cpu selects CPU at launch even when
    # CUDA wheels are installed. Never reinstall GBs merely to disable the GPU.
    if paired:
        if cpu:
            print('Dung lai PyTorch/torchaudio ' + versions[0] + ' theo lua chon --cpu.', flush=True)
            return
        suffix = versions[0].partition('+')[2]
        runtime = probe_torch() if suffix.startswith('cu') or not suffix else {}
        if suffix.startswith('cu') or runtime.get('cuda_build'):
            if gpu and not runtime.get('cuda_available'):
                raise RuntimeError(runtime.get('reason') or 'PyTorch CUDA da cai nhung chua dung duoc GPU. Kiem tra driver NVIDIA hoac chay voi --cpu.')
            print('Bo PyTorch CUDA da cai; giu nguyen ' + versions[0] + '.', flush=True)
            if not runtime.get('cuda_available'):
                print(runtime.get('reason') or 'GPU chua san sang; che do auto se dung CPU.', flush=True)
            return
    hardware = detect_nvidia() if not cpu else {}
    wheel = hardware.get('wheel') or 'cpu'
    if gpu and wheel == 'cpu':
        raise RuntimeError(hardware.get('reason') or 'Khong tim thay GPU NVIDIA va driver tuong thich. Bo CPU hien co duoc giu nguyen.')
    if paired and wheel == 'cpu':
        print('Dung lai PyTorch/torchaudio ' + versions[0] + '.', flush=True)
        if hardware.get('reason'):
            print(hardware['reason'], flush=True)
        return
    if paired:
        print('Phat hien GPU NVIDIA tuong thich. Nang bo CPU sang CUDA de tang toc; can tai vai GB. Dung --cpu neu muon giu CPU.', flush=True)
    print('Dang cai PyTorch/torchaudio ' + TORCH_VERSION + ' (' + wheel + '). Lan dau can Internet va vai GB dia trong.', flush=True)
    if hardware.get('reason'):
        print(hardware['reason'], flush=True)
    args = ['torch==' + TORCH_VERSION, 'torchaudio==' + TORCH_VERSION,
            '--index-url', 'https://download.pytorch.org/whl/' + wheel]
    if any(versions):
        # ==2.6.0 also matches +cpu; force replacing that build for --gpu.
        args.append('--force-reinstall')
    pip(*args)
    if wheel != 'cpu':
        runtime = probe_torch()
        if not runtime.get('cuda_available'):
            message = runtime.get('reason') or 'Da cai bo CUDA nhung GPU chua hoat dong. Kiem tra driver NVIDIA; co the chay voi --cpu.'
            if gpu:
                raise RuntimeError(message)
            print(message, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Chuan bi Hmong Nhanh va dung lai bo AI da cai.')
    devices = parser.add_mutually_exclusive_group()
    devices.add_argument('--gpu', action='store_true', help='Yeu cau GPU NVIDIA va driver tuong thich, nang bo CPU len CUDA neu can.')
    devices.add_argument('--cpu', action='store_true', help='Giu bo CPU hien co, khong tu dong nang len CUDA.')
    args = parser.parse_args(argv)
    if not all(installed(name) for name in ('fastapi', 'uvicorn', 'pydantic')):
        print('Dang cai giao dien doc van ban...', flush=True)
        pip('-r', str(BASE / 'requirements.txt'))
    prepare_torch(gpu=args.gpu, cpu=args.cpu)
    if not installed('f5-tts', '1.1.22') or not all(installed(name) for name in ('soundfile', 'scipy', 'numpy', 'librosa')):
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
