"""Offline Qwen preset/clone inference in a separate, pinned Python runtime.

Importing this adapter never imports Torch, Transformers or Qwen into Nano/Turbo.
This distribution explicitly uses CPU FP32 and SDPA; GPU speed is not implied.
"""
from __future__ import annotations

import argparse
import atexit
from collections import OrderedDict
import contextlib
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import uuid


BASE = Path(__file__).resolve().parent
MODELS = {
    'qwen': ('Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice', 'qwen-customvoice'),
    'qwen_clone': ('Qwen/Qwen3-TTS-12Hz-0.6B-Base', 'qwen-base'),
}
RUNTIME_PACKAGES = {'torch': '2.8.0+cpu', 'qwen-tts': '0.1.1',
                    'transformers': '4.57.3', 'huggingface-hub': '0.36.2', 'tokenizers': '0.22.2'}
LANGUAGES = {'en-US': 'English', 'en-GB': 'English', 'ja': 'Japanese', 'ko': 'Korean',
             'zh': 'Chinese', 'fr': 'French', 'de': 'German', 'es': 'Spanish',
             'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian'}
SPEAKERS = frozenset({'Ryan', 'Aiden', 'Vivian', 'Serena', 'Uncle_Fu',
                      'Dylan', 'Eric', 'Sohee', 'Ono_Anna'})
_SHA = re.compile('[0-9a-f]{64}')
_client = None
_lock = threading.RLock()
_runtime_cache = None
_verified_models = set()


def runtime_python():
    override = os.environ.get('VOICE_STUDIO_QWEN_PYTHON')
    if override:
        return Path(override).absolute()  # resolving a venv symlink loses its environment
    root = BASE.parent / 'runtime-qwen'
    return root / ('python.exe' if os.name == 'nt' else 'bin/python')


def _package_roots(executable):
    root = executable.parent if executable.name.lower().endswith('.exe') else executable.parent.parent
    return [root / 'Lib/site-packages', *sorted((root / 'lib').glob('python*/site-packages'))]


def runtime_ready():
    """Check the isolated installation's metadata without importing its modules."""
    global _runtime_cache
    executable = runtime_python()
    if not executable.is_file():
        return False
    now = time.monotonic()
    if _runtime_cache and _runtime_cache[0] == str(executable) and now - _runtime_cache[1] < 5:
        return _runtime_cache[2]
    versions = {}
    try:
        for distribution in importlib.metadata.distributions(path=[str(p) for p in _package_roots(executable)]):
            name = re.sub('[-_.]+', '-', distribution.metadata.get('Name', '').lower())
            if name in RUNTIME_PACKAGES:
                if name in versions:
                    raise ValueError('Trùng bản ghi thư viện Qwen riêng.')
                versions[name] = distribution.version
        ready = all(versions.get(name) == version for name, version in RUNTIME_PACKAGES.items())
    except (OSError, ValueError, UnicodeError):
        ready = False
    _runtime_cache = (str(executable), now, ready)
    return ready


def _safe_name(value):
    return (isinstance(value, str) and bool(value) and len(value) <= 240
            and '\\' not in value and ':' not in value and not any(ord(char) < 32 for char in value)
            and not PurePosixPath(value).is_absolute()
            and all(part not in {'', '.', '..'} for part in value.split('/')))


