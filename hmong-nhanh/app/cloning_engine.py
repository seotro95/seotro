"""Optional offline F5-Hmong reference conditioning.

Only explicit local model files are used. The community Hmong checkpoint has
not been verified for Hmong White here; configuration is not quality evidence.
See https://github.com/YangNobody12/F5-TTS-Hmong for its provenance.
"""
from __future__ import annotations

from array import array
import importlib.util
import io
import math
import os
from pathlib import Path
import re
import sys
import threading
import wave
from model_files import model_directory


class CloningError(Exception):
    """Actionable local inference failure, safe to display in the UI."""


_lock = threading.Lock()
_model = None
_model_key = None
_reference = None
_reference_key = None
_cuda_probe_key = None
_cuda_probe_result = None
MAX_GENERATED_SECONDS = 600
QUALITY_STEPS = {'draft': 4, 'fast': 8, 'balanced': 16, 'quality': 32}


def runtime_device():
    """Device actually used by this worker; None until the model has loaded."""
    return getattr(_model, 'device', None)


def _dependencies():
    return all(importlib.util.find_spec(name) is not None
               for name in ('f5_tts', 'torch', 'torchaudio', 'soundfile', 'scipy', 'vocos'))


def _settings():
    root = model_directory()
    return {
        'checkpoint': os.getenv('HMONG_F5_CHECKPOINT', str(root / 'f5-hmong' / 'model_159952.safetensors')),
        'vocab': os.getenv('HMONG_F5_VOCAB', str(root / 'f5-hmong' / 'vocab.txt')),
        'vocoder': os.getenv('HMONG_F5_VOCODER', str(root / 'vocos')),
        'model': os.getenv('HMONG_F5_MODEL', 'F5TTS_Base'),
        'device': os.getenv('HMONG_F5_DEVICE', 'auto').lower(),
    }


def _configuration_error(settings):
    if not all(settings[name] for name in ('checkpoint', 'vocab', 'vocoder')):
        return ('Chưa cấu hình mô hình nhân bản cục bộ. Cần HMONG_F5_CHECKPOINT, '
                'HMONG_F5_VOCAB và HMONG_F5_VOCODER trỏ tới tệp đã tải trên máy.')
    if settings['model'] != 'F5TTS_Base':
        return 'Checkpoint F5-Hmong này cần HMONG_F5_MODEL=F5TTS_Base; không dùng mô hình F5 tiếng Anh thay thế.'
    if settings['device'] not in ('auto', 'cpu', 'cuda', 'mps'):
        return 'HMONG_F5_DEVICE chỉ nhận auto, cpu, cuda hoặc mps.'
    checkpoint = Path(settings['checkpoint'])
    if checkpoint.suffix.lower() != '.safetensors':
        return 'Checkpoint Hmong phải ở định dạng .safetensors; không nạp checkpoint pickle tùy ý.'
    required = [checkpoint, Path(settings['vocab']),
                Path(settings['vocoder']) / 'config.yaml',
                Path(settings['vocoder']) / 'pytorch_model.bin']
    if not all(path.is_file() and path.stat().st_size > 0 for path in required):
        return ('Chưa tải đủ mô hình Hmong. Chạy MO_HMONG_NHANH.bat để cài thư viện và tải F5-Hmong/Vocos, '
                'rồi mở lại tool. Có thể dùng HMONG_F5_CHECKPOINT, HMONG_F5_VOCAB và HMONG_F5_VOCODER '
                'cho mô hình đã có trên máy.')
    return None


def availability():
    """Report prerequisites without importing/loading models or using a network."""
    settings = _settings()
    try:
        problem = _configuration_error(settings)
    except OSError:
        problem = 'Không đọc được tệp mô hình cục bộ. Kiểm tra quyền truy cập.'
    dependencies = _dependencies()
    configured = problem is None
    if not problem and not dependencies:
        problem = 'Chưa cài thư viện F5-TTS/PyTorch cho nhân bản cục bộ.'
    return {
        'backend': 'f5-hmong', 'dependencies': dependencies,
        'configured': configured, 'ready': problem is None,
        'requested_device': settings['device'],
        'device': getattr(_model, 'device', None),
        'quality_steps': QUALITY_STEPS.copy(),
        'default_quality': 'fast',
        'model_warm': _model is not None,
        'dialect_verified': False,
        'reason': problem or ('Đã có điều kiện chạy thử F5-Hmong cục bộ. Chưa kiểm chứng '
                              'phương ngữ Hmong Trắng hoặc độ giống hai giọng mẫu; cần nghe đánh giá.'),
    }


