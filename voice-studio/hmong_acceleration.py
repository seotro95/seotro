"""Optional NVIDIA runtime, isolated from the working CPU installation.

Importing this module never imports torch or downloads anything. A saved marker
is a location-bound installation record, not evidence of any throughput target.
The launcher checks actual GPU execution before handing a new process over.
"""
from __future__ import annotations

from contextlib import contextmanager
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import sysconfig
import venv


TORCH_VERSION = '2.8.0+cu128'
CUDA_INDEX = 'https://download.pytorch.org/whl/cu128'
MARKER_NAME = 'cuda-runtime.json'
RUNTIME_NAME = '.runtime-cuda'

# Arguments are passed separately; no project path is interpolated into code.
PROBE = r'''
import json, pathlib, sys
from importlib import metadata
import torch, torchaudio
if not torch.cuda.is_available():
    raise RuntimeError('PyTorch chua chay duoc CUDA; kiem tra GPU va driver NVIDIA.')
value = torch.ones((32, 32), device='cuda')
result = value @ value
if not bool(torch.isfinite(result).all().item()) or float(result[0, 0].item()) != 32.0:
    raise RuntimeError('GPU tensor check failed')
torch.cuda.synchronize()
print(json.dumps({'prefix': str(pathlib.Path(sys.prefix).resolve()),
    'torch_version': torch.__version__, 'torchaudio_version': torchaudio.__version__,
    'cuda_version': torch.version.cuda, 'gpu': torch.cuda.get_device_name(),
    'torch_file': str(pathlib.Path(torch.__file__).resolve()),
    'torchaudio_file': str(pathlib.Path(torchaudio.__file__).resolve()),
    'f5_version': metadata.version('f5-tts'), 'gpu_tensor_test': True}))
'''


def data_directory(base):
    return Path(os.getenv('VOICE_STUDIO_DATA_DIR', str(Path(base) / '.data-hmong'))).expanduser().resolve()


def runtime_directory(base):
    return data_directory(base) / RUNTIME_NAME


def runtime_python(runtime):
    return Path(runtime) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def _identity(base):
    # Keep the executable spelling: venv python may be a symlink to base Python.
    return {'application': str(Path(base).resolve()),
            'base_executable': os.path.abspath(sys.executable),
            'base_prefix': str(Path(sys.prefix).resolve()),
            'python': list(sys.version_info[:3]), 'platform': sys.platform,
            'machine': platform.machine().lower()}


def _environment():
    environment = dict(os.environ, PYTHONNOUSERSITE='1', PYTHONUTF8='1')
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONPATH', None)
    return environment


def _pip_environment():
    environment = _environment()
    # Inherited pip target/user/index settings must not redirect this explicit
    # install into the working CPU environment or another package source.
    for name in tuple(environment):
        if name.startswith('PIP_') and name not in {'PIP_CERT', 'PIP_CLIENT_CERT', 'PIP_PROXY'}:
            environment.pop(name)
    environment['PIP_CONFIG_FILE'] = os.devnull
    return environment


def _read_marker(base):
    path = data_directory(base) / MARKER_NAME
    try:
        if path.stat().st_size > 32000:
            raise ValueError('marker too large')
        result = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(result, dict):
            raise ValueError('invalid marker')
        return result
    except (OSError, ValueError):
        return None


def _marker_problem(base, marker):
    runtime = runtime_directory(base)
    if marker is None:
        return 'Chưa cài bộ NVIDIA riêng hoặc thông tin cài đặt không đọc được.'
    if marker.get('schema') != 1 or marker.get('identity') != _identity(base):
        return 'Thư mục tool hoặc Python đã thay đổi sau khi cài bộ NVIDIA.'
    if marker.get('runtime') != str(runtime) or marker.get('torch_version') != TORCH_VERSION:
        return 'Thông tin bộ NVIDIA không khớp bản ứng dụng này.'
    if not (runtime / 'pyvenv.cfg').is_file() or not runtime_python(runtime).is_file():
        return 'Thiếu Python trong bộ NVIDIA riêng.'
    return None


