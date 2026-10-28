"""Private reference-voice adapter; heavyweight imports stay in a child runtime.

VoxCPM2 2.0.3 supports Thai and the other reference languages. Normal inference
is offline. Only the explicitly invoked preparation command downloads models.
"""
from __future__ import annotations

import argparse
import atexit
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import uuid

BASE = Path(__file__).resolve().parent
MODEL_REPO = 'openbmb/VoxCPM2'
PACKAGE_VERSION = '2.0.3'
_client = None
_client_lock = threading.RLock()


def data_directory(value=None):
    return Path(value or os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE/'.data'))).resolve()


def runtime_python():
    override = os.environ.get('VOICE_STUDIO_INTERNATIONAL_PYTHON')
    if override:
        # Keep a venv's executable path: resolving its symlink would run the
        # base interpreter and lose the isolated environment's dependencies.
        return Path(override).absolute()
    root = BASE.parent/'runtime-international'
    return root/('python.exe' if os.name == 'nt' else 'bin/python')


def isolated_environment(data, threads=4, offline=True):
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'TRANSFORMERS_CACHE'):
        env.pop(key, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', VOICE_STUDIO_DATA_DIR=str(data),
               HF_HOME=str(data/'models/cache'), HF_HUB_DISABLE_XET='1',
               HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1', GRADIO_ANALYTICS_ENABLED='False',
               HF_HUB_OFFLINE='1' if offline else '0', TRANSFORMERS_OFFLINE='1' if offline else '0',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS=str(threads), OMP_NUM_THREADS=str(threads),
               TOKENIZERS_PARALLELISM='false')
    return env


def prepared_model(data):
    marker = json.loads((data/'models/voxcpm.ready').read_text(encoding='utf-8'))
    relative = Path(marker['model_dir'])
    if relative.is_absolute() or '..' in relative.parts or len(relative.parts) != 1:
        raise ValueError('Đường dẫn model quốc tế không hợp lệ.')
    model = data/'models'/relative
    config = json.loads((model/'config.json').read_text(encoding='utf-8'))
    if config.get('architecture', '').lower() != 'voxcpm2' or config.get('dtype') != 'float32':
        raise ValueError('Model quốc tế chưa được chuẩn bị ở FP32 cho CPU.')
    if not any((model/name).is_file() for name in ('model.safetensors', 'pytorch_model.bin')):
        raise ValueError('Thiếu trọng số model quốc tế.')
    if not any((model/name).is_file() for name in ('audiovae.safetensors', 'audiovae.pth')):
        raise ValueError('Thiếu bộ mã hóa âm thanh quốc tế.')
    return model


