"""Offline White Hmong reference-voice inference with the pinned CosyVoice3 model.

Only a verified local snapshot is loaded.  Reference audio conditions instruct2;
it is not a transcript or a newly trained voice.  Dialect/voice quality still
needs a native listener.  Run this module inside the cancellable voice worker.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import logging
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import wave

REPOSITORY = 'Xuajpaj2026/hmong-tts-weights'
REVISION = '5663e0df2589c2ca2403cd327a52702c3ff96e8f'
MODEL_FOLDER = 'Fun-CosyVoice3-0.5B-hmong'
MARKER = '.hmong-model-ready.json'
DEPENDENCIES = ('torch', 'torchaudio', 'numpy', 'soundfile', 'yaml', 'hyperpyyaml',
                'onnxruntime', 'whisper', 'inflect', 'transformers', 'diffusers',
                'omegaconf', 'conformer', 'einops', 'x_transformers', 'librosa',
                'scipy', 'tiktoken')
STYLES = {
    'neutral': 'Speak naturally and clearly.',
    'review': 'Use a friendly, conversational product review style. Emphasize the main points clearly.',
    'storytelling': 'Tell the story expressively, with natural pauses and changes of intonation.',
    'warm': 'Use a warm, gentle and friendly voice.',
    'cheerful': 'Speak happily with a bright and cheerful voice.',
    'sad': 'Speak sadly with a subdued voice and gentle pauses.',
    'advertising': 'Use an energetic, enthusiastic advertising style with clear emphasis.',
    'news': 'Use a clear, composed newsreader style with steady pacing.',
    'meditation': 'Use a very soft, calm and soothing voice with relaxed pauses.',
}
_CONFIG_KEYS = {'sample_rate', 'llm_input_size', 'llm_output_size', 'spk_embed_dim',
                'qwen_pretrain_path', 'token_frame_rate', 'token_mel_ratio',
                'chunk_size', 'num_decoding_left_chunks', 'llm', 'flow', 'hift',
                'get_tokenizer', 'feat_extractor', 'allowed_special'}
_CONFIG_TAGS = {
    '!ref',
    '!new:cosyvoice.llm.llm.CosyVoice3LM',
    '!new:cosyvoice.llm.llm.Qwen2Encoder',
    '!name:cosyvoice.utils.common.ras_sampling',
    '!new:cosyvoice.flow.flow.CausalMaskedDiffWithDiT',
    '!new:cosyvoice.transformer.upsample_encoder.PreLookaheadLayer',
    '!new:cosyvoice.flow.flow_matching.CausalConditionalCFM',
    '!new:omegaconf.DictConfig',
    '!new:cosyvoice.flow.DiT.dit.DiT',
    '!new:cosyvoice.hifigan.generator.CausalHiFTGenerator',
    '!new:cosyvoice.hifigan.f0_predictor.CausalConvRNNF0Predictor',
    '!name:cosyvoice.tokenizer.tokenizer.get_qwen_tokenizer',
    '!name:matcha.utils.audio.mel_spectrogram',
}
_REQUIRED_FILES = (
    'CosyVoice/cosyvoice/cli/frontend.py', 'CosyVoice/cosyvoice/cli/model.py',
    'CosyVoice/cosyvoice/llm/llm.py',
    'CosyVoice/third_party/Matcha-TTS/matcha/utils/audio.py',
    *(f'{MODEL_FOLDER}/{name}' for name in ('cosyvoice3.yaml', 'llm.pt', 'flow.pt',
        'hift.pt', 'campplus.onnx', 'speech_tokenizer_v3.onnx',
        'CosyVoice-BlankEN/config.json', 'CosyVoice-BlankEN/model.safetensors',
        'CosyVoice-BlankEN/tokenizer_config.json', 'CosyVoice-BlankEN/vocab.json',
        'CosyVoice-BlankEN/merges.txt')),
)
_lock = threading.Lock()
_engine = None
_verified = None


class EngineError(Exception):
    pass


def model_dir():
    """Snapshot root, shared with prepare_clone_model.py (not weights subdir)."""
    return Path(os.getenv('HMONG_COSY_DIR') or
                Path(__file__).resolve().parent / '.data' / 'models' / 'hmong-cosy').expanduser().resolve()


def _manifest(root):
    try:
        info = json.loads((root / MARKER).read_text(encoding='utf-8'))
        if info.get('repository') != REPOSITORY or info.get('revision') != REVISION:
            raise ValueError('wrong snapshot')
        entries = info['files']
        if not isinstance(entries, list) or not entries:
            raise ValueError('empty manifest')
        seen = set()
        for item in entries:
            relative = item['path']
            path = root / relative
            if (not isinstance(relative, str) or not relative or '\\' in relative
                    or Path(relative).is_absolute() or '..' in Path(relative).parts
                    or not path.resolve().is_relative_to(root)
                    or relative in seen or not isinstance(item['size'], int)
                    or item['size'] < 0 or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
                    or not path.is_file() or path.stat().st_size != item['size']):
                raise ValueError('invalid or incomplete manifest')
            seen.add(relative)
        if not set(_REQUIRED_FILES).issubset(seen):
            raise ValueError('missing inference files')
        return entries
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise EngineError('Chưa tải đủ hoặc chưa xác minh mô hình Hmong. Chạy bộ cài mô hình cục bộ rồi khởi động lại tool.') from exc


def availability():
    missing = []
    for name in DEPENDENCIES:
        try:
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        except (ImportError, ValueError):
            missing.append(name)
    root = model_dir()
    reason = ''
    try:
        _manifest(root)
        prepared = True
    except EngineError as exc:
        prepared, reason = False, str(exc)
    ffmpeg = bool(shutil.which('ffmpeg'))
    if missing:
        reason = 'Thiếu thư viện nhân bản cục bộ. Chạy install_clone_ai.bat rồi mở lại tool.'
    elif not ffmpeg:
        reason = 'Chưa có FFmpeg trong PATH. Chạy bộ cài AI rồi mở lại tool.'
    return {'dependencies': not missing, 'missing_dependencies': missing, 'ffmpeg': ffmpeg,
            'model_ready': prepared, 'ready': not missing and ffmpeg and prepared,
            'model_dir': str(root), 'repository': REPOSITORY, 'revision': REVISION,
            'loaded': _engine is not None and _engine[0] == root,
            'styles': list(STYLES), 'reason': reason,
            'quality_verified': False, 'reference_transcript_required': False}


def _verify_snapshot(root):
    """Hash once before executing code/loading weights; status checks use sizes."""
    global _verified
    entries = _manifest(root)
    signature = (str(root), (root / MARKER).stat().st_mtime_ns,
                 tuple((item['path'], (root / item['path']).stat().st_mtime_ns,
                        item['size']) for item in entries))
    if signature == _verified:
        return
    for item in entries:
        digest = hashlib.sha256()
        with (root / item['path']).open('rb') as stream:
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != item['sha256']:
            raise EngineError('Tệp mô hình hoặc mã CosyVoice đã thay đổi/sai mã kiểm tra. Chạy lại bộ tải để xác minh; chưa dùng tệp này tạo voice.')
    _verified = signature


def _inference_config(path):
    """Select syntax nodes before tagged YAML constructors can run.

    Training/data-pipeline modules are deliberately excluded. SafeLoader.compose
    does not construct Python objects, including unknown !new/!apply tags.
    """
    import yaml
    document = yaml.compose(path.read_text(encoding='utf-8'), Loader=yaml.SafeLoader)
    if not isinstance(document, yaml.MappingNode):
        raise EngineError('Cấu hình mô hình không hợp lệ.')
    document.value = [(key, value) for key, value in document.value if key.value in _CONFIG_KEYS]
    if {key.value for key, _ in document.value} != _CONFIG_KEYS:
        raise EngineError('Cấu hình thiếu thành phần suy luận CosyVoice3.')

    def check(node):
        if not (node.tag.startswith('tag:yaml.org,2002:') or node.tag in _CONFIG_TAGS):
            raise EngineError('Cấu hình mô hình chứa thành phần chưa được kiểm tra.')
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                check(key)
                check(value)
        elif isinstance(node, yaml.SequenceNode):
            for child in node.value:
                check(child)
    check(document)
    return yaml.serialize(document)


def _bootstrap_sources(root):
    source = root / 'CosyVoice'
    matcha = source / 'third_party' / 'Matcha-TTS'
    sys.path[:0] = [str(source), str(matcha)]
    # Matcha's package initializer imports unrelated training frameworks. Use
    # its real audio/flow modules, with a standard single-process logger.
    utilities = types.ModuleType('matcha.utils')
    utilities.__path__ = [str(matcha / 'matcha' / 'utils')]
    utilities.__package__ = 'matcha.utils'
    pylogger = types.ModuleType('matcha.utils.pylogger')
    pylogger.get_pylogger = logging.getLogger
    utilities.get_pylogger = logging.getLogger
    sys.modules['matcha.utils'] = utilities
    sys.modules['matcha.utils.pylogger'] = pylogger
    # Hmong RPA must not pass through English/Chinese normalization or download
    # their FST models. Inference always passes text_frontend=False equivalent.
    class IdentityNormalizer:
        def __init__(self, *args, **kwargs):
            pass

        def normalize(self, text):
            return text
    normalizer = types.ModuleType('wetext')
    normalizer.Normalizer = IdentityNormalizer
    sys.modules['wetext'] = normalizer
    sys.modules['wetext.wetext'] = normalizer


def _weights(path, torch):
    state = torch.load(str(path), map_location='cpu', weights_only=True)
    if not isinstance(state, dict):
        raise EngineError('Trọng số không phải bảng tensor hợp lệ.')
    # The author's fine-tune includes primitive training counters. Discard them
    # in memory only, never rewrite the verified checkpoint.
    state = dict(state)
    for key in ('epoch', 'step'):
        if key in state:
            value = state.pop(key)
            if not isinstance(value, (int, float, torch.Tensor)):
                raise EngineError('Metadata trọng số không hợp lệ.')
    if not state or any(not isinstance(key, str) or not isinstance(value, torch.Tensor)
                        for key, value in state.items()):
        raise EngineError('Trọng số chứa thành phần không phải tensor đã kiểm tra.')
    return state


def _load_engine(root):
    global _engine
    if _engine is not None and _engine[0] == root:
        return _engine[1:]
    _verify_snapshot(root)
    for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_DATASETS_OFFLINE', 'MODELSCOPE_OFFLINE'):
        os.environ[name] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ.setdefault('HF_HOME', str(Path(__file__).resolve().parent / '.data' / 'cache' / 'huggingface'))
    # onnx_path is a training-only global hook in the upstream source.
    os.environ.pop('onnx_path', None)
    _bootstrap_sources(root)
    import numpy as np
    import torch
    import torchaudio
    import soundfile as sf
    from hyperpyyaml import load_hyperpyyaml

    # Avoid torchcodec and preserve offline WAV support on Windows.
    def load_audio(uri, *args, **kwargs):
        samples, rate = sf.read(str(uri), dtype='float32', always_2d=True)
        return torch.from_numpy(samples.T.copy()), int(rate)
    torchaudio.load = load_audio
    try:
        threads = int(os.getenv('HMONG_COSY_THREADS', '4'))
    except ValueError as exc:
        raise EngineError('HMONG_COSY_THREADS phải là số nguyên từ 1 đến 16.') from exc
    if not 1 <= threads <= 16:
        raise EngineError('HMONG_COSY_THREADS phải nằm trong khoảng 1 đến 16.')
    torch.set_num_threads(max(1, min(threads, os.cpu_count() or 1)))
    random.seed(1986)
    np.random.seed(1986)
    torch.manual_seed(1986)
    weights_dir = root / MODEL_FOLDER
    configuration = _inference_config(weights_dir / 'cosyvoice3.yaml')
    configs = load_hyperpyyaml(configuration, overrides={
        'qwen_pretrain_path': str(weights_dir / 'CosyVoice-BlankEN')})
    from cosyvoice.cli.frontend import CosyVoiceFrontEnd
    from cosyvoice.cli.model import CosyVoice3Model
    frontend = CosyVoiceFrontEnd(configs['get_tokenizer'], configs['feat_extractor'],
        str(weights_dir / 'campplus.onnx'), str(weights_dir / 'speech_tokenizer_v3.onnx'),
        '', configs['allowed_special'])
    backend = CosyVoice3Model(configs['llm'], configs['flow'], configs['hift'], fp16=False)
    backend.llm.load_state_dict(_weights(weights_dir / 'llm.pt', torch), strict=True)
    backend.flow.load_state_dict(_weights(weights_dir / 'flow.pt', torch), strict=True)
    hift = {key.removeprefix('generator.'): value
            for key, value in _weights(weights_dir / 'hift.pt', torch).items()}
    backend.hift.load_state_dict(hift, strict=True)
    for module in (backend.llm, backend.flow, backend.hift):
        module.float().to(backend.device).eval()
    rate = int(configs['sample_rate'])
    if rate != 24000:
        raise EngineError('Tần số mô hình khác cấu hình Hmong đã kiểm tra.')
    _engine = (root, frontend, backend, rate)
    return frontend, backend, rate


def _decode_reference(reference_path, output_path):
    import numpy as np
    reference = Path(reference_path).expanduser().resolve()
    if not reference.is_file() or reference.stat().st_size > 200 * 1024 * 1024:
        raise EngineError('Không tìm thấy mẫu giọng cục bộ hợp lệ (tối đa 200 MB).')
    try:
        result = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist',
            'file,pipe', '-i', str(reference), '-t', '10', '-vn', '-ac', '1', '-ar', '24000',
            '-f', 'f32le', 'pipe:1'], capture_output=True, timeout=45, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise EngineError('Không giải mã được mẫu giọng. Hãy chọn MP3/WAV có lời nói rõ.') from exc
    samples = np.frombuffer(result.stdout, dtype='<f4').copy()
    if (samples.size < 24000 or samples.size > 10 * 24000 or not np.isfinite(samples).all()
            or float(np.max(np.abs(samples))) < 1e-5):
        raise EngineError('Mẫu giọng phải có ít nhất 1 giây âm thanh rõ. Bộ máy dùng tối đa 10 giây đầu, không cần bản chép.')
    peak = float(np.max(np.abs(samples)))
    if peak > .98:
        samples *= .98 / peak
    Path(output_path).write_bytes(_wav(samples, 24000))


def _wav(samples, rate):
    import numpy as np
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if (not samples.size or not np.isfinite(samples).all()
            or float(np.max(np.abs(samples))) < 1e-6):
        raise EngineError('Mô hình trả âm thanh rỗng, im lặng hoặc không hợp lệ; chưa tạo voice hoàn tất.')
    peak = float(np.max(np.abs(samples)))
    if peak > .99:
        samples = samples * (.99 / peak)
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes((samples * 32767).astype('<i2').tobytes())
    return buffer.getvalue()


def _sentences(text):
    for sentence in re.split(r'(?<=[.!?;])\s+|\n+', text.strip()):
        words = sentence.split()
        while words:
            chunk = []
            while words and (not chunk or len(' '.join(chunk + words[:1])) <= 220):
                chunk.append(words.pop(0))
            yield ' '.join(chunk)


def synthesize(text, reference_path, emotion='neutral', speed=1.0):
    """Return real PCM WAV bytes; no service calls, transcript or training."""
    text = str(text).strip()
    if not text or len(text) > 2000:
        raise EngineError('Nhập từ 1 đến 2.000 ký tự mỗi lượt tạo voice cục bộ.')
    if emotion not in STYLES:
        raise EngineError('Cách đọc đã chọn chưa được bộ máy Hmong hỗ trợ.')
    if not isinstance(speed, (int, float)) or not math.isfinite(speed) or not .5 <= speed <= 2:
        raise EngineError('Tốc độ đọc phải nằm trong khoảng 0,5 đến 2,0.')
    status = availability()
    if not status['ready']:
        raise EngineError(status['reason'])
    if not _lock.acquire(blocking=False):
        raise EngineError('Bộ máy nhân bản đang tạo voice khác. Chờ hoàn tất hoặc bấm Dừng.')
    try:
        import numpy as np
        import torch
        root = model_dir()
        with tempfile.TemporaryDirectory(prefix='hmong-reference-') as folder:
            prepared = Path(folder) / 'reference.wav'
            _decode_reference(reference_path, prepared)
            frontend, backend, rate = _load_engine(root)
            instruct = ('You are a helpful assistant. Please speak Hmong (White Hmong RPA). '
                        + STYLES[emotion] + '<|endofprompt|>')
            sounds = []
            total = 0
            with torch.inference_mode():
                for sentence in _sentences(text):
                    # Same instruct2 data flow as upstream inference_instruct2,
                    # without logging the user's script. No reference transcript.
                    inputs = frontend.frontend_instruct2(sentence, instruct, str(prepared), rate, '')
                    for output in backend.tts(**inputs, stream=False, speed=float(speed)):
                        sound = output['tts_speech'].detach().cpu().float().numpy().reshape(-1)
                        if not sound.size or not np.isfinite(sound).all():
                            raise EngineError('Mô hình tạo đoạn voice không hợp lệ. Thử lời đọc ngắn hơn.')
                        total += sound.size
                        if total > rate * 15 * 60:
                            raise EngineError('Bản đọc vượt giới hạn 15 phút mỗi lượt; hãy chia kịch bản nhỏ hơn.')
                        sounds.append(sound)
                    sounds.append(np.zeros(int(rate * .15), dtype=np.float32))
            return _wav(np.concatenate(sounds) if sounds else [], rate)
    except EngineError:
        raise
    except (ImportError, ModuleNotFoundError) as exc:
        raise EngineError('Thiếu hoặc không nạp được thư viện nhân bản cục bộ: '
                          + str(getattr(exc, 'name', '') or type(exc).__name__)
                          + '. Chạy lại install_clone_ai.bat rồi khởi động lại tool.') from exc
    except Exception as exc:
        raise EngineError('Không nạp/chạy được mô hình nhân bản Hmong (' + type(exc).__name__
                          + '). Kiểm tra nhật ký cục bộ, RAM và bộ cài AI; chưa có voice hoàn tất.') from exc
    finally:
        _lock.release()
