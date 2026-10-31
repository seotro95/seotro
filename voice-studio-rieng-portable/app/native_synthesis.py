"""Small ctypes binding and private stdio server for audio.cpp's C ABI.

No network access, Torch imports, HTTP server or per-segment model reloads.
The child owns every native handle and releases it before changing devices.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
import contextlib
import ctypes as C
import json
import math
import os
from pathlib import Path
import sys
import traceback
import uuid

from fast_multilingual import library_path, prepared_model, _validate, language_code, _runtime_manifest, validate_native_performance
from native_paths import native_model_path


_REFERENCE_CACHE_MAX_ENTRIES = 8
_REFERENCE_CACHE_MAX_BYTES = 16 * 1024**2


def _reference_key(path, stat):
    return (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns,
            stat.st_ino, stat.st_dev)


class ModelConfig(C.Structure):
    _fields_ = [('family_hint', C.c_char_p), ('config_id', C.c_char_p),
                ('weight_id', C.c_char_p), ('model_spec_override', C.c_char_p)]


class BackendConfig(C.Structure):
    _fields_ = [('backend', C.c_char_p), ('device', C.c_int), ('threads', C.c_int)]


def _bind(lib):
    ptr = C.c_void_p
    pp = C.POINTER(ptr)
    signatures = {
        'audiocpp_abi_version': ([], C.c_uint32),
        'audiocpp_last_error': ([], C.c_char_p),
        'audiocpp_build_version': ([], C.c_char_p),
        'audiocpp_options_create': ([], ptr),
        'audiocpp_options_set': ([ptr, C.c_char_p, C.c_char_p], C.c_int),
        'audiocpp_options_free': ([ptr], None),
        'audiocpp_registry_create': ([C.c_char_p, pp], C.c_int),
        'audiocpp_registry_free': ([ptr], None),
        'audiocpp_model_load': ([ptr, C.c_char_p, C.POINTER(ModelConfig), ptr, pp], C.c_int),
        'audiocpp_model_free': ([ptr], None),
        'audiocpp_session_create': ([ptr, C.c_char_p, C.c_char_p, C.POINTER(BackendConfig), ptr, pp], C.c_int),
        'audiocpp_session_free': ([ptr], None),
        'audiocpp_request_create': ([], ptr),
        'audiocpp_request_free': ([ptr], None),
        'audiocpp_request_set_text': ([ptr, C.c_char_p, C.c_char_p], C.c_int),
        'audiocpp_request_set_voice_audio': ([ptr, C.POINTER(C.c_float), C.c_size_t, C.c_int, C.c_int], C.c_int),
        'audiocpp_request_set_option': ([ptr, C.c_char_p, C.c_char_p], C.c_int),
        'audiocpp_session_run': ([ptr, ptr, pp], C.c_int),
        'audiocpp_result_audio': ([ptr, C.POINTER(C.POINTER(C.c_float)), C.POINTER(C.c_size_t),
                                  C.POINTER(C.c_int), C.POINTER(C.c_int)], C.c_int),
        'audiocpp_result_free': ([ptr], None),
    }
    for name, (args, result) in signatures.items():
        function = getattr(lib, name)
        function.argtypes, function.restype = args, result
    return lib


class NativeSession:
    def __init__(self, data, threads=4, device='cpu', family='omnivoice', native_performance='off'):
        _validate(threads, 8 if family == 'voxcpm2' else 16, device, 'fr', '', family=family)
        validate_native_performance(native_performance, device, family)
        self.data = Path(data).resolve()
        self.threads, self.device = threads, device
        self.family = family
        self.native_performance = native_performance
        self.registry, self.model, self.session = C.c_void_p(), C.c_void_p(), C.c_void_p()
        self._dll_directory = None
        self._model_path_stack = contextlib.ExitStack()
        self.lib = None
        self._reference_cache = OrderedDict()
        self._reference_cache_bytes = 0
        path = library_path(device, family=family) if family != 'omnivoice' else library_path(device)
        if not path.is_file():
            raise ValueError('Chưa cài bộ native '+device.upper()+'.')
        if family == 'voxcpm2':
            from native_voxcpm_model import prepared_model as prepared_voxcpm
            model, provenance = prepared_voxcpm(self.data, verify=True)
            _runtime_manifest(path, device, family, verify=True)
        else:
            model, provenance = prepared_model(self.data, verify=True)
        try:
            if os.name == 'nt':
                self._dll_directory = os.add_dll_directory(str(path.parent))
            self.lib = _bind(C.CDLL(str(path)))
            version = self.lib.audiocpp_abi_version()
            if version >> 16 != 0 or (version >> 8) & 255 < 2:
                raise ValueError('Bộ native dùng C ABI không tương thích; cần audio.cpp C ABI 0.2 trở lên.')
            self._check(self.lib.audiocpp_registry_create(None, C.byref(self.registry)))
            config = ModelConfig(family.encode('ascii'), None, None, None)
            native_filename = self._model_path_stack.enter_context(native_model_path(model))
            self._check(self.lib.audiocpp_model_load(self.registry, native_filename,
                                                    C.byref(config), None, C.byref(self.model)))
            options = self.lib.audiocpp_options_create()
            if not options:
                raise MemoryError('Không cấp phát được tùy chọn native.')
            try:
                # Keep graphs and conservative GGUF weight types as authored.
                # Runtime tokenizer INT8 has known audible quality failures.
                session_options = ({'voxcpm2.mem_saver': 'false',
                                    'voxcpm2.prompt_cache_slots': '4',
                                    'voxcpm2.perf_mode': native_performance} if family == 'voxcpm2'
                                   else {'omnivoice.mem_saver': 'false'})
                for name, value in session_options.items():
                    self._check(self.lib.audiocpp_options_set(options, name.encode('ascii'), value.encode('ascii')))
                backend = BackendConfig(device.encode('ascii'), 0, threads)
                self._check(self.lib.audiocpp_session_create(self.model, b'tts', b'offline',
                                                            C.byref(backend), options, C.byref(self.session)))
            finally:
                self.lib.audiocpp_options_free(options)
            name = 'voxcpm_native' if family == 'voxcpm2' else 'omnivoice'
            self.info = {'international_backend': name, 'backend': name,
                         'device': device, 'precision': 'q8_0', 'workers': 1,
                         'threads': threads, 'model': 'VoxCPM2-GGUF' if family == 'voxcpm2' else 'OmniVoice-GGUF',
                         'native_runtime_version': self.lib.audiocpp_build_version().decode('utf-8', 'replace')}
            if family == 'voxcpm2':
                self.info['model_family'] = family
                self.info['native_performance'] = native_performance
            build_marker = path.parent/'native-build.json'
            if not build_marker.is_file():
                build_marker = path.parent.parent/'native-build.json'
            if build_marker.is_file():
                build = json.loads(build_marker.read_text(encoding='utf-8'))
                revision = build.get('source_revision') or build.get('native_revision') or build.get('revision')
                if isinstance(revision, str) and len(revision) == 40 and all(c in '0123456789abcdef' for c in revision):
                    self.info['native_source_revision'] = revision
        except BaseException:
            self.close()
            raise

    def _check(self, status):
        if status:
            message = self.lib.audiocpp_last_error().decode('utf-8', 'replace')
            raise RuntimeError('audio.cpp '+self.device.upper()+': '+message)

    def _reference_audio(self, reference):
        """Retain exact validated PCM between sentences, never encoded voice data."""
        import numpy as np
        import soundfile as sf

        reference = Path(reference).resolve()
        before = reference.stat()
        key = _reference_key(reference, before)
        # Lazy initialization also permits lightweight binding tests that do not
        # load a native model. The stdio worker invokes one request at a time.
        if not hasattr(self, '_reference_cache'):
            self._reference_cache = OrderedDict()
            self._reference_cache_bytes = 0
        cache = self._reference_cache
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        # Changed or replaced recordings cannot retain an older cached speaker.
        for previous in tuple(cache):
            if previous[0] == str(reference):
                self._reference_cache_bytes -= cache.pop(previous)[0].nbytes
        if before.st_size > 64 * 1024**2:
            raise ValueError('Mẫu giọng native phải là âm thanh hợp lệ dài tối đa 30 giây.')
        details = sf.info(str(reference))
        if (details.channels not in {1, 2} or not 8000 <= details.samplerate <= 192000
                or not 0 < details.duration <= 30):
            raise ValueError('Mẫu giọng native phải là âm thanh hợp lệ dài tối đa 30 giây.')
        samples, rate = sf.read(str(reference), dtype='float32', always_2d=True)
        if (samples.ndim != 2 or samples.shape != (details.frames, details.channels)
                or rate != details.samplerate or not samples.size
                or not np.isfinite(samples).all()):
            raise ValueError('Mẫu giọng native không có tiếng hợp lệ.')
        # Match the CLI's mono route without resampling or changing amplitudes.
        samples = np.ascontiguousarray(samples.mean(axis=1), dtype=np.float32)
        if np.max(np.abs(samples)) <= 1e-5:
            raise ValueError('Mẫu giọng native không có tiếng hợp lệ.')
        if _reference_key(reference, reference.stat()) != key:
            raise ValueError('Mẫu giọng native đã thay đổi trong khi đọc; hãy thử lại.')
        # A valid high-rate recording may exceed the budget. It can still be
        # used for this request without retaining it in the process afterward.
        if samples.nbytes <= _REFERENCE_CACHE_MAX_BYTES and _REFERENCE_CACHE_MAX_ENTRIES > 0:
            while cache and (len(cache) >= _REFERENCE_CACHE_MAX_ENTRIES
                             or self._reference_cache_bytes + samples.nbytes > _REFERENCE_CACHE_MAX_BYTES):
                _, (old_samples, _) = cache.popitem(last=False)
                self._reference_cache_bytes -= old_samples.nbytes
            samples.setflags(write=False)
            cache[key] = (samples, rate)
            self._reference_cache_bytes += samples.nbytes
        return samples, rate

    def synthesize(self, text, reference, output, *, steps=None, language='fr', reference_text=''):
        family = getattr(self, 'family', 'omnivoice')
        if steps is None:
            steps = 8 if family == 'voxcpm2' else 16
        _validate(self.threads, steps, self.device, language, reference_text, family=family)
        if not isinstance(text, str) or not text.strip() or len(text) > 16000:
            raise ValueError('Lời đọc native không hợp lệ hoặc quá dài.')
        if family == 'omnivoice' and not reference_text.strip():
            raise ValueError('OmniVoice cần bản chép lời chính xác của tệp mẫu giọng.')
        import numpy as np
        import soundfile as sf
        samples, rate = self._reference_audio(reference)
        request, result = self.lib.audiocpp_request_create(), C.c_void_p()
        if not request:
            raise MemoryError('Không cấp phát được tác vụ native.')
        try:
            self._check(self.lib.audiocpp_request_set_text(request, text.encode('utf-8'), language_code(language, family=family).encode('utf-8')))
            self._check(self.lib.audiocpp_request_set_voice_audio(
                request, samples.ctypes.data_as(C.POINTER(C.c_float)), len(samples), rate, 1))
            request_options = {'num_inference_steps': str(steps), 'guidance_scale': '2.0'}
            if family == 'omnivoice':
                request_options['reference_text'] = reference_text
            for key, value in request_options.items():
                self._check(self.lib.audiocpp_request_set_option(request, key.encode('ascii'), value.encode('utf-8')))
            self._check(self.lib.audiocpp_session_run(self.session, request, C.byref(result)))
            native_samples = C.POINTER(C.c_float)()
            frames, native_rate, channels = C.c_size_t(), C.c_int(), C.c_int()
            self._check(self.lib.audiocpp_result_audio(result, C.byref(native_samples), C.byref(frames),
                                                      C.byref(native_rate), C.byref(channels)))
            if (not native_samples or channels.value not in {1, 2} or not 8000 <= native_rate.value <= 192000
                    or not 0 < frames.value <= native_rate.value*600):
                raise ValueError('Bộ native trả về âm thanh không hợp lệ.')
            audio = np.ctypeslib.as_array(native_samples, shape=(frames.value*channels.value,)).copy()
            if channels.value > 1:
                audio = audio.reshape(-1, channels.value).mean(axis=1)
            if not np.isfinite(audio).all() or np.max(np.abs(audio)) <= 1e-5:
                raise ValueError('Bộ native không tạo được tiếng hợp lệ.')
            if native_rate.value != 24000:
                if family == 'voxcpm2':
                    import soxr
                    audio = np.asarray(soxr.resample(audio, native_rate.value, 24000, quality='HQ'), dtype=np.float32)
                else:
                    from scipy.signal import resample_poly
                    divisor = math.gcd(native_rate.value, 24000)
                    audio = resample_poly(audio, 24000//divisor, native_rate.value//divisor).astype(np.float32)
            if not audio.size or not np.isfinite(audio).all() or np.max(np.abs(audio)) <= 1e-5:
                raise ValueError('Bộ native không tạo được tiếng hợp lệ sau khi chuyển tần số.')
            output = Path(output).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(output.stem+'.'+uuid.uuid4().hex+'.tmp.wav')
            try:
                sf.write(str(temporary), audio, 24000, subtype='PCM_16')
                temporary.replace(output)
            finally:
                temporary.unlink(missing_ok=True)
            return {**self.info, 'voxcpm_steps' if family == 'voxcpm2' else 'omnivoice_steps': steps,
                    'language': language, 'model_language': language_code(language, family=family)}
        finally:
            self.lib.audiocpp_result_free(result)
            self.lib.audiocpp_request_free(request)

    def close(self):
        getattr(self, '_reference_cache', {}).clear()
        self._reference_cache_bytes = 0
        try:
            if self.lib is not None:
                for name in ('session', 'model', 'registry'):
                    handle = getattr(self, name)
                    if handle:
                        getattr(self.lib, 'audiocpp_'+name+'_free')(handle)
                        setattr(self, name, C.c_void_p())
        finally:
            try:
                if self._dll_directory is not None:
                    self._dll_directory.close()
                    self._dll_directory = None
            finally:
                stack = getattr(self, '_model_path_stack', None)
                if stack is not None:
                    stack.close()


def serve(data, threads, device, source=None, protocol=None, errors=None, family='omnivoice', native_performance='off'):
    _validate(threads, 8 if family == 'voxcpm2' else 16, device, 'fr', '', family=family)
    validate_native_performance(native_performance, device, family)
    source, protocol, errors = source or sys.stdin, protocol or sys.stdout, errors or sys.stderr
    session = None
    try:
        for line in source:
            ident = None
            try:
                request = json.loads(line)
                ident = request['id']
                output = Path(request['output']).resolve()
                if not output.is_relative_to(Path(data).resolve()):
                    raise ValueError('Tệp kết quả native phải nằm trong thư mục dữ liệu.')
                with contextlib.redirect_stdout(errors):
                    if session is None:
                        session = (NativeSession(data, threads, device, family=family, native_performance=native_performance) if family != 'omnivoice'
                                   else NativeSession(data, threads, device))
                    info = session.synthesize(request['text'], Path(request['reference_wav']), output,
                                              steps=request['steps'], language=request['language'],
                                              reference_text=request.get('reference_text', ''))
                response = {'id': ident, 'ok': True, 'output': str(output), 'execution': info}
            except Exception as exc:
                traceback.print_exc(file=errors)
                if session is not None:
                    session.close()
                    session = None
                response = {'id': ident, 'ok': False,
                            'error': 'Không tạo được giọng ' + ('VoxCPM2 native' if family == 'voxcpm2' else 'OmniVoice') + ' '+device.upper()+': '+str(exc)[:500]}
            protocol.write(json.dumps(response, ensure_ascii=False)+'\n')
            protocol.flush()
    finally:
        if session is not None:
            session.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--family', choices=('omnivoice', 'voxcpm2'), default='omnivoice')
    parser.add_argument('--native-performance', choices=('off', 'cuda_perf'), default='off')
    args = parser.parse_args()
    validate_native_performance(args.native_performance, args.device, args.family)
    # Native code writes directly to file descriptor 1. Preserve the protocol
    # pipe separately before moving ALL library output to the task log.
    with os.fdopen(os.dup(1), 'w', encoding='utf-8', buffering=1) as protocol:
        os.dup2(2, 1)
        sys.stdout = sys.stderr
        if args.family == 'omnivoice':
            serve(args.data_dir.resolve(), args.threads, args.device, protocol=protocol)
        else:
            serve(args.data_dir.resolve(), args.threads, args.device, protocol=protocol,
                  family=args.family, native_performance=args.native_performance)


if __name__ == '__main__':
    main()
