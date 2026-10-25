"""Small hardware reports without importing PyTorch into the HTTP process."""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time


TORCH_VERSION = '2.6.0'
_lock = threading.Lock()
_reports = {}
_pending = set()
_CACHE_SECONDS = 300


def cpu_threads():
    try:
        requested = int(os.getenv('HMONG_CPU_THREADS', '4'))
    except ValueError:
        requested = 4
    return max(1, min(requested, os.cpu_count() or 1))


def detect_nvidia():
    """Inspect the driver, not an installed CUDA toolkit or environment path."""
    binary = shutil.which('nvidia-smi')
    result = {'detected': False, 'name': '', 'cuda_version': None,
              'compute_capability': None, 'wheel': None, 'reason': ''}
    if not binary:
        return result
    try:
        summary = subprocess.run([binary], capture_output=True, text=True,
                                 timeout=4, check=True)
        match = re.search(r'CUDA Version:\s*(\d+)\.(\d+)', summary.stdout)
        if match:
            result['cuda_version'] = (int(match[1]), int(match[2]))
        query = subprocess.run(
            [binary, '--query-gpu=name,compute_cap', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=4)
        if query.returncode:
            query = subprocess.run(
                [binary, '--query-gpu=name', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=4, check=True)
        first = next((line.strip() for line in query.stdout.splitlines() if line.strip()), '')
        if not first:
            return result
        name, _, capability = first.rpartition(',')
        if not name:
            name, capability = first, ''
        result.update(detected=True, name=name.strip())
        if re.fullmatch(r'\d+\.\d+', capability.strip()):
            result['compute_capability'] = tuple(map(int, capability.strip().split('.')))
        cap = result['compute_capability']
        # PyTorch 2.6's cu118/cu124 builds do not support Blackwell.
        blackwell = (cap is not None and cap[0] >= 10) or bool(re.search(r'\bBlackwell\b|\bRTX\s+50[5-9]0\b', result['name'], re.I))
        if blackwell:
            result['reason'] = 'GPU Blackwell cần bản PyTorch/CUDA mới hơn bộ 2.6 hiện tại; bộ cài này dùng CPU.'
        elif cap is not None and cap < (5, 0):
            result['reason'] = 'GPU này quá cũ cho bản PyTorch 2.6 được hỗ trợ; dùng CPU.'
        elif result['cuda_version'] is None:
            result['reason'] = 'Chưa xác định được phiên bản CUDA mà driver hỗ trợ; dùng CPU.'
        elif result['cuda_version'] >= (12, 4):
            result['wheel'] = 'cu124'
        elif result['cuda_version'] >= (11, 8):
            result['wheel'] = 'cu118'
        else:
            result['reason'] = 'Driver NVIDIA chưa hỗ trợ CUDA 11.8; cập nhật driver để dùng GPU.'
    except (OSError, subprocess.SubprocessError):
        result['reason'] = 'Không đọc được driver NVIDIA; dùng CPU cho đến khi driver hoạt động.'
    return result


_TORCH_PROBE = r'''
import json
import torch
cuda = bool(torch.cuda.is_available())
capability = list(torch.cuda.get_device_capability(0)) if cuda else None
name = torch.cuda.get_device_name(0) if cuda else ''
reason = ''
if cuda:
    try:
        # Device enumeration alone also succeeds with unsupported architectures.
        # A tiny kernel verifies that this installed build can use device zero.
        torch.ones(1, device='cuda').add_(1).cpu()
    except Exception:
        cuda = False
        reason = 'PyTorch thấy GPU nhưng chưa chạy được CUDA; kiểm tra driver và bản PyTorch hỗ trợ GPU này.'
mps = bool(getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available())
print('HMONG_HARDWARE=' + json.dumps({'cuda_available': cuda,
    'cuda_build': torch.version.cuda, 'mps_available': mps, 'device_name': name,
    'capability': capability, 'torch_version': torch.__version__, 'reason': reason}))
'''


def probe_torch():
    """One bounded subprocess; caller decides whether to cache or run in background."""
    try:
        result = subprocess.run([sys.executable, '-c', _TORCH_PROBE],
                                capture_output=True, text=True, timeout=15, check=True)
        payload = next(line.removeprefix('HMONG_HARDWARE=') for line in reversed(result.stdout.splitlines())
                       if line.startswith('HMONG_HARDWARE='))
        return json.loads(payload)
    except (OSError, subprocess.SubprocessError, StopIteration, ValueError):
        return {'cuda_available': False, 'cuda_build': None, 'mps_available': False,
                'device_name': '', 'reason': 'Chưa kiểm tra được PyTorch; xem trạng thái bộ tạo giọng.'}


def _make_report(requested, threads, nvidia, runtime):
    cuda = bool(runtime.get('cuda_available'))
    reason = runtime.get('reason', '')
    capability = runtime.get('capability')
    version = str(runtime.get('torch_version', '')).split('+')[0]
    if cuda and capability and capability[0] >= 10 and version.startswith('2.6.'):
        cuda = False
        reason = 'GPU Blackwell chưa tương thích với PyTorch 2.6; cần bộ PyTorch/CUDA hỗ trợ GPU này.'
    mps = bool(runtime.get('mps_available'))
    device = 'cpu'
    if requested == 'auto':
        device = 'cuda' if cuda else 'mps' if mps else 'cpu'
    elif requested == 'cuda':
        if cuda:
            device = 'cuda'
        else:
            reason = reason or 'Đã yêu cầu CUDA nhưng PyTorch chưa dùng được GPU; tạo giọng sẽ báo lỗi. Chọn auto hoặc sửa bộ CUDA.'
    elif requested == 'mps':
        if mps:
            device = 'mps'
        else:
            reason = reason or 'Đã yêu cầu MPS nhưng máy chưa dùng được MPS; chọn auto hoặc cpu.'
    elif requested != 'cpu':
        reason = 'HMONG_F5_DEVICE chỉ nhận auto, cpu, cuda hoặc mps.'
    if not reason and requested == 'cpu':
        reason = 'Đang dùng CPU theo thiết lập của bạn.'
    if not reason and device == 'cpu' and nvidia.get('detected'):
        reason = nvidia.get('reason') or ('Máy có NVIDIA nhưng PyTorch hiện dùng CPU. Chạy MO_HMONG_NHANH.bat --gpu để cài bộ CUDA phù hợp.'
                                         if not runtime.get('cuda_build') else 'PyTorch CUDA đã cài nhưng chưa truy cập được GPU; kiểm tra driver NVIDIA.')
    if not reason:
        reason = {'cuda': 'Sẵn sàng tạo giọng bằng GPU NVIDIA.', 'mps': 'Sẵn sàng tạo giọng bằng Apple MPS.',
                  'cpu': 'Đang dùng CPU.'}[device]
    return {'requested': requested, 'device': device, 'cuda_available': cuda,
            'device_name': runtime.get('device_name') if device == 'cuda' else 'Apple MPS' if device == 'mps' else platform.processor() or 'CPU',
            'cpu_threads': threads, 'gpu_detected': bool(nvidia.get('detected') or cuda or mps),
            'reason': reason, 'probing': False}


def _refresh(key):
    try:
        report = _make_report(key[0], key[1], detect_nvidia(), probe_torch())
        with _lock:
            _reports[key] = (time.monotonic(), report)
    finally:
        with _lock:
            _pending.discard(key)


def hardware_info(probe=True):
    """Return immediately; reuse one report while a bounded probe runs separately."""
    requested = os.getenv('HMONG_F5_DEVICE', 'auto').strip().lower()
    key = (requested, cpu_threads(), sys.executable)
    with _lock:
        cached = _reports.get(key)
        if probe and (not cached or time.monotonic() - cached[0] > _CACHE_SECONDS) and key not in _pending:
            _pending.add(key)
            threading.Thread(target=_refresh, args=(key,), daemon=True).start()
        if cached:
            return dict(cached[1])
    return {'requested': requested, 'device': 'cpu', 'cuda_available': False,
            'device_name': platform.processor() or 'CPU', 'cpu_threads': key[1],
            'gpu_detected': False, 'reason': 'Đang kiểm tra thiết bị và PyTorch…' if probe else 'Chưa kiểm tra GPU.',
            'probing': probe}
