"""Crash-safe instance locking and verified loopback discovery; no model imports."""
from __future__ import annotations

from contextlib import AbstractContextManager
import errno
from functools import lru_cache
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import time
import urllib.parse
import urllib.request
import uuid
import wave

import psutil

from state_io import write_json_atomic

RECORD_NAME = 'server-instance.json'
_owned = set()
_owned_guard = threading.Lock()


class StudioBusy(RuntimeError):
    """Only an actual held kernel lock, never an arbitrary filesystem error."""


def _canonical(path):
    return os.path.normcase(str(Path(path).expanduser().resolve()))


def make_data_id(path):
    return hashlib.sha256(_canonical(path).encode('utf-8')).hexdigest()


make_root_id = make_data_id


def _local_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urllib.parse.urlsplit(value)
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1'
                or parsed.username or parsed.password or parsed.path not in ('', '/')
                or parsed.query or parsed.fragment or not parsed.port or not 1 <= parsed.port <= 65535):
            return None
        return 'http://127.0.0.1:' + str(parsed.port)
    except ValueError:
        return None


def _read_record(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(32769)
        if not 0 < len(raw) <= 32768:
            return None
        result = json.loads(raw)
        return result if isinstance(result, dict) else None
    except (OSError, ValueError, TypeError, RecursionError):
        return None


def _get_json(url, *, timeout=1):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=timeout) as response:
            raw = response.read(32769)
        if not 0 < len(raw) <= 32768:
            return None
        result = json.loads(raw)
        return result if isinstance(result, dict) else None
    except (OSError, ValueError, TypeError, RecursionError):
        return None


@lru_cache(maxsize=1)
def _windows_api():
    import ctypes
    from ctypes import wintypes

    class Overlapped(ctypes.Structure):
        _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                    ('Offset', wintypes.DWORD), ('OffsetHigh', wintypes.DWORD),
                    ('hEvent', wintypes.HANDLE)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = (wintypes.HANDLE,)
    kernel.ReleaseMutex.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LockFileEx.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(Overlapped))
    kernel.LockFileEx.restype = wintypes.BOOL
    kernel.UnlockFileEx.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.DWORD, ctypes.POINTER(Overlapped))
    kernel.UnlockFileEx.restype = wintypes.BOOL
    kernel.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    kernel.GetDriveTypeW.restype = wintypes.UINT
    return ctypes, kernel, Overlapped


