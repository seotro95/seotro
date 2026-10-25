"""Offline runtime and two-preset speech checks, independent of the job queue.

The launcher isolates runtime imports in a child process so that a broken native
DLL cannot take down startup without a readable diagnostic. No weights are
loaded by the runtime probe. Only the explicit speech check performs inference.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
import time
import uuid

from state_io import write_json_atomic
from voice_errors import describe_failure


BASE = Path(__file__).resolve().parent
TEST_TEXT = 'Nyob zoo, kuv zoo siab tau ntsib nej hnub no.'
OUTPUT_SAMPLE_RATE = 24000


class HealthError(RuntimeError):
    """A fixed, actionable diagnostic message safe to save and display."""


def diagnostics_directory(base=BASE):
    data = Path(os.getenv('VOICE_STUDIO_DATA_DIR', os.getenv(
        'HMOOB_DATA_DIR', str(Path(base) / '.data-hmong')))).expanduser().resolve()
    return data / 'diagnostics'


def _report_path(base, kind):
    if kind == 'runtime' and _private_runtime_id() is not None:
        return diagnostics_directory(base) / ('.runtime-' + _private_runtime_id() + '.json')
    return diagnostics_directory(base) / ('runtime-check.json' if kind == 'runtime' else 'speech-check.json')


def _private_runtime_id():
    ident = os.getenv('HMOOB_HEALTH_PRIVATE_RUNTIME_ID')
    if (isinstance(ident, str) and len(ident) == 32
            and all(character in '0123456789abcdef' for character in ident)
            and ident == os.getenv('HMOOB_HEALTH_RUN_ID')):
        return ident
    return None


def _new_report(base, kind):
    return {'schema_version': 1, 'kind': kind, 'ok': False, 'success': False,
            'run_id': os.getenv('HMOOB_HEALTH_RUN_ID') or uuid.uuid4().hex,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'backend': os.getenv('HMOOB_BACKEND', 'f5').strip().lower(),
            'phase': 'starting', 'message': 'Đang bắt đầu kiểm tra…',
            'inference_tested': False, 'report_path': str(_report_path(base, kind))}


def _save(report):
    path = Path(report['report_path'])
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, report)


def _phase(report, name, message):
    report.update(phase=name, message=message)
    _save(report)
    print(message, flush=True)


def _fail(report, exc=None, *, returncode=None, log_tail=''):
    message = str(exc) if isinstance(exc, HealthError) else describe_failure(
        exc, returncode=returncode, log_tail=log_tail)
    report.update(ok=False, success=False, message=message)
    if returncode is not None:
        report['returncode'] = returncode
    try:
        _save(report)
    except OSError as write_error:
        report['report_saved'] = False
        report['diagnostic_error'] = describe_failure(write_error)
    print('LỖI: ' + message, flush=True)
    if report.get('report_saved') is False:
        print('Không lưu được báo cáo: ' + report['diagnostic_error'], flush=True)
    else:
        print('Báo cáo: ' + report['report_path'], flush=True)
    return report


def _configuration(backend):
    if backend not in {'native', 'f5'}:
        raise HealthError('HMOOB_BACKEND chỉ nhận f5 hoặc native. Mở lại launcher của gói đầy đủ.')
    if backend == 'native':
        from hmong_native import runtime_settings
        # The native backend accepts legacy F5 precision overrides and runs
        # them in FP32, using exactly the same normalization as real inference.
        from hmong_engine import EngineError
        try:
            return runtime_settings()
        except EngineError:
            raise HealthError('Cấu hình đọc nhanh không hợp lệ. Đặt HMOOB_DEVICE=auto, cpu hoặc cuda '
                              'và HMOOB_PRECISION=auto hoặc fp32 rồi mở lại tool.') from None
    # Mirror the F5 adapter's accepted values so a successful probe cannot hide
    # an environment setting that the subsequent real inference would reject.
    device = os.getenv('HMOOB_DEVICE', 'auto').lower()
    precision = os.getenv('HMOOB_PRECISION', 'auto')
    if device not in {'auto', 'cpu', 'cuda', 'mps'} or precision not in {'auto', 'fp32', 'int8'}:
        raise HealthError('Cấu hình F5 không hợp lệ. Đặt HMOOB_DEVICE=auto, cpu, cuda hoặc mps '
                          'và HMOOB_PRECISION=auto, fp32 hoặc int8 rồi mở lại tool.')
    return {'device': device, 'precision': precision}


def _offline_environment(base):
    environment = dict(os.environ)
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONPATH', None)
    environment.update(PYTHONUTF8='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       HF_DATASETS_OFFLINE='1')
    cache = diagnostics_directory(base).parent / 'cache'
    for name, folder in (('MPLCONFIGDIR', 'matplotlib'), ('NUMBA_CACHE_DIR', 'numba'),
                         ('XDG_CACHE_HOME', 'xdg')):
        environment.setdefault(name, str(cache / folder))
    return environment


def probe_runtime(base=BASE):
    """Probe the current process offline; never construct or load a model."""
    report = _new_report(base, 'runtime')
    report.update(checks=[], versions={}, runtime={'python': platform.python_version(),
                  'system': platform.system(), 'machine': platform.machine(),
                  'bits': struct.calcsize('P') * 8})
    started = time.monotonic()
    try:
        _phase(report, 'configuration', 'Đang kiểm tra cấu hình Python và bộ tạo giọng…')
        if os.getenv('HMOOB_HEALTH_PRIVATE_RUNTIME_ID') is not None and _private_runtime_id() is None:
            raise HealthError('Mã kiểm tra thư viện không hợp lệ. Mở lại tool bằng launcher của gói đầy đủ.')
        if report['runtime']['bits'] != 64:
            raise HealthError('Bộ tạo giọng cần Python 64-bit. Dùng gói Portable Windows x64 đầy đủ.')
        report['configuration'] = _configuration(report['backend'])
        environment = _offline_environment(base)
        for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_DATASETS_OFFLINE',
                     'MPLCONFIGDIR', 'NUMBA_CACHE_DIR', 'XDG_CACHE_HOME'):
            os.environ[name] = environment[name]
        modules = {}
        for name in ('torch', 'numpy', 'soundfile', 'soxr', 'scipy.signal', 'librosa'):
            _phase(report, 'imports', 'Đang nạp thử thư viện ' + name + '…')
            modules[name] = importlib.import_module(name)
            report['checks'].append({'name': 'import:' + name, 'ok': True})
            top = sys.modules.get(name.split('.')[0], modules[name])
            version = getattr(top, '__version__', None)
            if isinstance(version, str):
                report['versions'][name.split('.')[0]] = version
        torch, np = modules['torch'], modules['numpy']
        device = report['configuration']['device']
        if device == 'cuda' and not torch.cuda.is_available():
            raise HealthError('Đã chọn CUDA nhưng PyTorch chưa nhận GPU. Chọn HMOOB_DEVICE=cpu '
                              'rồi mở lại tool, hoặc cài bộ CUDA phù hợp trong tools.')
        if device == 'mps' and not (getattr(torch.backends, 'mps', None)
                                    and torch.backends.mps.is_available()):
            raise HealthError('Đã chọn MPS nhưng máy này không có MPS khả dụng. Chọn HMOOB_DEVICE=cpu.')
        _phase(report, 'tensor', 'Đang chạy phép tính PyTorch CPU và kiểm tra NumPy…')
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        with torch.inference_mode():
            source = torch.from_numpy(np.ones((1, 1, 64), dtype=np.float32))
            output = torch.nn.functional.conv1d(source, torch.ones((1, 1, 3)))
            if tuple(output.shape) != (1, 1, 62) or not bool(torch.isfinite(output).all()):
                raise HealthError('PyTorch trả dữ liệu không hợp lệ. Giải nén lại gói Portable đầy đủ.')
            if not np.isfinite(output.numpy()).all():
                raise HealthError('PyTorch và NumPy không tương thích. Cài lại requirements-hmong.txt.')
        report['checks'].append({'name': 'cpu-conv1d-numpy', 'ok': True})
        _phase(report, 'audio', 'Đang thử đọc ghi WAV và đổi tần số âm thanh…')
        samples = (np.sin(np.arange(2205, dtype=np.float32) * .05) * .1).astype(np.float32)
        converted = modules['soxr'].resample(samples, 22050, OUTPUT_SAMPLE_RATE, quality='HQ')
        filtered = modules['scipy.signal'].resample_poly(samples, 2, 1)
        mel = modules['librosa'].filters.mel(sr=22050, n_fft=128, n_mels=8)
        if not all(np.isfinite(item).all() and item.size for item in (converted, filtered, mel)):
            raise HealthError('Thư viện âm thanh trả dữ liệu không hợp lệ. Giải nén lại gói Portable đầy đủ.')
        stream = io.BytesIO()
        modules['soundfile'].write(stream, converted, OUTPUT_SAMPLE_RATE, format='WAV', subtype='PCM_16')
        stream.seek(0)
        decoded, rate = modules['soundfile'].read(stream, dtype='float32')
        if rate != OUTPUT_SAMPLE_RATE or not len(decoded) or not np.isfinite(decoded).all() or not np.any(decoded):
            raise HealthError('Không đọc ghi được WAV hợp lệ. Kiểm tra thư viện soundfile của gói Portable.')
        report['checks'].append({'name': 'wav-soxr-scipy-librosa', 'ok': True})
        _phase(report, 'backend-imports', 'Đang nạp thử mã mô hình, chưa đọc trọng số…')
        required = (('hmong_native_vendor.vits.models', 'hmong_native_vendor.openvoice.models',
                     'hmong_native_vendor.openvoice.mel_processing',
                     'hmong_native_vendor.watermark.models.my_model') if report['backend'] == 'native'
                    else ('torchaudio', 'f5_tts.model', 'vocos'))
        for name in required:
            importlib.import_module(name)
            report['checks'].append({'name': 'import:' + name, 'ok': True})
        report.update(ok=True, success=True, phase='complete',
                      message='PASS: thư viện và phép tính âm thanh hoạt động. Chưa chạy tạo giọng.',
                      elapsed_seconds=round(time.monotonic() - started, 3))
        _save(report)
        print(report['message'], flush=True)
        print('Báo cáo: ' + report['report_path'], flush=True)
        return report
    except Exception as exc:
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        return _fail(report, exc)


def run_runtime_probe(base=BASE, timeout=90):
    """Run one fresh isolated probe using the launcher's selected interpreter."""
    base = Path(base).resolve()
    report = _new_report(base, 'runtime')
    # A double click can run independent probes at the same time. Each parent
    # reads only its own child's file; the public report is a final snapshot.
    report['run_id'] = uuid.uuid4().hex
    public_path = diagnostics_directory(base) / 'runtime-check.json'
    private_path = public_path.with_name('.runtime-' + report['run_id'] + '.json')
    report['report_path'] = str(private_path)
    environment = _offline_environment(base)
    environment['HMOOB_HEALTH_RUN_ID'] = report['run_id']
    environment['HMOOB_HEALTH_PRIVATE_RUNTIME_ID'] = report['run_id']

    def public(item):
        # Never trust a report's path for either promotion or cleanup.
        item['report_path'] = str(public_path)
        return item

    try:
        try:
            _phase(report, 'subprocess', 'Đang kiểm tra bộ tạo giọng trong tiến trình riêng…')
            result = subprocess.run([sys.executable, str(base / 'hmong_health.py'), '--probe-runtime'],
                                    cwd=base, env=environment, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                                    text=True, encoding='utf-8', errors='replace')
        except subprocess.TimeoutExpired:
            return _fail(public(report), HealthError('Kiểm tra thư viện tạo giọng quá thời gian. Đóng bớt ứng dụng, '
                                                    'mở lại tool; nếu vẫn lỗi hãy giải nén lại gói Portable đầy đủ.'))
        except OSError as exc:
            return _fail(public(report), exc)
        try:
            if private_path.stat().st_size > 100_000:
                raise ValueError('invalid report size')
            child = json.loads(private_path.read_text(encoding='utf-8'))
            if (not isinstance(child, dict) or child.get('schema_version') != 1
                    or child.get('kind') != 'runtime' or child.get('run_id') != report['run_id']
                    or not isinstance(child.get('ok'), bool) or not isinstance(child.get('message'), str)):
                raise ValueError('invalid report identity')
        except (OSError, ValueError, TypeError, RecursionError):
            child = None
        if child and ((result.returncode == 0 and child['ok']) or
                      (result.returncode == 1 and not child['ok'] and child.get('phase') != 'subprocess')):
            public(child)
            try:
                _save(child)
            except OSError as exc:
                return _fail(child, exc)
            print(('' if child['ok'] else 'LỖI: ') + child['message'], flush=True)
            print('Báo cáo: ' + child['report_path'], flush=True)
            return child
        return _fail(public(child or report), returncode=result.returncode, log_tail=result.stdout[-8000:])
    finally:
        try:
            private_path.unlink(missing_ok=True)
        except OSError:
            pass


