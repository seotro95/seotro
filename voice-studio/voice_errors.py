"""Actionable runtime failures without exposing raw tracebacks in the browser."""
from __future__ import annotations

import errno
import os
import re
import subprocess
from pathlib import Path


_PUBLIC_MODULES = {
    'torch', 'torchaudio', 'numpy', 'soundfile', 'soxr', 'scipy', 'librosa',
    'unidecode', 'phonemizer', 'numba', 'llvmlite', 'f5_tts', 'omegaconf',
    'transformers', 'tokenizers', 'vocos', 'pydub', 'einops', 'psutil',
    'vieneu', 'qwen_tts', 'yaml',
}


def describe_failure(exc=None, *, returncode=None, log_tail=''):
    """Classify an exception or a dead worker's log; never return its raw text."""
    detail = ((str(exc) + '\n') if exc is not None else '') + str(log_tail)
    lowered = detail.lower()
    windows_code = returncode & 0xffffffff if isinstance(returncode, int) else None
    winerror = getattr(exc, 'winerror', None)
    error_number = getattr(exc, 'errno', None)
    requirements = ('requirements-hmong.txt' if os.getenv('VOICE_STUDIO_VARIANT') == 'hmong'
                    else 'requirements.txt')
    if (isinstance(exc, MemoryError) or 'out of memory' in lowered
            or 'memoryerror' in lowered or 'cannot allocate memory' in lowered
            or winerror in {8, 14, 1455} or windows_code in {0xc0000017, 0xc000009a, 0xc000012d}):
        return ('Không đủ RAM/VRAM hoặc bộ nhớ ảo để tạo giọng. Đóng bớt ứng dụng, '
                'chọn HMOOB_DEVICE=cpu rồi mở lại tool; trên Windows kiểm tra bộ nhớ ảo của hệ thống.')
    if (error_number == errno.ENOSPC or winerror == 112
            or 'no space left on device' in lowered or 'not enough space on the disk' in lowered):
        return 'Ổ đĩa lưu dữ liệu đã đầy. Giải phóng dung lượng rồi bấm Tiếp tục để giữ các đoạn đã tạo.'
    if (isinstance(exc, PermissionError) or error_number in {errno.EACCES, errno.EPERM}
            or 'permissionerror:' in lowered):
        return ('Tool không có quyền đọc hoặc ghi tệp cần thiết. Giải nén gói vào thư mục có quyền ghi, '
                'kiểm tra phần mềm bảo vệ rồi mở lại tool.')
    if isinstance(exc, ModuleNotFoundError) or 'modulenotfounderror:' in lowered:
        module = getattr(exc, 'name', None)
        if not module:
            matches = re.findall(r"No module named ['\"]([A-Za-z0-9_.]+)['\"]", detail)
            module = matches[-1] if matches else None
        module = module.split('.')[0] if isinstance(module, str) else None
        label = ' (' + module + ')' if module in _PUBLIC_MODULES else ''
        return ('Thiếu thư viện tạo giọng' + label + '. Dùng gói Portable đầy đủ và giải nén toàn bộ; '
                f'nếu chạy mã nguồn, cài lại {requirements} trong đúng môi trường Python.')
    if (winerror in {126, 127, 193, 1114} or windows_code in {0xc000007b, 0xc0000135, 0xc0000142}
            or 'dll load failed' in lowered or 'error loading' in lowered and '.dll' in lowered
            or re.search(r'winerror\s+(126|127|193|1114)\b', lowered)):
        return ('Không nạp được thư viện DLL của bộ tạo giọng. Giải nén lại toàn bộ gói Portable, '
                'cài Microsoft Visual C++ Redistributable 2015–2022 x64 rồi mở lại tool. '
                'Nếu vừa cài bộ CUDA, kiểm tra lại môi trường CPU/GPU.')
    command = getattr(exc, 'cmd', None)
    executable = command[0] if isinstance(command, (list, tuple)) and command else command
    ffmpeg = isinstance(executable, str) and Path(executable).stem.lower() == 'ffmpeg'
    if ffmpeg and isinstance(exc, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
        return ('FFmpeg không xử lý được âm thanh. Giải nén đầy đủ thư mục FFmpeg của gói Portable, '
                'kiểm tra dung lượng đĩa rồi thử lại; xem nhật ký tác vụ để biết bước âm thanh bị lỗi.')
    if isinstance(exc, FileNotFoundError):
        return ('Thiếu tệp mô hình hoặc công cụ âm thanh. Tải model giọng đã chọn hoặc giải nén '
                'đầy đủ gói Portable, gồm thư mục FFmpeg.')
    if isinstance(exc, ImportError) or 'importerror:' in lowered:
        return ('Các thư viện tạo giọng không tương thích hoặc chưa cài đủ. Giải nén lại gói Portable '
                f'đầy đủ; nếu chạy mã nguồn, cài {requirements} trong đúng môi trường Python.')
    code = f' (mã thoát {returncode})' if isinstance(returncode, int) else ''
    if returncode == -9:
        return ('Tiến trình tạo giọng bị hệ điều hành dừng' + code + '. Đóng bớt ứng dụng để có đủ RAM, '
                'mở lại tool rồi bấm Tiếp tục; xem nhật ký tác vụ nếu lỗi lặp lại.')
    return ('Tiến trình tạo giọng dừng bất thường' + code + '. Mở lại tool bằng launcher trong gói '
            'Portable đầy đủ rồi thử lại; xem nhật ký tác vụ để xác định thư viện hoặc bước xử lý bị lỗi.')