def runtime_status(base):
    """Read installation identity only; this does not claim live GPU readiness."""
    marker = _read_marker(base)
    problem = _marker_problem(base, marker)
    return {'installed': marker is not None, 'identity_valid': problem is None,
            'runtime': str(runtime_directory(base)), 'problem': problem,
            'last_verified_gpu': marker.get('gpu') if marker else None,
            'throughput_verified': False}


def _probe(interpreter, *, runtime=None):
    try:
        result = subprocess.run([str(interpreter), '-c', PROBE], env=_environment(),
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=90, check=False)
        if result.returncode:
            raise ValueError(result.stderr[-1600:] or result.stdout[-1600:] or 'CUDA probe failed')
        details = json.loads(result.stdout.strip().splitlines()[-1])
        if details.get('gpu_tensor_test') is not True or details.get('f5_version') != '1.1.22':
            raise ValueError('GPU/F5 version check failed')
        if runtime is not None:
            runtime = Path(runtime).resolve()
            if (details.get('prefix') != str(runtime)
                    or details.get('torch_version') != TORCH_VERSION
                    or details.get('torchaudio_version') != TORCH_VERSION
                    or details.get('cuda_version') != '12.8'):
                raise ValueError('CUDA runtime version does not match the pinned installation')
            for field in ('torch_file', 'torchaudio_file'):
                if not Path(details[field]).resolve().is_relative_to(runtime):
                    raise ValueError('PyTorch was imported from outside the NVIDIA environment')
        return details
    except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Không chạy được phép thử CUDA. Kiểm tra GPU và driver NVIDIA tương thích CUDA 12.8. '
                           'Chạy lại tools/install_hmong_cuda.bat; bộ CPU và dữ liệu vẫn được giữ. '
                           + str(exc)[-1800:]) from None


def preferred_interpreter(base, requested_device=None):
    """Return verified managed GPU Python, or stay in the current interpreter."""
    requested = (requested_device or os.getenv('HMOOB_DEVICE', 'auto')).lower()
    if requested not in {'auto', 'cpu', 'cuda', 'mps'}:
        raise RuntimeError('HMOOB_DEVICE chỉ nhận auto, cpu, cuda hoặc mps.')
    runtime = runtime_directory(base)
    if requested in {'cpu', 'mps'} or Path(sys.prefix).resolve() == runtime:
        return None  # Explicit override, or already in the handed-over runtime.
    marker = _read_marker(base)
    problem = _marker_problem(base, marker)
    if problem is None:
        try:
            _probe(runtime_python(runtime), runtime=runtime)
            return runtime_python(runtime)
        except RuntimeError as exc:
            problem = str(exc)
    if requested == 'cuda':
        # A custom/source installation can already have a working CUDA build.
        try:
            _probe(sys.executable)
            return None
        except RuntimeError:
            raise RuntimeError((problem or 'Chưa có CUDA hoạt động.')
                               + ' Chạy tools/install_hmong_cuda.bat trên máy có GPU NVIDIA, '
                               'hoặc đặt HMOOB_DEVICE=cpu để dùng bộ CPU hiện tại.') from None
    if marker is not None or (data_directory(base) / MARKER_NAME).is_file():
        print('Bộ NVIDIA đã lưu chưa dùng được: ' + str(problem)
              + ' Dùng Python hiện tại. Chạy lại tools/install_hmong_cuda.bat để sửa.', flush=True)
    return None


def _preflight():
    if (sys.version_info[:2] not in {(3, 10), (3, 11), (3, 12)}
            or struct.calcsize('P') != 8 or sys.platform not in {'win32', 'linux'}
            or platform.machine().lower() not in {'amd64', 'x86_64'}):
        raise RuntimeError('Bộ NVIDIA cần Python 3.10–3.12 x64 trên Windows hoặc Linux x86_64.')
    binary = shutil.which('nvidia-smi')
    if not binary:
        raise RuntimeError('Chưa tìm thấy GPU/driver NVIDIA (nvidia-smi). '
                           'Không tải hoặc thay đổi bộ CPU. Máy chỉ có CPU không dùng được bộ CUDA.')
    try:
        result = subprocess.run([binary, '--query-gpu=name', '--format=csv,noheader'],
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=15, check=False)
        if result.returncode or not result.stdout.strip():
            raise ValueError('NVIDIA driver did not report a GPU')
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise RuntimeError('Driver NVIDIA chưa nhận GPU. Kiểm tra driver trước khi cài CUDA; '
                           'chưa thay đổi bộ CPU hoặc tải thư viện.') from None
    try:
        if metadata.version('f5-tts') != '1.1.22':
            raise metadata.PackageNotFoundError('f5-tts 1.1.22')
    except metadata.PackageNotFoundError:
        raise RuntimeError('Cài bộ CPU Hmong đầy đủ trước bằng install_hmong.bat, '
                           'rồi chạy lại tools/install_hmong_cuda.bat bằng cùng Python.') from None


