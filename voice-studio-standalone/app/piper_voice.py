"""Verified model preparation and bounded CPU-only Piper synthesis.

Models are ordinary files, so moving the portable folder needs no cache repair.
The app only loads prepared files. Network downloads happen during preparation.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor

from piper_catalog import DEMO_TEXTS, PIPER_MODELS, PIPER_REPOSITORY, PIPER_REVISION


def _model(model_key):
    try:
        return PIPER_MODELS[model_key]
    except KeyError:
        raise ValueError('Không tìm thấy giọng quốc tế đã chọn.') from None


def model_paths(data, model_key):
    model = _model(model_key)
    directory = Path(data) / 'models' / 'piper' / model_key
    return {
        'directory': directory,
        'model': directory / (model_key + '.onnx'),
        'config': directory / (model_key + '.onnx.json'),
        'card': directory / 'MODEL_CARD',
        'marker': directory / '.ready.json',
        'files': [(directory / item['name'], item) for item in model['files']],
    }


def model_ready(data, model_key):
    """Cheap readiness check; preparation performs full SHA256 verification."""
    paths = model_paths(data, model_key)
    try:
        marker = json.loads(paths['marker'].read_text(encoding='utf-8'))
        if not isinstance(marker, dict) or not isinstance(marker.get('sha256'), dict):
            return False
        if marker.get('revision') != PIPER_REVISION or marker.get('model') != model_key:
            return False
        if marker.get('sample_seconds', 0) <= 0 or not marker.get('nonzero'):
            return False
        return all(
            path.is_file() and path.stat().st_size == item['size']
            and marker.get('sha256', {}).get(item['name']) == item['sha256']
            for path, item in paths['files']
        )
    except (OSError, ValueError, TypeError):
        return False


def ready_languages(data):
    return list(dict.fromkeys(
        model['language'] for key, model in PIPER_MODELS.items() if model_ready(data, key)
    ))


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _download_file(path, item):
    if path.is_file() and path.stat().st_size == item['size'] and _sha256(path) == item['sha256']:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f'https://huggingface.co/{PIPER_REPOSITORY}/resolve/{PIPER_REVISION}/{item["path"]}?download=true'
    error = None
    for attempt in range(3):
        temporary = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.download', dir=path.parent)
            temporary = Path(temporary_name)
            digest = hashlib.sha256()
            size = 0
            request = urllib.request.Request(url, headers={'User-Agent': 'Voice-Studio-Portable/1.2'})
            with os.fdopen(descriptor, 'wb') as output, urllib.request.urlopen(request, timeout=90) as response:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > item['size']:
                        raise ValueError('Model download exceeds its pinned size.')
                    digest.update(block)
                    output.write(block)
            if size != item['size'] or digest.hexdigest() != item['sha256']:
                raise ValueError(f'Model checksum failed: {item["name"]}')
            temporary.replace(path)
            return
        except (OSError, ValueError) as caught:
            error = caught
            if attempt < 2:
                time.sleep(attempt + 1)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    raise RuntimeError(f'Không tải được giọng quốc tế: {item["name"]}') from error


def _load_voice(data, model_key, threads=0):
    """Construct the public Piper voice with explicit ONNX CPU resource limits.

    PiperVoice.load in 1.8.0 does not expose SessionOptions. Its default lets
    ONNX create threads for every visible host CPU, exceeding a container's CPU
    quota. The same public constructor accepts our bounded inference session.
    """
    import onnxruntime as ort
    from piper import PiperConfig, PiperVoice
    from nano_resources import cpu_budget

    paths = model_paths(data, model_key)
    selected = max(1, min(8, cpu_budget(), int(threads) if threads else 2))
    options = ort.SessionOptions()
    options.intra_op_num_threads = selected
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    options.add_session_config_entry('session.intra_op.allow_spinning', '0')
    options.add_session_config_entry('session.inter_op.allow_spinning', '0')
    config = PiperConfig.from_dict(json.loads(paths['config'].read_text(encoding='utf-8')))
    session = ort.InferenceSession(str(paths['model']), sess_options=options, providers=['CPUExecutionProvider'])
    return PiperVoice(session=session, config=config, download_dir=paths['directory'])


def _synthesizer(voice):
    from piper import SynthesisConfig
    configuration = SynthesisConfig(normalize_audio=True)

    def synthesize(text, output):
        with wave.open(str(output), 'wb') as audio:
            voice.synthesize_wav(text, audio, syn_config=configuration)

    return synthesize


def create_synthesizer(data, model_key, threads=0):
    """Return a warm callable(text, WAV_path); the worker caches this callable."""
    if not model_ready(data, model_key):
        raise RuntimeError('Giọng quốc tế chưa sẵn sàng. Hãy kiểm tra lại gói portable.')
    return _synthesizer(_load_voice(data, model_key, threads))


def check_model(data, model_key, threads=0):
    """Synthesize real native-language speech and report elapsed time and frames."""
    paths = model_paths(data, model_key)
    model = _model(model_key)
    start = time.perf_counter()
    synthesize = _synthesizer(_load_voice(data, model_key, threads))
    sample = paths['directory'] / '.prepare-sample.wav'
    try:
        synthesize(DEMO_TEXTS[model['language']], sample)
        with wave.open(str(sample), 'rb') as audio:
            seconds = audio.getnframes() / audio.getframerate()
            nonzero = False
            while block := audio.readframes(65536):
                nonzero |= any(block)
            rate = audio.getframerate()
        if seconds <= 0.1 or not nonzero:
            raise RuntimeError(f'Giọng quốc tế không tạo được âm thanh: {model_key}')
        return {
            'model': model_key, 'language': model['language'], 'culture': model['culture'],
            'revision': PIPER_REVISION, 'sample_seconds': seconds, 'sample_rate': rate,
            'nonzero': True, 'elapsed_seconds': round(time.perf_counter() - start, 6),
            'sha256': {item['name']: item['sha256'] for item in model['files']},
        }
    finally:
        sample.unlink(missing_ok=True)


def prepare_all(data, threads=0):
    """Download pinned models/cards, then validate every voice before readiness.

    This is a build/setup action. Runtime generation never invokes this function.
    Ordinary downloads avoid retaining a duplicate Hugging Face blob cache.
    """
    data = Path(data)
    aggregate = data / 'models' / 'piper.ready'
    aggregate.unlink(missing_ok=True)
    tasks = [pair for key in PIPER_MODELS for pair in model_paths(data, key)['files']]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda pair: _download_file(*pair), tasks))
    reports = []
    for key in PIPER_MODELS:
        paths = model_paths(data, key)
        paths['marker'].unlink(missing_ok=True)
        report = check_model(data, key, threads)
        temporary = paths['marker'].with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(paths['marker'])
        reports.append(report)
        print(f'Piper: {key}: {report["sample_seconds"]:.2f}s audio / {report["elapsed_seconds"]:.2f}s check', flush=True)
    result = {'revision': PIPER_REVISION, 'models': reports}
    temporary = aggregate.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(aggregate)
    return result