def _reference_snapshot(ident, folder):
    import hmong_assets
    from hmong_engine import EngineError, _reference_identity
    try:
        path, words = hmong_assets.reference(ident)
        content = Path(path).read_bytes()
        expected = hmong_assets.references()[ident.removeprefix('hmong-')]['reference_sha256']
    except (OSError, ValueError, KeyError, TypeError):
        raise HealthError('Thiếu giọng mẫu hoặc SHA-256 không đạt. Giải nén lại toàn bộ thư mục '
                          'assets/hmong của gói Portable đầy đủ.') from None
    digest = hashlib.sha256(content).hexdigest()
    if digest != expected:
        raise HealthError('Giọng mẫu thay đổi trong lúc kiểm tra. Giải nén lại assets/hmong của gói đầy đủ.')
    snapshot = folder / (ident + '.wav')
    snapshot.write_bytes(content)
    try:
        _reference_identity(snapshot, words)
    except EngineError:
        raise HealthError('Giọng mẫu sai định dạng hoặc độ dài. Giải nén lại assets/hmong của gói đầy đủ.') from None
    identity = {'version': 1, 'audio_sha256': digest, 'transcript': words}
    fingerprint = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True,
                                            separators=(',', ':')).encode('utf-8')).hexdigest()
    return snapshot, words, {'id': ident, 'reference_sha256': digest,
                             'reference_text': words, 'reference_fingerprint': fingerprint}