class _BackendClient:
    def __init__(self, data, threads):
        executable = runtime_python()
        if not executable.is_file() or not (data/'models/voxcpm.ready').is_file():
            raise ValueError('Bộ giọng quốc tế chưa sẵn sàng. Chạy TAI_GIONG_DA_NGON_NGU.bat một lần rồi mở lại tool.')
        self.key = (str(executable), str(data), threads)
        self.lock = threading.RLock()
        self.responses = queue.Queue()
        data.mkdir(parents=True, exist_ok=True)
        self.log = (data/'international-backend.log').open('a', encoding='utf-8')
        self.process = subprocess.Popen(
            [str(executable), '-s', '-X', 'utf8', str(Path(__file__).resolve()), '--serve',
             '--data-dir', str(data), '--threads', str(threads)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding='utf-8', bufsize=1, env=isolated_environment(data, threads))
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            for line in self.process.stdout:
                self.responses.put(line)
        finally:
            self.responses.put(None)

    def synthesize(self, text, reference, output, steps=10):
        with self.lock:
            ident = uuid.uuid4().hex
            request = {'id': ident, 'text': text, 'reference_wav': str(reference), 'output': str(output), 'steps': steps}
            try:
                self.process.stdin.write(json.dumps(request, ensure_ascii=False)+'\n')
                self.process.stdin.flush()
                line = self.responses.get(timeout=600)
                if line is None:
                    raise ValueError('Bộ giọng quốc tế đã dừng. Kiểm tra international-backend.log trong thư mục dữ liệu.')
                response = json.loads(line)
                if not response.get('ok'):
                    raise ValueError('Không tạo được giọng quốc tế: '+response.get('error', 'lỗi chưa xác định'))
                if response.get('id') != ident or response.get('output') != str(output):
                    raise ValueError('Phản hồi bộ giọng quốc tế không khớp tác vụ.')
            except (OSError, queue.Empty, json.JSONDecodeError) as exc:
                self.close()
                raise ValueError('Bộ giọng quốc tế chưa phản hồi; có thể bấm tiếp tục để thử lại.') from exc

    def close(self):
        with self.lock:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()
            self.log.close()


def close_backends():
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None


atexit.register(close_backends)


def create_synthesizer(reference_audio: Path, data: Path, threads: int = 4, steps: int = 10):
    """Keep one model resident across different reference voices, without Torch here."""
    reference = Path(reference_audio).resolve()
    data = Path(data).resolve()
    threads = max(1, min(8, int(threads)))
    if type(steps) is not int or steps not in {4, 8, 10}:
        raise ValueError('Chọn bộ đọc quốc tế 4, 8 hoặc 10 bước.')
    if not reference.is_file():
        raise ValueError('Không tìm thấy mẫu giọng đã chọn.')

    def synthesize(text, output):
        global _client
        key = (str(runtime_python()), str(data), threads)
        with _client_lock:
            if _client is None or _client.key != key or _client.process.poll() is not None:
                close_backends()
                _client = _BackendClient(data, threads)
            client = _client
        client.synthesize(text, reference, Path(output).resolve(), steps=steps)
    return synthesize


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)


def _load_model(path, threads):
    import torch
    from voxcpm import VoxCPM
    if importlib.metadata.version('voxcpm') != PACKAGE_VERSION:
        raise ValueError('Cần voxcpm '+PACKAGE_VERSION+' trong runtime-international.')
    torch.set_num_threads(max(1, min(8, int(threads))))
    model = VoxCPM.from_pretrained(str(path), local_files_only=True, load_denoiser=False,
                                   optimize=False, device='cpu')
    from voxcpm_acceleration import enable_active_kv_attention, CachedReferenceModel
    status = enable_active_kv_attention(model)
    print('Voice Studio CPU acceleration: '+json.dumps(status), file=sys.stderr, flush=True)
    optimized = CachedReferenceModel(model)
    optimized.voice_studio_acceleration = status
    return optimized