def prepared_model(data, engine='qwen', verify=False):
    if engine not in MODELS:
        raise ValueError('Chọn Qwen có sẵn hoặc Qwen nhân bản.')
    models = Path(data).resolve() / 'models'
    marker = models / (engine + '.ready')
    try:
        if marker.stat().st_size > 128 * 1024:
            raise ValueError('Bản ghi mô hình Qwen quá lớn.')
        payload = marker.read_bytes()
        record = json.loads(payload)
        repository, folder = MODELS[engine]
        if (not isinstance(record, dict) or type(record.get('schema')) is not int or record.get('schema') != 1
                or record.get('backend') != 'qwen-isolated' or record.get('engine') != engine
                or record.get('repository') != repository or record.get('model_dir') != folder
                or not isinstance(record.get('revision'), str)
                or not re.fullmatch('[0-9a-f]{40}', record['revision'])):
            raise ValueError('Bản ghi mô hình Qwen không đúng nguồn đã chuẩn bị.')
        model = models / folder
        if model.is_symlink() or not model.resolve().is_relative_to(models.resolve()):
            raise ValueError('Đường dẫn mô hình Qwen không hợp lệ.')
        entries = record.get('files')
        if not isinstance(entries, list) or not 8 <= len(entries) <= 256:
            raise ValueError('Mô hình Qwen thiếu danh sách tệp đầy đủ.')
        seen, states, total = set(), [], 0
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError('Bản ghi tệp Qwen không hợp lệ.')
            name, size, digest = (item.get(key) for key in ('name', 'size', 'sha256'))
            if (not _safe_name(name) or name.casefold() in seen or type(size) is not int
                    or not 0 < size <= 8 * 1024**3 or not isinstance(digest, str) or not _SHA.fullmatch(digest)):
                raise ValueError('Bản ghi tệp Qwen thiếu đường dẫn, kích thước hoặc SHA256 hợp lệ.')
            seen.add(name.casefold())
            path = model.joinpath(*PurePosixPath(name).parts)
            if path.is_symlink() or not path.resolve().is_relative_to(model.resolve()) or not path.is_file():
                raise ValueError('Thiếu tệp trong mô hình Qwen đã chuẩn bị.')
            state = path.stat()
            if state.st_size != size:
                raise ValueError('Tệp mô hình Qwen thiếu hoặc sai dung lượng.')
            states.append((name, state.st_size, state.st_mtime_ns, state.st_ctime_ns, state.st_ino, digest))
            total += size
        required = {'config.json', 'generation_config.json', 'tokenizer_config.json',
                    'speech_tokenizer/config.json', 'speech_tokenizer/preprocessor_config.json',
                    'speech_tokenizer/model.safetensors'}
        if (total > 16 * 1024**3 or not required <= seen
                or not ('tokenizer.json' in seen or {'vocab.json', 'merges.txt'} <= seen)):
            raise ValueError('Mô hình Qwen thiếu cấu hình hoặc bộ mã hóa âm thanh/văn bản.')
        if 'model.safetensors' not in seen:
            if 'model.safetensors.index.json' not in seen:
                raise ValueError('Mô hình Qwen thiếu trọng số safetensors.')
            index = json.loads((model / 'model.safetensors.index.json').read_text(encoding='utf-8'))
            shards = index.get('weight_map', {})
            if (not isinstance(shards, dict) or not shards
                    or any(not _safe_name(name) or name.casefold() not in seen for name in shards.values())):
                raise ValueError('Mô hình Qwen thiếu một phần trọng số safetensors.')
        identity = (str(model), hashlib.sha256(payload).hexdigest(), tuple(states))
        if verify and identity not in _verified_models:
            for item in entries:
                path = model.joinpath(*PurePosixPath(item['name']).parts)
                with path.open('rb') as source:
                    actual = hashlib.file_digest(source, 'sha256').hexdigest()
                if actual != item['sha256']:
                    raise ValueError('SHA256 mô hình Qwen không khớp; dùng lại gói đầy đủ đã xác minh.')
            current = [(name, (model / name).stat()) for name, *_ in states]
            if any((state.st_size, state.st_mtime_ns, state.st_ctime_ns, state.st_ino) != old[1:5]
                   for (_, state), old in zip(current, states)):
                raise ValueError('Mô hình Qwen thay đổi trong lúc xác minh.')
            _verified_models.add(identity)
        return model, record
    except (FileNotFoundError, json.JSONDecodeError, UnicodeError, KeyError, TypeError):
        raise ValueError('Thiếu hoặc hỏng mô hình Qwen. Dùng gói đầy đủ có model Qwen đã chuẩn bị.') from None


def is_ready(data, engine='qwen'):
    try:
        return runtime_ready() and bool(prepared_model(data, engine)[0])
    except (OSError, ValueError, AttributeError):
        return False


def _settings(engine, language, speaker, reference, reference_text, threads, quality, device):
    if engine not in MODELS or language not in LANGUAGES:
        raise ValueError('Giọng hoặc ngôn ngữ Qwen chưa được hỗ trợ.')
    if device != 'cpu':
        raise ValueError('Bộ Qwen đi kèm chạy CPU FP32; chưa có bộ Qwen CUDA đã kiểm thử.')
    if type(threads) is not int or not 1 <= threads <= 8 or quality not in {'auto', 'standard', 'fast'}:
        raise ValueError('Cấu hình tạo giọng Qwen không hợp lệ.')
    if not isinstance(reference_text, str) or len(reference_text) > 8000:
        raise ValueError('Lời mẫu Qwen không hợp lệ.')
    if engine == 'qwen' and speaker not in SPEAKERS:
        raise ValueError('Chọn một trong chín giọng Qwen có sẵn.')
    if engine == 'qwen_clone' and (reference is None or not Path(reference).is_file()):
        raise ValueError('Không tìm thấy mẫu giọng Qwen nhân bản.')


def _environment(data, threads):
    env = dict(os.environ)
    for name in ('PYTHONHOME', 'PYTHONPATH', 'TRANSFORMERS_CACHE'):
        env.pop(name, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', VOICE_STUDIO_DATA_DIR=str(data),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
               HF_HUB_DISABLE_XET='1', DO_NOT_TRACK='1', CUDA_VISIBLE_DEVICES='',
               HF_HOME=str(data / 'models/cache'), TOKENIZERS_PARALLELISM='false',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS=str(threads), OMP_NUM_THREADS=str(threads))
    return env