class _KernelLock(AbstractContextManager):
    def __init__(self, data, kind):
        self.data = Path(data).expanduser().resolve()
        self.kind = kind
        self.key = (make_data_id(self.data), kind)
        self.handle = self.mutex = self.overlapped = None
        self.registered = self.file_locked = False
        self.lock_backend = 'file'

    def __enter__(self):
        with _owned_guard:
            if self.key in _owned:
                raise StudioBusy('Voice Studio đã chạy với thư mục dữ liệu này.')
            _owned.add(self.key)
            self.registered = True
        try:
            self.data.mkdir(parents=True, exist_ok=True)
            if os.name == 'nt':
                ctypes, kernel, _ = _windows_api()
                name = 'Global\\VoiceStudio.' + self.kind + '.' + self.key[0]
                self.mutex = kernel.CreateMutexW(None, False, name)
                if not self.mutex:
                    raise ctypes.WinError(ctypes.get_last_error())
                outcome = kernel.WaitForSingleObject(self.mutex, 0)
                if outcome == 258:  # WAIT_TIMEOUT alone proves contention.
                    raise StudioBusy('Voice Studio đã chạy với thư mục dữ liệu này.')
                if outcome not in (0, 128):  # OBJECT_0 or abandoned owner.
                    raise ctypes.WinError(ctypes.get_last_error())
            path = self.data / ('server.lock' if self.kind == 'server' else 'launcher.lock')
            self.handle = path.open('a+b')
            self.handle.seek(0, os.SEEK_END)
            if self.handle.tell() == 0:
                self.handle.write(b'0')
                self.handle.flush()
            self.handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                ctypes, kernel, structure = _windows_api()
                self.overlapped = structure()
                descriptor = msvcrt.get_osfhandle(self.handle.fileno())
                if not kernel.LockFileEx(descriptor, 3, 0, 1, 0, ctypes.byref(self.overlapped)):
                    code = ctypes.get_last_error()
                    if code in (32, 33):
                        raise StudioBusy('Voice Studio đã chạy với thư mục dữ liệu này.')
                    if code not in (1, 50):
                        raise ctypes.WinError(code)
                    drive = str(self.data.anchor)
                    if str(self.data).startswith('\\\\') or kernel.GetDriveTypeW(drive) == 4:
                        raise RuntimeError('Ổ mạng không hỗ trợ khóa dữ liệu. Chép toàn bộ tool sang ổ cục bộ có quyền ghi.')
                    self.lock_backend = 'windows_mutex'  # Local FAT/exFAT fallback.
                else:
                    self.file_locked = True
                    self.lock_backend = 'windows_mutex_and_file'
            else:
                import fcntl
                try:
                    fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    if exc.errno in (errno.EACCES, errno.EAGAIN):
                        raise StudioBusy('Voice Studio đã chạy với thư mục dữ liệu này.') from None
                    raise
                self.file_locked = True
            return self
        except BaseException as exc:
            self.__exit__(None, None, None)
            if isinstance(exc, OSError):
                raise RuntimeError('Không mở/khóa được thư mục dữ liệu. Kiểm tra quyền ghi hoặc chép toàn bộ tool '
                                   'sang ổ cục bộ. Lỗi hệ thống: ' + str(exc)) from None
            raise

    def __exit__(self, *args):
        if self.handle is not None:
            try:
                if os.name == 'nt' and self.file_locked:
                    import msvcrt
                    ctypes, kernel, _ = _windows_api()
                    kernel.UnlockFileEx(msvcrt.get_osfhandle(self.handle.fileno()), 0, 1, 0,
                                         ctypes.byref(self.overlapped))
            finally:
                self.handle.close()
                self.handle = None
        if self.mutex:
            _, kernel, _ = _windows_api()
            kernel.ReleaseMutex(self.mutex)
            kernel.CloseHandle(self.mutex)
            self.mutex = None
        if self.registered:
            with _owned_guard:
                _owned.discard(self.key)
            self.registered = False


class StartupLock(AbstractContextManager):
    def __init__(self, data, timeout=60):
        self.lock = _KernelLock(data, 'launcher')
        self.timeout = timeout

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.lock.__enter__()
                return self
            except StudioBusy:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Một cửa sổ đang khởi động tool. Đợi cửa sổ đó hoàn tất rồi mở lại.') from None
                time.sleep(.1)

    def __exit__(self, *args):
        return self.lock.__exit__(*args)


class StudioInstance(AbstractContextManager):
    def __init__(self, data_dir, root_dir, version, variant, backend, url=None):
        self.data = Path(data_dir).expanduser().resolve()
        self.lock = _KernelLock(self.data, 'server')
        self.identity = {'instance_id': uuid.uuid4().hex, 'pid': os.getpid(),
                         'create_time': psutil.Process().create_time(), 'url': _local_url(url),
                         'data_id': make_data_id(data_dir), 'root_id': make_root_id(root_dir),
                         'version': version, 'variant': variant, 'backend': backend}

    def public_identity(self):
        return dict(self.identity)

    def __enter__(self):
        self.lock.__enter__()
        try:
            write_json_atomic(self.data / RECORD_NAME, self.identity)
        except BaseException:
            self.lock.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *args):
        try:
            path = self.data / RECORD_NAME
            current = _read_record(path)
            if current and current.get('instance_id') == self.identity['instance_id']:
                path.unlink(missing_ok=True)
        finally:
            self.lock.__exit__(*args)