def _generate(model, text, reference, output, steps=10):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Chưa có lời đọc.')
    if type(steps) is not int or steps not in {4, 8, 10}:
        raise ValueError('Số bước đọc quốc tế không hợp lệ.')
    options = {'text': text, 'cfg_value': 2.0, 'inference_timesteps': steps,
               'normalize': False, 'denoise': False, 'retry_badcase': True}
    if reference is not None:
        options['reference_wav_path'] = str(reference)
    samples = np.asarray(model.generate(**options), dtype=np.float32).squeeze()
    if samples.ndim != 1 or samples.size == 0 or not np.isfinite(samples).all() or np.max(np.abs(samples)) <= 1e-5:
        raise ValueError('Model không tạo được lời đọc hợp lệ.')
    rate = int(model.tts_model.sample_rate)
    if rate != 24000:
        import math
        divisor = math.gcd(rate, 24000)
        samples = resample_poly(samples, 24000//divisor, rate//divisor).astype(np.float32)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output), samples, 24000, subtype='PCM_16')
    return len(samples)


def _model_files_available(names):
    weights = next((name for name in ('model.safetensors', 'pytorch_model.bin') if name in names), None)
    vae = next((name for name in ('audiovae.safetensors', 'audiovae.pth') if name in names), None)
    if not weights or not vae or 'config.json' not in names:
        raise ValueError('Bộ model quốc tế thiếu config, model hoặc AudioVAE.')
    return weights, vae


def _source_model(data, provided=None):
    """Use an integrity-checked public model pack, or explicitly download HF."""
    candidates = [Path(provided)] if provided else [BASE.parent/'voxcpm2-original', data/'models/voxcpm2-original']
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        provenance = json.loads((candidate/'MODEL_PROVENANCE.json').read_text(encoding='utf-8'))
        if provenance.get('repository', '').lower() != MODEL_REPO.lower():
            raise ValueError('Bộ model tải sẵn không thuộc nguồn VoxCPM2 đã chọn.')
        revision = provenance.get('revision', '')
        if len(revision) != 40 or any(ch not in '0123456789abcdef' for ch in revision):
            raise ValueError('Bộ model tải sẵn thiếu phiên bản cố định.')
        expected = {entry['name']: entry for entry in provenance['files']}
        required = _model_files_available(expected)
        for name in (*required, 'config.json'):
            if name not in expected:
                raise ValueError('Bộ model tải sẵn thiếu bản ghi kiểm tra tệp '+name)
        for name, record in expected.items():
            path = Path(name)
            if path.is_absolute() or '..' in path.parts or len(path.parts) != 1:
                raise ValueError('Tên tệp trong bộ model không hợp lệ.')
            source = candidate/path
            if not source.is_file() or source.stat().st_size != record['size']:
                raise ValueError('Tệp model bị thiếu hoặc tải chưa đủ: '+name)
            with source.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != record['sha256']:
                    raise ValueError('SHA256 của model không khớp: '+name)
        return candidate, revision, expected
    if provided:
        raise ValueError('Không tìm thấy thư mục model đã chọn.')
    from huggingface_hub import HfApi, snapshot_download
    info = HfApi().model_info(MODEL_REPO, files_metadata=True)
    revision = info.sha
    if not revision or len(revision) != 40:
        raise ValueError('Không xác nhận được phiên bản model quốc tế từ nguồn phát hành.')
    siblings = {entry.rfilename: entry for entry in info.siblings}
    weights, vae = _model_files_available(siblings)
    allowed = [name for name in siblings if '/' not in name and
               (name.endswith(('.json', '.model')) or name in {weights, vae, 'README.md'}
                or name.startswith(('LICENSE', 'NOTICE')))]
    source = Path(snapshot_download(MODEL_REPO, revision=revision, cache_dir=str(data/'models/cache/hub'),
                                   allow_patterns=allowed))
    expected = {}
    for name in allowed:
        entry = siblings[name]
        lfs = getattr(entry, 'lfs', None)
        digest = getattr(lfs, 'sha256', None) if lfs else None
        if isinstance(lfs, dict):digest = lfs.get('sha256')
        if name in {weights, vae} and not digest:
            raise ValueError('Nguồn phát hành chưa cung cấp SHA256 cho '+name)
        expected[name] = {'name': name, 'size': getattr(entry, 'size', None), 'sha256': digest}
    return source, revision, expected


def prepare_model(data, threads=4, model_source=None):
    """Explicit download, immutable upstream revision, derived CPU-only config."""
    models = data/'models'
    models.mkdir(parents=True, exist_ok=True)
    marker = models/'voxcpm.ready'
    if marker.is_file():
        try:
            return {'ok': True, 'model_dir': str(prepared_model(data)), 'already_prepared': True}
        except (OSError, ValueError, KeyError):
            pass
    marker.unlink(missing_ok=True)
    source, revision, expected = _source_model(data, model_source)
    destination = models/('voxcpm2-cpu-'+revision[:12]+'-fp32')
    destination.mkdir(exist_ok=True)
    manifest = []
    for file in source.iterdir():
        if not file.is_file() or file.name not in expected:
            continue
        target = destination/file.name
        with file.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        record = expected[file.name]
        if (record.get('sha256') and digest != record['sha256']) or (record.get('size') is not None and file.stat().st_size != record['size']):
            raise ValueError('Kiểm tra toàn vẹn model không đạt: '+file.name)
        manifest.append({'name': file.name, 'sha256': digest, 'size': file.stat().st_size})
        if file.name == 'config.json':
            config = json.loads(file.read_text(encoding='utf-8'))
            if config.get('architecture', '').lower() != 'voxcpm2':
                raise ValueError('Nguồn tải không phải model VoxCPM2.')
            config['device'] = 'cpu'
            config['dtype'] = 'float32'
            _write_json(target, config)
        else:
            if target.exists():
                with target.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                        raise ValueError('Model đã chuẩn bị có tệp khác nguồn: '+file.name)
            else:
                try:
                    os.link(file.resolve(), target)
                except OSError:
                    shutil.copy2(file, target)
    _write_json(destination/'UPSTREAM-MANIFEST.json', {'repository': MODEL_REPO, 'revision': revision,
                'original_files': manifest, 'config_override': {'device': 'cpu', 'dtype': 'float32'}})
    model = _load_model(destination, threads)
    output = models/'voxcpm-preparation-check.wav'
    frames = _generate(model, 'สวัสดีครับ ยินดีต้อนรับ', None, output)
    if frames < 2400:
        raise ValueError('Kiểm tra tạo lời tiếng Thái chưa hoàn tất.')
    record = {'repository': MODEL_REPO, 'revision': revision, 'model_dir': destination.name,
              'package_version': PACKAGE_VERSION, 'sample_rate': 24000, 'verified_thai_frames': frames}
    _write_json(marker, record)
    output.unlink(missing_ok=True)
    return {'ok': True, **record}


def check_runtime(data):
    import torch
    import torchaudio
    import voxcpm
    version = importlib.metadata.version('voxcpm')
    if version != PACKAGE_VERSION or torch.__version__.split('+')[0] != '2.8.0':
        raise ValueError('Phiên bản thư viện quốc tế không khớp bản đã chọn.')
    ready = False
    try:
        prepared_model(data)
        ready = True
    except (OSError, ValueError, KeyError):
        pass
    return {'ok': True, 'runtime_ok': True, 'model_ready': ready, 'voxcpm': version,
            'torch': torch.__version__, 'torchaudio': torchaudio.__version__, 'device': 'cpu'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--prepare-model', action='store_true')
    parser.add_argument('--data-dir')
    parser.add_argument('--model-source', type=Path)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    data = data_directory(args.data_dir)
    protocol = sys.stdout
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if args.check:
                result = check_runtime(data)
            elif args.prepare_model:
                result = prepare_model(data, args.threads, args.model_source)
            elif args.serve:
                model = _load_model(prepared_model(data), args.threads)
                result = None
            else:
                parser.error('Chọn --serve, --check hoặc --prepare-model.')
        if result is not None:
            protocol.write(json.dumps(result, ensure_ascii=False)+'\n')
            protocol.flush()
            return
        for line in sys.stdin:
            ident = None
            try:
                request = json.loads(line)
                ident = request.get('id')
                reference = Path(request['reference_wav']).resolve()
                output = Path(request['output']).resolve()
                if not reference.is_file() or data/'parts' not in output.parents:
                    raise ValueError('Đường dẫn mẫu hoặc tệp đầu ra không hợp lệ.')
                with contextlib.redirect_stdout(sys.stderr):
                    frames = _generate(model, request['text'], reference, output, steps=request.get('steps', 10))
                response = {'ok': True, 'id': ident, 'output': str(output), 'sample_rate': 24000, 'frames': frames}
            except Exception as exc:
                response = {'ok': False, 'id': ident, 'error': str(exc)}
            protocol.write(json.dumps(response, ensure_ascii=False)+'\n')
            protocol.flush()
    except Exception as exc:
        protocol.write(json.dumps({'ok': False, 'fatal': True, 'error': str(exc)}, ensure_ascii=False)+'\n')
        protocol.flush()
        raise SystemExit(1)


if __name__ == '__main__':
    main()
