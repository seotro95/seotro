"""Warm native multilingual adapter, with one isolated model for all voices.

Normal inference is offline. Preparation separately verifies the published GGUF
and installs a pinned audio.cpp CPU/CUDA runtime. A requested device never falls
back to another backend without the user choosing it.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import uuid

BASE = Path(__file__).resolve().parent
MODEL_NAME = 'omnivoice-q8_0.gguf'
MODEL_REPOSITORY = 'audio-cpp/audio.cpp-gguf'
_client = None
_client_lock = threading.RLock()
_verified_models = set()
_verified_libraries = set()


def _backend_name(family):
    if not isinstance(family, str) or family not in {'omnivoice', 'voxcpm2'}:
        raise ValueError('Chọn bộ đọc native OmniVoice hoặc VoxCPM2.')
    return 'voxcpm_native' if family == 'voxcpm2' else 'omnivoice'


def validate_native_performance(value, device, family):
    if not isinstance(value, str) or value not in {'off', 'cuda_perf'}:
        raise ValueError('Chọn chế độ native Tiêu chuẩn hoặc CUDA nhanh.')
    if value == 'cuda_perf' and (family != 'voxcpm2' or device != 'cuda'):
        raise ValueError('CUDA nhanh chỉ dùng với VoxCPM2 native trên NVIDIA CUDA.')
    return value


def _native_root():
    return Path(os.environ.get('VOICE_STUDIO_NATIVE_ROOT', str(BASE.parent / 'runtime-native'))).resolve()


def _runtime_manifest(path, device, family, verify=False):
    """VoxCPM2 cannot run in an old, OmniVoice-only native library."""
    _backend_name(family)
    if family == 'omnivoice':
        return {}
    from native_voxcpm_model import NATIVE_REVISION
    marker = path.parent / 'native-build.json'
    if not marker.is_file():
        marker = path.parent.parent / 'native-build.json'
    try:
        record = json.loads(marker.read_text(encoding='utf-8'))
        families = record.get('families', [record.get('family')])
        revision = record.get('revision') or record.get('source_revision') or record.get('native_revision')
        digest = record.get('sha256', {}).get(path.name)
        if (not isinstance(families, list) or 'voxcpm2' not in families
                or revision != NATIVE_REVISION or record.get('device') != device
                or not isinstance(digest, str) or len(digest) != 64
                or any(char not in '0123456789abcdef' for char in digest)):
            raise ValueError('Wrong native build record')
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Chưa cài đúng thư viện VoxCPM2 native ' + device.upper() + '. Cài bản có hỗ trợ voxcpm2 rồi thử lại.') from exc
    if verify:
        before = path.stat()
        state = (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino, before.st_dev)
        key = (str(path.resolve()), state, digest)
        if key not in _verified_libraries:
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            after = path.stat()
            current = (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino, after.st_dev)
            if actual != digest or current != state:
                raise ValueError('SHA256 thư viện VoxCPM2 native không khớp. Cài lại bộ chạy đã xác minh.')
            _verified_libraries.clear()
            _verified_libraries.add(key)
    return record


def library_path(device='cpu', family='omnivoice'):
    _backend_name(family)
    if device not in {'cpu', 'cuda'}:
        raise ValueError('Chọn CPU hoặc NVIDIA CUDA cho bộ đọc native.')
    folder = _native_root() / device
    names = ['audiocpp.dll'] if os.name == 'nt' else (['libaudiocpp.dylib'] if sys.platform == 'darwin' else ['libaudiocpp.so', 'libaudiocpp.so.0'])
    for root in (folder, folder / 'libs'):
        for name in names:
            path = root / name
            if path.is_file():
                _runtime_manifest(path, device, family)
                return path
    raise ValueError('Chưa cài thư viện native ' + device.upper() + '. Chạy TAI_GIONG_DA_NGON_NGU_NHANH.bat rồi mở lại tool.')


def prepared_model(data, verify=False, family='omnivoice'):
    _backend_name(family)
    if family == 'voxcpm2':
        from native_voxcpm_model import prepared_model as prepared_voxcpm
        return prepared_voxcpm(data, verify=verify)
    data = Path(data).resolve()
    marker = data / 'models/omnivoice.ready'
    record = json.loads(marker.read_text(encoding='utf-8'))
    if (not isinstance(record, dict) or type(record.get('schema')) is not int
            or record.get('schema') != 1 or record.get('backend') != 'omnivoice'
            or record.get('repository') != 'audio-cpp/audio.cpp-gguf'):
        raise ValueError('Bản ghi mô hình OmniVoice không đúng nguồn đã chuẩn bị.')
    folder, filename = record.get('model_dir'), record.get('filename')
    if folder != 'omnivoice' or filename != 'omnivoice-q8_0.gguf':
        raise ValueError('Đường dẫn mô hình OmniVoice không hợp lệ.')
    digest, revision, size = record.get('sha256'), record.get('revision'), record.get('size')
    if (not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)
            or not isinstance(revision, str) or len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision)
            or type(size) is not int or not 4 <= size <= 8 * 1024**3):
        raise ValueError('Bản ghi mô hình OmniVoice thiếu kích thước, phiên bản hoặc SHA256.')
    model = data / 'models' / folder / filename
    if not model.resolve().is_relative_to((data / 'models').resolve()):
        raise ValueError('Đường dẫn mô hình OmniVoice nằm ngoài thư mục dữ liệu.')
    stat = model.stat()
    if stat.st_size != size:
        raise ValueError('Mô hình OmniVoice không đủ dung lượng. Chạy lại bộ tải native.')
    with model.open('rb') as stream:
        if stream.read(4) != b'GGUF':
            raise ValueError('Mô hình OmniVoice không phải GGUF hợp lệ.')
    key = (str(model.resolve()), stat.st_mtime_ns, stat.st_size, stat.st_ino, digest)
    if verify and key not in _verified_models:
        with model.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = model.stat()
        if actual != digest or (after.st_mtime_ns, after.st_size, after.st_ino) != (stat.st_mtime_ns, stat.st_size, stat.st_ino):
            raise ValueError('SHA256 mô hình OmniVoice không khớp. Chạy lại bộ tải native.')
        _verified_models.clear()
        _verified_models.add(key)
    return model, record


def _prepared_for_family(data, verify=False, family='omnivoice'):
    # Keep the original OmniVoice call shape for existing integrations.
    return prepared_model(data, verify=verify, family=family) if family != 'omnivoice' else prepared_model(data, verify=verify)


def is_ready(data, device=None, family='omnivoice'):
    try:
        _prepared_for_family(data, family=family)
        for candidate in (device,) if device is not None else ('cpu', 'cuda'):
            try:
                library_path(candidate, family=family) if family != 'omnivoice' else library_path(candidate)
                return True
            except (OSError, ValueError):
                pass
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return False


def cuda_available(data, family='omnivoice'):
    """Installed CUDA package, not a claim that a GPU has passed inference."""
    return is_ready(data, 'cuda', family=family)


def language_code(language, family='omnivoice'):
    _backend_name(family)
    if family == 'voxcpm2':
        from native_voxcpm_model import language_code as voxcpm_language
        return voxcpm_language(language)
    # The pinned audio.cpp OmniVoice map uses ISO 639-1, with Filipino as fil.
    from language_catalog import LANGUAGES
    if not isinstance(language, str) or language not in LANGUAGES:
        raise ValueError('Ngôn ngữ này chưa được ánh xạ cho bộ đọc native.')
    return {'en-US': 'en', 'en-GB': 'en', 'tl': 'fil', 'ar': 'arb', 'ne': 'npi'}.get(language, language)


def _validate(threads, steps, device, language, reference_text, family='omnivoice'):
    _backend_name(family)
    if type(threads) is not int or not 1 <= threads <= 8:
        raise ValueError('Chọn từ 1 đến 8 luồng cho bộ đọc native.')
    if type(steps) is not int or steps not in ({4, 8, 10} if family == 'voxcpm2' else {8, 16, 32}):
        raise ValueError('Chọn VoxCPM2 4, 8 hoặc 10 bước.' if family == 'voxcpm2' else 'Chọn OmniVoice 8, 16 hoặc 32 bước.')
    if device not in {'cpu', 'cuda'}:
        raise ValueError('Chọn CPU hoặc NVIDIA CUDA cho bộ đọc native.')
    language_code(language, family=family)
    if not isinstance(reference_text, str) or len(reference_text) > 16000:
        raise ValueError('Bản chép lời mẫu giọng không hợp lệ.')


class _BackendClient:
    def __init__(self, library, model, data, threads, device, key, record):
        self.key = key
        self.device = device
        self.family = 'voxcpm2' if record.get('backend') == 'voxcpm_native' else 'omnivoice'
        self.backend = _backend_name(self.family)
        self.native_performance = validate_native_performance(record.get('native_performance', 'off'), device, self.family)
        self.responses = queue.Queue()
        self.process, self.log = None, None
        self.execution = {}
        data.mkdir(parents=True, exist_ok=True)
        self.log = (data / 'international-native-backend.log').open('a', encoding='utf-8')
        env = dict(os.environ)
        for name in ('PYTHONPATH', 'PYTHONHOME'):
            env.pop(name, None)
        env.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', HF_HUB_OFFLINE='1',
                   TRANSFORMERS_OFFLINE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        try:
            arguments = [sys.executable, '-s', '-X', 'utf8', str(BASE / 'native_synthesis.py'), '--serve',
                         '--data-dir', str(data), '--threads', str(threads), '--device', device]
            if self.family != 'omnivoice':
                arguments.extend(['--family', self.family, '--native-performance', self.native_performance])
            self.process = subprocess.Popen(
                arguments,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                text=True, encoding='utf-8', bufsize=1, env=env)
            threading.Thread(target=self._read, daemon=True).start()
            self.execution.update(model_sha256=record['sha256'], model_repository=record['repository'], model_revision=record['revision'])
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                self.responses.put(line)
        finally:
            self.responses.put(None)

    def _response(self):
        try:
            line = self.responses.get(timeout=600)
            if line is None:
                raise ValueError('Bộ đọc native đã dừng. Xem international-native-backend.log trong dữ liệu ứng dụng.')
            result = json.loads(line)
            if not isinstance(result, dict):
                raise ValueError('Bộ đọc native trả về dữ liệu không hợp lệ.')
            return result
        except (queue.Empty, json.JSONDecodeError) as exc:
            raise ValueError('Bộ đọc native không phản hồi hợp lệ; có thể tiếp tục để thử lại.') from exc

    def _execution(self, value):
        if (not isinstance(value, dict) or value.get('backend') != self.backend
                or value.get('device') != self.device
                or (self.family == 'voxcpm2' and (value.get('model_family') != 'voxcpm2'
                    or value.get('native_performance') != getattr(self, 'native_performance', 'off')))):
            raise ValueError('Bộ đọc native không xác nhận đúng thiết bị đã chọn.')
        # Permit only public runtime metadata in the visible speed report.
        for name in ('backend', 'device', 'precision', 'native_runtime_version', 'native_source_revision', 'workers', 'threads', 'omnivoice_steps', 'voxcpm_steps', 'model_language', 'model_family', 'native_performance'):
            if name in value:
                self.execution[name] = value[name]

    def synthesize(self, text, reference, output, steps, language, reference_text):
        ident = uuid.uuid4().hex
        request = {'id': ident, 'text': text, 'reference_wav': str(reference), 'output': str(output),
                   'steps': steps, 'language': language, 'reference_text': reference_text}
        try:
            self.process.stdin.write(json.dumps(request, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
            response = self._response()
            if response.get('id') != ident:
                raise ValueError('Phản hồi bộ đọc native không khớp tác vụ.')
            if not response.get('ok'):
                raise ValueError('Không tạo được lời đọc native: ' + str(response.get('error', 'lỗi chưa xác định')))
            if response.get('output') != str(output):
                raise ValueError('Phản hồi bộ đọc native không khớp tệp đầu ra.')
            self._execution(response.get('execution'))
            return dict(self.execution)
        except (OSError, ValueError):
            self.close()
            raise

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout):
                if stream is not None:
                    stream.close()
        if self.log is not None:
            self.log.close()


def close_backends():
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None


def execution_info():
    with _client_lock:
        return dict(_client.execution) if _client is not None and _client.process.poll() is None else {}


def create_synthesizer(reference_audio, data, threads=4, steps=None, device='cpu', language='fr', reference_text='', reference_language=None, family='omnivoice', native_performance='off'):
    data = Path(data).resolve()
    reference = Path(reference_audio).resolve()
    if not reference.is_file():
        raise ValueError('Không tìm thấy mẫu giọng đã chọn.')
    threads = max(1, min(8, int(threads)))
    if steps is None:
        steps = 8 if family == 'voxcpm2' else 16
    _validate(threads, steps, device, language, reference_text, family=family)
    validate_native_performance(native_performance, device, family)
    if reference_language is not None and family == 'omnivoice':
        language_code(reference_language)
    code = language
    library = library_path(device, family=family) if family != 'omnivoice' else library_path(device)
    # Readiness is cheap; the first actual use verifies full SHA256 once.
    model, _ = _prepared_for_family(data, family=family)
    transcript_state, resolved_transcript = None, reference_text

    def synthesize(text, output):
        global _client
        nonlocal transcript_state, resolved_transcript
        with _client_lock:
            current_model, record = _prepared_for_family(data, verify=True, family=family)
            _runtime_manifest(library, device, family, verify=True)
            stat, library_stat = current_model.stat(), library.stat()
            key = (family, str(current_model), stat.st_mtime_ns, stat.st_size, record['sha256'], str(library),
                   library_stat.st_mtime_ns, library_stat.st_size, native_performance, threads, device)
            if family == 'omnivoice' and not reference_text.strip():
                # Some installed reference packs omit transcripts. Derive one
                # locally once; never send the user's sample to a service or
                # silently replace it with an unrelated preset speaker.
                reference_stat = reference.stat()
                state = (reference_stat.st_mtime_ns, reference_stat.st_size, reference_stat.st_ino)
                if transcript_state != state:
                    from native_transcript import reference_transcript
                    resolved_transcript = reference_transcript(reference, data, reference_language or language)
                    if not isinstance(resolved_transcript, str) or not resolved_transcript.strip():
                        raise ValueError('Chưa nhận được bản chép lời mẫu giọng hợp lệ. Bổ sung lời mẫu rồi thử lại.')
                    transcript_state = state
            if _client is None or _client.key != key or _client.process.poll() is not None:
                close_backends()
                runtime_record = {**record, 'native_performance': native_performance} if family == 'voxcpm2' else record
                _client = _BackendClient(library, current_model, data, threads, device, key, runtime_record)
            try:
                return _client.synthesize(text, reference, Path(output).resolve(), steps, code, resolved_transcript)
            except BaseException:
                close_backends()
                raise
    return synthesize


atexit.register(close_backends)