def discover_instance(data, root):
    record = _read_record(Path(data) / RECORD_NAME)
    if (not record or record.get('data_id') != make_data_id(data)
            or record.get('root_id') != make_root_id(root)
            or not isinstance(record.get('instance_id'), str) or len(record['instance_id']) != 32
            or type(record.get('pid')) is not int or record['pid'] <= 0):
        return None
    url = _local_url(record.get('url'))
    if url is None:
        return None
    try:
        process = psutil.Process(record['pid'])
        created = process.create_time()
        if not process.is_running() or created != record.get('create_time'):
            return None
        identity = _get_json(url + '/api/runtime')
        if not identity or any(identity.get(key) != value for key, value in record.items()):
            return None
        if process.create_time() != created or not process.is_running():
            return None
        return {**record, 'url': url}
    except (psutil.Error, OSError, ValueError):
        return None


def _legacy_data_challenge(data, url):
    """Prove old server's data directory without inspecting protected PEB/env.

    The old sample route serves unregistered WAVs by UUID. A short, random PCM
    challenge gets no profile/history entry and is removed in all outcomes.
    """
    ident = uuid.uuid4().hex
    path = Path(data) / 'voices' / (ident + '.wav')
    created = False
    try:
        output = io.BytesIO()
        with wave.open(output, 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(os.urandom(64))
        challenge = output.getvalue()
        with path.open('xb') as stream:
            created = True
            stream.write(challenge)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url + '/api/voices/' + ident + '/sample', timeout=2) as response:
            return response.read(len(challenge) + 1) == challenge
    except (OSError, ValueError):
        return False
    finally:
        if created:
            # Windows may still be closing the FileResponse's read handle.
            for attempt in range(10):
                try:
                    path.unlink(missing_ok=True)
                    break
                except PermissionError:
                    if attempt < 9:
                        time.sleep(.05)
                except OSError:
                    break


def legacy_discover(data, root):
    """Adopt old1.5 only with process plus environment or nonce-data proof."""
    for process in psutil.process_iter(['pid', 'cmdline']):
        try:
            command = process.info.get('cmdline') or []
            if not any(command[i:i+3] == ['-m', 'uvicorn', 'app:app']
                       for i in range(len(command) - 2)):
                continue
            port = int(command[command.index('--port') + 1])
            host = command[command.index('--host') + 1]
            if host != '127.0.0.1' or not 1 <= port <= 65535:
                continue
            needs_challenge = False
            server_cwd = None
            try:
                server_cwd = Path(process.cwd())
                if _canonical(server_cwd) != _canonical(root):
                    continue
            except psutil.AccessDenied:
                needs_challenge = True
            try:
                environment = process.environ()  # Never log process environment.
                variant = environment.get('VOICE_STUDIO_VARIANT', '').lower()
                folder = '.data-hmong' if variant == 'hmong' else '.data'
                actual_data = Path(environment.get('VOICE_STUDIO_DATA_DIR', str(Path(root) / folder)))
                if not actual_data.is_absolute():
                    if server_cwd is None:
                        needs_challenge = True
                        actual_data = None
                    else:
                        actual_data = server_cwd / actual_data
                if actual_data is not None and make_data_id(actual_data) != make_data_id(data):
                    continue
            except psutil.AccessDenied:
                needs_challenge = True
                variant = os.getenv('VOICE_STUDIO_VARIANT', '').lower()
            created = process.create_time()
            url = 'http://127.0.0.1:' + str(port)
            if needs_challenge and (not 8770 <= port < 8790 or not _legacy_data_challenge(data, url)):
                continue
            config = _get_json(url + '/api/config', timeout=5)
            if (not config or config.get('mode') != 'local'
                    or config.get('variant', 'standard') != ('hmong' if variant == 'hmong' else 'standard')
                    or process.create_time() != created or not process.is_running()):
                continue
            backend = config.get('hmong_engine', 'f5_hmong') if variant == 'hmong' else 'standard'
            return {'url': url, 'version': config.get('version', ''), 'backend': backend,
                    'variant': 'hmong' if variant == 'hmong' else 'standard',
                    'pid': process.pid, 'create_time': created, 'instance_id': None,
                    'data_id': make_data_id(data), 'root_id': make_root_id(root), 'legacy': True}
        except (psutil.Error, OSError, ValueError, IndexError):
            continue
    return None