class _BackendClient:
    def __init__(self, data, engine, threads, key):
        if not is_ready(data, engine):
            raise ValueError('Thiếu bộ chạy hoặc model Qwen riêng. Dùng gói đầy đủ có runtime-qwen.')
        self.key, self.engine = key, engine
        self.responses, self.execution = queue.Queue(), {}
        self.process = self.log = None
        data.mkdir(parents=True, exist_ok=True)
        try:
            self.log = (data / 'qwen-backend.log').open('a', encoding='utf-8')
            self.process = subprocess.Popen(
                [str(runtime_python()), '-s', '-X', 'utf8', str(Path(__file__).resolve()), '--serve',
                 '--data-dir', str(data), '--engine', engine, '--threads', str(threads)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                text=True, encoding='utf-8', bufsize=1, env=_environment(data, threads))
            threading.Thread(target=self._read, daemon=True).start()
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                self.responses.put(line)
        finally:
            self.responses.put(None)

    def synthesize(self, text, output, **options):
        request = {'id': uuid.uuid4().hex, 'text': text, 'output': str(output), **options}
        try:
            self.process.stdin.write(json.dumps(request, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
            line = self.responses.get(timeout=1800)
            if line is None:
                raise ValueError('Bộ Qwen riêng đã dừng. Xem qwen-backend.log trong dữ liệu ứng dụng.')
            response = json.loads(line)
            if (not isinstance(response, dict) or response.get('id') != request['id']
                    or response.get('output') != str(output) or response.get('ok') is not True):
                raise ValueError('Bộ Qwen không hoàn tất đúng tác vụ. Xem qwen-backend.log.')
            execution = response.get('execution')
            if (not isinstance(execution, dict) or execution.get('backend') != 'qwen_isolated'
                    or execution.get('engine') != self.engine or execution.get('device') != 'cpu'
                    or execution.get('precision') != 'fp32'):
                raise ValueError('Bộ Qwen không xác nhận đúng CPU FP32 đã chọn.')
            self.execution = dict(execution)
            return dict(execution)
        except (OSError, ValueError, queue.Empty):
            self.close()
            raise

    def close(self):
        # Shared shutdown semantics let the child run its model finalizers.
        from fast_multilingual import _BackendClient as NativeClient
        NativeClient.close(self)


def close_backends():
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None


def execution_info():
    with _lock:
        return dict(_client.execution) if _client is not None and _client.process.poll() is None else {}


def create_synthesizer(data, engine='qwen', language='en-US', speaker=None,
                       reference_audio=None, reference_text='', threads=4,
                       quality='standard', device='cpu'):
    data = Path(data).resolve()
    reference = Path(reference_audio).resolve() if reference_audio is not None else None
    _settings(engine, language, speaker, reference, reference_text, threads, quality, device)
    if not is_ready(data, engine):
        raise ValueError('Thiếu bộ chạy hoặc model Qwen riêng. Dùng gói đầy đủ có runtime-qwen.')
    _, marker = prepared_model(data, engine)
    model_key = hashlib.sha256(json.dumps(marker, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    key = (str(runtime_python()), str(data), engine, device, threads, model_key)

    def synthesize(text, output):
        global _client
        with _lock:
            if _client is None or _client.key != key or _client.process.poll() is not None:
                close_backends()
                _client = _BackendClient(data, engine, threads, key)
            return _client.synthesize(text, Path(output).resolve(), language=language,
                                      speaker=speaker, reference_wav=str(reference) if reference else None,
                                      reference_text=reference_text, quality=quality)
    return synthesize


class _Session:
    def __init__(self, data, engine, threads):
        for package, expected in RUNTIME_PACKAGES.items():
            if importlib.metadata.version(package) != expected:
                raise ValueError('Bộ Qwen riêng không đúng phiên bản đã chuẩn bị: ' + package)
        import torch
        from qwen_tts import Qwen3TTSModel
        model_dir, record = prepared_model(data, engine, verify=True)
        torch.set_num_threads(threads)
        self.torch, self.engine, self.threads = torch, engine, threads
        self.model = Qwen3TTSModel.from_pretrained(str(model_dir), device_map='cpu', dtype=torch.float32,
                                                  attn_implementation='sdpa', local_files_only=True)
        self.prompts = OrderedDict()
        self.info = {'backend': 'qwen_isolated', 'engine': engine, 'device': 'cpu',
                     'precision': 'fp32', 'attention': 'sdpa', 'threads': threads,
                     'model_repository': record['repository'], 'model_revision': record['revision'],
                     'gpu_inference_tested': False}

    def _clone_prompt(self, reference, text):
        import numpy as np
        import soundfile as sf
        reference = Path(reference).resolve()
        before = reference.stat()
        if before.st_size > 64 * 1024**2:
            raise ValueError('Mẫu Qwen quá lớn.')
        key = (str(reference), before.st_size, before.st_mtime_ns, before.st_ctime_ns,
               before.st_ino, before.st_dev, text)
        if key in self.prompts:
            self.prompts.move_to_end(key)
            return self.prompts[key]
        audio, rate = sf.read(reference, dtype='float32', always_2d=True)
        if (audio.ndim != 2 or audio.shape[1] not in {1, 2} or not 8000 <= rate <= 192000
                or not 3 <= len(audio) / rate <= 30 or not np.isfinite(audio).all()
                or np.max(np.abs(audio)) <= 1e-5):
            raise ValueError('Mẫu Qwen cần lời đọc hợp lệ dài từ 3 đến 30 giây.')
        with self.torch.inference_mode():
            prompt = self.model.create_voice_clone_prompt(ref_audio=str(reference), ref_text=text or None,
                                                         x_vector_only_mode=not bool(text))
        after = reference.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino):
            raise ValueError('Mẫu Qwen thay đổi trong lúc chuẩn bị.')
        while len(self.prompts) >= 8:
            self.prompts.popitem(last=False)
        self.prompts[key] = prompt
        return prompt

    def synthesize(self, request):
        import numpy as np
        import soundfile as sf
        text, language = request.get('text'), request.get('language')
        reference = request.get('reference_wav')
        reference_text = request.get('reference_text', '')
        quality = request.get('quality', 'standard')
        _settings(self.engine, language, request.get('speaker'), reference, reference_text,
                  self.threads, quality, 'cpu')
        if not isinstance(text, str) or not text.strip() or len(text) > 16000:
            raise ValueError('Lời đọc Qwen không hợp lệ hoặc quá dài.')
        options = {'text': text, 'language': LANGUAGES[language], 'max_new_tokens': 2048}
        if quality == 'fast':
            options.update(do_sample=False, subtalker_dosample=False)
        with self.torch.inference_mode():
            if self.engine == 'qwen_clone':
                prompt = self._clone_prompt(reference, reference_text.strip())
                samples, rate = self.model.generate_voice_clone(**options, voice_clone_prompt=prompt)
            else:
                samples, rate = self.model.generate_custom_voice(**options, speaker=request['speaker'])
        audio = np.asarray(samples[0], dtype=np.float32).squeeze()
        if (audio.ndim != 1 or not audio.size or not 8000 <= rate <= 192000
                or not np.isfinite(audio).all() or np.max(np.abs(audio)) <= 1e-5):
            raise ValueError('Bộ Qwen không tạo được lời đọc hợp lệ.')
        if rate != 24000:
            import soxr
            audio = np.asarray(soxr.resample(audio, rate, 24000, quality='HQ'), dtype=np.float32)
        output = Path(request['output']).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.stem + '.' + uuid.uuid4().hex + '.tmp.wav')
        try:
            sf.write(str(temporary), audio, 24000, subtype='PCM_16')
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
        return dict(self.info)

    def close(self):
        self.prompts.clear()
        self.model = None
        gc.collect()


def serve(data, engine, threads, source=None, protocol=None, errors=None):
    source, protocol, errors = source or sys.stdin, protocol or sys.stdout, errors or sys.stderr
    data = Path(data).resolve()
    session = None
    try:
        for line in source:
            ident, output = None, None
            try:
                if len(line) > 1024**2:
                    raise ValueError('Yêu cầu Qwen quá lớn.')
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError('Yêu cầu Qwen không hợp lệ.')
                ident = request.get('id')
                if not isinstance(ident, str) or not re.fullmatch('[0-9a-f]{32}', ident):
                    raise ValueError('Mã tác vụ Qwen không hợp lệ.')
                output = Path(request['output']).resolve()
                if not output.is_relative_to(data):
                    raise ValueError('Tệp kết quả Qwen phải nằm trong dữ liệu ứng dụng.')
                with contextlib.redirect_stdout(errors):
                    if session is None:
                        session = _Session(data, engine, threads)
                    execution = session.synthesize(request)
                response = {'ok': True, 'id': ident, 'output': str(output), 'execution': execution}
            except Exception:
                traceback.print_exc(file=errors)
                if session is not None:
                    session.close()
                    session = None
                response = {'ok': False, 'id': ident, 'output': str(output) if output else None}
            protocol.write(json.dumps(response, ensure_ascii=False) + '\n')
            protocol.flush()
    finally:
        if session is not None:
            session.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--engine', choices=tuple(MODELS), required=True)
    parser.add_argument('--threads', type=int, choices=range(1, 9), default=4)
    args = parser.parse_args(argv)
    serve(args.data_dir, args.engine, args.threads)


atexit.register(close_backends)

if __name__ == '__main__':
    main()