def _validate_reference(path):
    try:
        with wave.open(str(path), 'rb') as source:
            if (source.getnchannels() not in (1, 2) or source.getsampwidth() != 2
                    or source.getframerate() < 8000):
                raise CloningError('Mẫu nhân bản cần là WAV PCM 16-bit, mono hoặc stereo.')
            duration = source.getnframes() / source.getframerate()
            if not 3 <= duration <= 8.001:
                raise CloningError('F5-Hmong cần mẫu dài 3–8 giây. Cắt một đoạn rõ lời và nhập bản chép khớp đúng đoạn đó.')
            frames = source.readframes(source.getnframes())
    except (OSError, EOFError, wave.Error):
        raise CloningError('Không đọc được mẫu WAV. Lưu lại đoạn mẫu trong mục Chuẩn bị mẫu.') from None
    samples = array('h', frames)
    if sys.byteorder != 'little':
        samples.byteswap()
    if not samples or max(abs(sample) for sample in samples) < 32:
        raise CloningError('Đoạn mẫu gần như im lặng. Chọn đoạn có tiếng nói rõ và lưu lại lời tương ứng.')
    return duration


def _wav(samples, sample_rate):
    """Validate the actual generated waveform, then write mono PCM 16-bit."""
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 96000:
        raise CloningError('Mô hình trả tần số lấy mẫu không hợp lệ.')
    try:
        import numpy as np
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim != 1 or not 0 < samples.size <= MAX_GENERATED_SECONDS * sample_rate:
            raise CloningError('Bản đọc rỗng hoặc vượt giới hạn 10 phút; hãy chia nhỏ kịch bản.')
        if not np.isfinite(samples).all():
            raise CloningError('Mô hình tạo âm thanh chứa mẫu không hợp lệ; chưa có bản đọc hoàn tất.')
        if float(np.max(np.abs(samples))) < 1e-6:
            raise CloningError('Mô hình chỉ tạo im lặng; chưa có bản đọc hoàn tất. Thử mẫu và lời khác.')
        pcm = np.rint(np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
    except (TypeError, ValueError, OverflowError):
        raise CloningError('Mô hình trả dạng sóng âm thanh không hợp lệ.') from None
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return output.getvalue()


def _cuda_usable(torch):
    """A visible GPU is not proof that this PyTorch build can run its kernels."""
    global _cuda_probe_key, _cuda_probe_result
    key = (torch, str(torch.__version__), os.getenv('CUDA_VISIBLE_DEVICES'))
    if _cuda_probe_key == key:
        return _cuda_probe_result
    reason = ''
    try:
        if not torch.cuda.is_available():
            reason = 'PyTorch chưa dùng được CUDA. Kiểm tra driver NVIDIA hoặc chọn chế độ auto/cpu.'
        elif (torch.cuda.get_device_capability(0)[0] >= 10
              and str(torch.__version__).split('+')[0].startswith('2.6.')):
            reason = 'GPU Blackwell chưa tương thích với PyTorch 2.6; cần bộ PyTorch/CUDA hỗ trợ GPU này hoặc chọn auto/cpu.'
        else:
            # Cache the completed operation. Availability alone can be True for
            # a GPU whose architecture is unsupported by the installed wheel.
            torch.zeros(1, device='cuda').add_(1).item()
    except Exception:
        reason = 'PyTorch thấy GPU nhưng chưa chạy được CUDA. Kiểm tra driver và bản PyTorch hỗ trợ GPU này, hoặc chọn auto/cpu.'
    _cuda_probe_key, _cuda_probe_result = key, (not reason, reason)
    return _cuda_probe_result


def _resolve_device(requested, torch):
    if requested == 'cpu':
        return 'cpu'
    cuda, cuda_reason = _cuda_usable(torch)
    mps = bool(getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available())
    if requested == 'auto':
        return 'cuda' if cuda else 'mps' if mps else 'cpu'
    if requested == 'cuda' and not cuda:
        raise CloningError(cuda_reason)
    if requested == 'mps' and not mps:
        raise CloningError('Máy này chưa dùng được MPS. Chọn chế độ auto/cpu.')
    if requested not in ('cpu', 'cuda', 'mps'):
        raise CloningError('Thiết bị tạo giọng không hợp lệ.')
    return requested


def _load_model(settings):
    global _model, _model_key, _reference, _reference_key
    import torch
    device = _resolve_device(settings['device'], torch)
    # File identity allows replacement in place without reusing a stale model.
    paths = [Path(settings['checkpoint']), Path(settings['vocab']),
             Path(settings['vocoder']) / 'config.yaml',
             Path(settings['vocoder']) / 'pytorch_model.bin']
    key = tuple((str(path.resolve()), path.stat().st_size, path.stat().st_mtime_ns) for path in paths)
    key += (settings['model'], device)
    if _model is None or _model_key != key:
        cache = model_directory().parent / 'cache'
        for name, subfolder in (('MPLCONFIGDIR', 'matplotlib'), ('NUMBA_CACHE_DIR', 'numba'),
                                ('XDG_CACHE_HOME', 'xdg')):
            if not os.getenv(name):
                location = cache / subfolder
                location.mkdir(parents=True, exist_ok=True)
                os.environ[name] = str(location)
        from f5_tts.api import F5TTS
        try:
            threads = int(os.getenv('HMONG_CPU_THREADS', '4'))
        except ValueError:
            threads = 4
        torch.set_num_threads(max(1, min(threads, os.cpu_count() or 1)))
        candidate = F5TTS(model=settings['model'], ckpt_file=settings['checkpoint'],
                          vocab_file=settings['vocab'], vocoder_local_path=settings['vocoder'],
                          device=device)
        # F5 1.1.22 selects fp16 on supported CUDA devices and fp32 on CPU/MPS.
        # Keep its tested dtype selection; no costly compile on first generation.
        _model, _model_key = candidate, key
        _reference = _reference_key = None
    return _model


def _reference_identity(path, text):
    try:
        path = Path(path)
        stat = path.stat()
        return (str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, text)
    except OSError:
        raise CloningError('Không đọc được mẫu WAV. Lưu lại đoạn mẫu trước khi tạo giọng.') from None


class _ConditionedModel:
    """Reuse the exact reference mel instead of encoding it for every chunk."""
    def __init__(self, model, mel):
        self.model = model
        self.mel = mel

    def sample(self, *, cond, **options):
        return self.model.sample(cond=self.mel, **options)


def _prepare_reference(engine, path, text, identity):
    global _reference, _reference_key
    key = (_model_key, identity, engine.device)
    if _reference is not None and _reference_key == key:
        return _reference
    import soundfile as sf
    import torch
    import torchaudio
    samples, rate = sf.read(str(path), dtype='float32', always_2d=True)
    audio = torch.from_numpy(samples.mean(axis=1, keepdims=True).T.copy())
    if rate != 24000:
        audio = torchaudio.functional.resample(audio, rate, 24000)
        rate = 24000
    if not torch.isfinite(audio).all():
        raise CloningError('Mẫu giọng chứa dữ liệu không hợp lệ.')
    audio = audio.to(engine.device)
    with torch.inference_mode():
        rms = torch.sqrt(torch.mean(audio.square()))
        if float(rms) < 1e-6:
            raise CloningError('Đoạn mẫu gần như im lặng.')
        # Mirror infer_batch_process target_rms exactly. Keep the unscaled input
        # so that upstream restores the original volume after vocoding.
        conditioned = audio * (.1 / rms) if float(rms) < .1 else audio
        mel = engine.ema_model.mel_spec(conditioned).permute(0, 2, 1)
    normalized_text = text.strip()
    if not normalized_text.endswith(('.', '!', '?', '。')):
        normalized_text += '.'
    normalized_text += ' '
    _reference = {'audio': (audio, rate), 'text': normalized_text,
                  'seconds': audio.shape[-1] / rate,
                  'conditioned_model': _ConditionedModel(engine.ema_model, mel)}
    _reference_key = key
    return _reference


def _infer_one(engine, reference, text, speed, steps):
    import torch
    from f5_tts.infer.utils_infer import infer_batch_process
    # Supplying one batch prevents upstream's ThreadPool from running concurrent
    # model calls. All text and reference values stay local; no ASR or downloads.
    with torch.inference_mode():
        audio, rate, _ = next(infer_batch_process(
            reference['audio'], reference['text'], [text],
            reference['conditioned_model'], engine.vocoder,
            mel_spec_type=engine.mel_spec_type, progress=None,
            nfe_step=steps, speed=float(speed), device=engine.device,
            cross_fade_duration=0,
        ))
    return _wav(audio, rate)


def _batches(text, byte_limit):
    """Bound each call without dropping words, even when a paragraph has no full stop."""
    pending = ''
    for token in re.findall(r'\S+\s*', text):
        if pending and len((pending + token).encode('utf-8')) > byte_limit:
            if pending.strip():
                yield pending.strip()
            pending = ''
        for character in token:
            if pending and len((pending + character).encode('utf-8')) > byte_limit:
                if pending.strip():
                    yield pending.strip()
                pending = ''
            pending += character
    if pending.strip():
        yield pending.strip()


def _join_wavs(parts):
    rate = None
    frames = []
    count = 0
    for part in parts:
        with wave.open(io.BytesIO(part), 'rb') as source:
            if rate is None:
                rate = source.getframerate()
            if source.getframerate() != rate:
                raise CloningError('Tần số âm thanh thay đổi giữa các đoạn; chưa có bản đọc hoàn tất.')
            count += source.getnframes()
            if count > MAX_GENERATED_SECONDS * rate:
                raise CloningError('Bản đọc vượt giới hạn 10 phút; hãy chia nhỏ kịch bản.')
            frames.append(source.readframes(source.getnframes()))
    if not rate or not count:
        raise CloningError('Mô hình trả bản đọc rỗng.')
    output = io.BytesIO()
    with wave.open(output, 'wb') as destination:
        destination.setnchannels(1)
        destination.setsampwidth(2)
        destination.setframerate(rate)
        for block in frames:
            destination.writeframesraw(block)
    return output.getvalue()


def synthesize(text, speed, reference_path, reference_text, quality='fast'):
    """Generate with local F5 files and an explicitly transcribed 3–8s WAV.

    This API never requests automatic ASR, cloud synthesis, or model downloads.
    A configured model still requires native evaluation for dialect and quality.
    """
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise CloningError('Nhân bản cục bộ nhận 1–2.000 ký tự mỗi lượt; hãy chia nhỏ kịch bản dài.')
    if not isinstance(reference_text, str) or not reference_text.strip() or len(reference_text) > 2000:
        raise CloningError('Nhập bản chép Hmong khớp chính xác đoạn mẫu 3–8 giây; không tự đoán lời mẫu.')
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not math.isfinite(speed) or not 0.5 <= speed <= 2:
        raise CloningError('Tốc độ đọc phải từ 0,5 đến 2 lần.')
    if not isinstance(quality, str) or quality not in QUALITY_STEPS:
        raise CloningError('Chọn chất lượng draft, fast, balanced hoặc quality.')
    identity = _reference_identity(reference_path, reference_text.strip())
    if _reference_key is None or _reference_key[1] != identity:
        _validate_reference(reference_path)
    status = availability()
    if not status['ready']:
        raise CloningError(status['reason'])
    if not _lock.acquire(blocking=False):
        raise CloningError('Bộ nhân bản cục bộ đang xử lý tác vụ khác. Hãy chờ hoàn tất.')
    try:
        engine = _load_model(_settings())
        reference = _prepare_reference(engine, reference_path, reference_text, identity)
        reference_seconds = reference['seconds']
        budget = int(len(reference['text'].encode('utf-8')) / reference_seconds
                     * (20 - reference_seconds) * float(speed) * .8)
        if budget < 8:
            raise CloningError('Lời mẫu quá ngắn so với âm thanh. Nhập đủ lời khớp đoạn 3–8 giây.')
        def rendered_parts():
            for batch in _batches(text.strip(), min(350, budget)):
                yield _infer_one(engine, reference, batch, speed, QUALITY_STEPS[quality])
        return _join_wavs(rendered_parts())
    except CloningError:
        raise
    except Exception:
        raise CloningError('Không nạp/chạy được F5-Hmong cục bộ. Kiểm tra checkpoint F5TTS_Base, '
                           'vocab đi kèm, Vocos, phiên bản thư viện và RAM. Chưa có bản đọc hoàn tất.') from None
    finally:
        _lock.release()