def _write_voice(samples, rate, target):
    import numbers
    import numpy as np
    import soundfile as sf
    import soxr
    samples = np.asarray(samples, dtype=np.float32)
    if (isinstance(rate, bool) or not isinstance(rate, numbers.Integral) or not 8000 <= rate <= 96000
            or samples.ndim != 1 or not 0 < len(samples) <= int(rate) * 120
            or not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 1e-6):
        raise HealthError('Mô hình trả âm thanh rỗng, im lặng hoặc không hợp lệ. Kiểm tra lại mô hình đã tải.')
    if rate != OUTPUT_SAMPLE_RATE:
        samples = soxr.resample(samples, int(rate), OUTPUT_SAMPLE_RATE, quality='HQ')
    if not len(samples) or not np.isfinite(samples).all():
        raise HealthError('Đổi tần số âm thanh thất bại. Kiểm tra thư viện soxr trong gói Portable.')
    peak = float(np.max(np.abs(samples)))
    if peak > .98:
        samples = samples * (.98 / peak)
    temporary = target.with_name('.' + target.stem + '-' + uuid.uuid4().hex + '.wav')
    try:
        sf.write(str(temporary), samples, OUTPUT_SAMPLE_RATE, format='WAV', subtype='PCM_16')
        info = sf.info(str(temporary))
        pcm, actual_rate = sf.read(str(temporary), dtype='int16', always_2d=True)
        if (info.samplerate != OUTPUT_SAMPLE_RATE or actual_rate != OUTPUT_SAMPLE_RATE
                or info.channels != 1 or info.subtype != 'PCM_16' or info.frames <= 0
                or pcm.shape != (info.frames, 1) or not np.any(pcm)):
            raise HealthError('Tệp WAV kiểm tra rỗng hoặc sai định dạng. Kiểm tra thư viện soundfile.')
        normalized = pcm.astype(np.float64) / 32768
        metadata = {'output': target.name, 'sample_rate': actual_rate, 'channels': info.channels,
                    'subtype': info.subtype, 'frames': info.frames,
                    'duration_seconds': info.frames / actual_rate,
                    'peak': float(np.max(np.abs(normalized))),
                    'rms': float(np.sqrt(np.mean(normalized ** 2))),
                    'nonzero_samples': int(np.count_nonzero(pcm)),
                    'output_sha256': hashlib.sha256(temporary.read_bytes()).hexdigest()}
        temporary.replace(target)
        return metadata
    finally:
        temporary.unlink(missing_ok=True)


