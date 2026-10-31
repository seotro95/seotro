"""Give the pinned Windows native loader an ASCII path to its verified model.

audio.cpp constructs a narrow Windows filesystem path, whereas GGML interprets
filenames as UTF-8. ASCII works consistently in both layers. An owned temporary
hard link handles Unicode folders even when the volume has no 8.3 filenames;
the large public GGUF is never copied. Reference audio stays in Python.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import stat
import tempfile


def _on_windows():
    return os.name == 'nt'


def _ascii_bytes(path):
    try:
        return str(path).encode('ascii')
    except UnicodeEncodeError:
        return None


def _windows_short_path(path):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    function = kernel.GetShortPathNameW
    function.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD)
    function.restype = wintypes.DWORD
    needed = function(str(path), None, 0)
    if not needed or needed > 32768:
        return None
    buffer = ctypes.create_unicode_buffer(needed + 1)
    written = function(str(path), buffer, len(buffer))
    if not written or written >= len(buffer):
        return None
    return Path(buffer.value)


def _short_ascii_alias(model):
    try:
        alias = _windows_short_path(model)
        if alias is None or _ascii_bytes(alias) is None or not os.path.samefile(alias, model):
            return None
        # Some Windows filesystem implementations expand 8.3 names during
        # canonicalization. Such an alias would reintroduce the native bug.
        if _ascii_bytes(alias.resolve(strict=True)) is None:
            return None
        return alias
    except (OSError, ValueError):
        return None


def _candidate_parents(model):
    candidates = [Path(tempfile.gettempdir()), *model.parents]
    system_root = os.environ.get('SystemRoot')
    public = os.environ.get('PUBLIC')
    if system_root:
        candidates.append(Path(system_root) / 'Temp')
    if public:
        candidates.append(Path(public) / 'Documents')
    seen = set()
    for parent in candidates:
        try:
            # Resolve only candidate parents, never the hard-link filename.
            # A junction to a Unicode directory is not a durable ASCII path.
            parent = parent.resolve(strict=True)
        except OSError:
            continue
        key = os.path.normcase(str(parent))
        if key not in seen and _ascii_bytes(parent) is not None:
            seen.add(key)
            yield parent


@contextmanager
def native_model_path(path):
    """Yield C-ABI filename bytes, retaining any owned link until context exit."""
    model = Path(path).resolve(strict=True)
    original_stat = model.stat()
    if not stat.S_ISREG(original_stat.st_mode):
        raise ValueError('Mô hình native phải là một tệp thông thường.')
    if not _on_windows():
        yield os.fsencode(model)
        return
    direct = _ascii_bytes(model)
    if direct is not None:
        yield direct
        return
    short = _short_ascii_alias(model)
    if short is not None:
        yield _ascii_bytes(short)
        return
    for parent in _candidate_parents(model):
        directory = alias = None
        try:
            parent_stat = parent.stat()
            if not stat.S_ISDIR(parent_stat.st_mode) or parent_stat.st_dev != original_stat.st_dev:
                continue
            directory = Path(tempfile.mkdtemp(prefix='voice-studio-native-', dir=parent))
            alias = directory / 'model.gguf'
            if _ascii_bytes(alias) is None:
                raise ValueError('Temporary model path is not ASCII')
            os.link(model, alias)
            if not os.path.samefile(model, alias):
                raise ValueError('Temporary model link does not identify the original file')
        except (OSError, ValueError):
            if alias is not None and alias.exists():
                alias.unlink()
            if directory is not None:
                directory.rmdir()
            continue
        try:
            yield _ascii_bytes(alias)
        finally:
            # Only these two paths were created by this context. Never remove
            # the original model or traverse/delete other files in its folder.
            alias.unlink(missing_ok=True)
            directory.rmdir()
        return
    raise RuntimeError(
        'Không tạo được đường dẫn tương thích cho mô hình native trong thư mục có dấu. '
        'Dùng ổ NTFS và thư mục tool có đường dẫn không dấu hoặc cho phép tạo tệp tạm trên cùng ổ.')