@contextmanager
def _installation_lock(data):
    # OS locks release automatically if installation is interrupted.
    path = Path(data) / '.cuda-install.lock'
    with path.open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        try:
            if os.name == 'nt':
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Một cửa sổ khác đang cài bộ NVIDIA. Đợi cửa sổ đó hoàn tất.') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _site_packages(runtime):
    if os.name == 'nt':
        return runtime / 'Lib' / 'site-packages'
    return runtime / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'


def install_cuda(base):
    """Explicit installation only. Publish readiness after real GPU execution."""
    _preflight()  # No filesystem mutation or network request before this passes.
    runtime = runtime_directory(base)
    if Path(sys.prefix).resolve() == runtime:
        raise RuntimeError('Chạy tools/install_hmong_cuda.bat bằng Python CPU đi kèm; '
                           'không cài lại vào môi trường NVIDIA đang chạy.')
    data = data_directory(base)
    data.mkdir(parents=True, exist_ok=True)
    marker = data / MARKER_NAME
    with _installation_lock(data):
        # A failed repair must not leave a prior ready marker in place.
        marker.unlink(missing_ok=True)
        print('Đang chuẩn bị bộ NVIDIA riêng. Cần Internet và vài GB dung lượng; '
              'không thay thư viện CPU hoặc dữ liệu giọng.', flush=True)
        venv.EnvBuilder(system_site_packages=True, with_pip=True).create(runtime)
        site = _site_packages(runtime)
        site.mkdir(parents=True, exist_ok=True)
        inherited = sorted({str(Path(sysconfig.get_path(name)).resolve()) for name in ('purelib', 'platlib')})
        if any('\n' in path or '\r' in path for path in inherited):
            raise RuntimeError('Đường dẫn thư viện Python không hợp lệ.')
        (site / 'hmong_cpu_dependencies.pth').write_text('\n'.join(inherited) + '\n', encoding='utf-8')
        interpreter = runtime_python(runtime)
        command = [str(interpreter), '-m', 'pip', 'install', '--upgrade', '--no-cache-dir',
                   'torch==' + TORCH_VERSION, 'torchaudio==' + TORCH_VERSION,
                   '--index-url', CUDA_INDEX]
        result = subprocess.run(command, env=_pip_environment(), check=False)
        if result.returncode:
            raise RuntimeError('Cài PyTorch CUDA chưa thành công. Có thể chạy lại tools/install_hmong_cuda.bat; '
                               'bộ CPU và dữ liệu vẫn được giữ nguyên.')
        result = subprocess.run([str(interpreter), '-m', 'pip', 'check'], env=_pip_environment(), check=False)
        if result.returncode:
            raise RuntimeError('Thư viện NVIDIA chưa khớp. Bộ CPU vẫn được giữ; '
                               'chạy lại tools/install_hmong_cuda.bat để sửa.')
        details = _probe(interpreter, runtime=runtime)
        record = {'schema': 1, 'identity': _identity(base), 'runtime': str(runtime),
                  'torch_version': TORCH_VERSION, 'gpu': details['gpu'],
                  'cuda_version': details['cuda_version'], 'gpu_tensor_test': True,
                  'throughput_verified': False}
        temporary = marker.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(marker)
    print('PASS: bộ NVIDIA riêng chạy được phép thử GPU. Đóng tool rồi mở lại để dùng CUDA. '
          'Chưa đo tốc độ tạo giọng; không xác nhận mục tiêu 30×.', flush=True)
    return record