def test_voices(base=BASE):
    """Actually synthesize both bundled voices offline without jobs or history."""
    report = _new_report(base, 'speech')
    report.update(voices=[], text=TEST_TEXT, pronunciation_evaluated=False,
                  reference_similarity_evaluated=False)
    started = time.monotonic()
    try:
        _phase(report, 'configuration', 'Đang chuẩn bị kiểm tra tạo giọng nam và nữ…')
        report['configuration'] = _configuration(report['backend'])
        environment = _offline_environment(base)
        for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_DATASETS_OFFLINE',
                     'MPLCONFIGDIR', 'NUMBA_CACHE_DIR', 'XDG_CACHE_HOME'):
            os.environ[name] = environment[name]
        folder = diagnostics_directory(base)
        for gender in ('male', 'female'):
            (folder / ('test-' + gender + '.wav')).unlink(missing_ok=True)
        _phase(report, 'models', 'Đang xác minh mô hình đã lưu; bước này không tải mạng…')
        module = importlib.import_module('hmong_native' if report['backend'] == 'native' else 'hmong_engine')
        from hmong_engine import EngineError
        try:
            module.verify_models()
        except EngineError:
            raise HealthError('Thiếu mô hình hoặc kiểm tra SHA-256 không đạt. Chạy launcher --setup-only '
                              'bằng mạng được phép rồi chạy lại --test-voice.') from None
        engine = module.SpeechEngine()
        engine.set_progress_callback(lambda message: _phase(report, 'synthesis', message))
        with tempfile.TemporaryDirectory(prefix='reference-check-', dir=folder) as temporary:
            snapshots = [_reference_snapshot('hmong-' + gender, Path(temporary))
                         for gender in ('male', 'female')]
            for gender, (snapshot, words, voice) in zip(('male', 'female'), snapshots):
                _phase(report, 'synthesis', 'Đang tạo thử giọng ' + ('nam' if gender == 'male' else 'nữ') + '…')
                voice_started = time.monotonic()
                report['inference_tested'] = True
                _save(report)
                samples, rate = engine.synthesize(TEST_TEXT, snapshot, words, speed=1.0,
                                                  quality='standard' if report['backend'] == 'native' else 'fast')
                _phase(report, 'output', 'Đang kiểm tra tệp WAV giọng ' + ('nam' if gender == 'male' else 'nữ') + '…')
                voice.update(_write_voice(samples, rate, folder / ('test-' + gender + '.wav')))
                voice.update(ok=True, elapsed_seconds=round(time.monotonic() - voice_started, 3))
                report['voices'].append(voice)
                _save(report)
        report.update(ok=True, success=True, phase='complete', device=engine.device,
                      message='PASS: đã tạo thật cả giọng nam và nữ. Mở hai tệp WAV để nghe kiểm tra.',
                      elapsed_seconds=round(time.monotonic() - started, 3))
        _save(report)
        print(report['message'], flush=True)
        print('Âm thanh: ' + str(folder / 'test-male.wav') + ' và ' + str(folder / 'test-female.wav'), flush=True)
        print('Báo cáo: ' + report['report_path'], flush=True)
        return report
    except Exception as exc:
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        return _fail(report, exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Kiểm tra ngoại tuyến Voice Studio Hmong')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--probe-runtime', action='store_true', help='Thử thư viện; không nạp mô hình.')
    action.add_argument('--test-voice', action='store_true', help='Tạo thật hai giọng mẫu, không thêm vào lịch sử.')
    args = parser.parse_args(argv)
    report = probe_runtime() if args.probe_runtime else test_voices()
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
