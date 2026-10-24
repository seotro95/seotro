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
MAX_GENERATED_SECONDS = 600


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
        'device': os.getenv('HMONG_F5_DEVICE', 'cpu'),
    }


def _configuration_error(settings):
    if not all(settings[name] for name in ('checkpoint', 'vocab', 'vocoder')):
        return ('Chưa cấu hình mô hình nhân bản cục bộ. Cần HMONG_F5_CHECKPOINT, '
                'HMONG_F5_VOCAB và HMONG_F5_VOCODER trỏ tới tệp đã tải trên máy.')
    if settings['model'] != 'F5TTS_Base':
        return 'Checkpoint F5-Hmong này cần HMONG_F5_MODEL=F5TTS_Base; không dùng mô hình F5 tiếng Anh thay thế.'
    if settings['device'] not in ('cpu', 'cuda', 'mps'):
        return 'HMONG_F5_DEVICE chỉ nhận cpu, cuda hoặc mps.'
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
            frames = source.readframes(source.getnframes())
    except (OSError, EOFError, wave.Error):
        raise CloningError('Không đọc được mẫu WAV. Lưu lại đoạn mẫu trong mục Chuẩn bị mẫu.') from None
    if not 3 <= duration <= 8.001:
        raise CloningError('F5-Hmong cần mẫu dài 3–8 giây. Cắt một đoạn rõ lời và nhập bản chép khớp đúng đoạn đó.')
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
        if not 0 < len(samples) <= MAX_GENERATED_SECONDS * sample_rate:
            raise CloningError('Bản đọc rỗng hoặc vượt giới hạn 10 phút; hãy chia nhỏ kịch bản.')
        pcm = array('h')
        peak = 0.0
        for value in samples:
            value = float(value)
            if not math.isfinite(value):
                raise CloningError('Mô hình tạo âm thanh chứa mẫu không hợp lệ; chưa có bản đọc hoàn tất.')
            peak = max(peak, abs(value))
            pcm.append(round(max(-1.0, min(1.0, value)) * 32767))
        if peak < 1e-6:
            raise CloningError('Mô hình chỉ tạo im lặng; chưa có bản đọc hoàn tất. Thử mẫu và lời khác.')
    except (TypeError, ValueError, OverflowError):
        raise CloningError('Mô hình trả dạng sóng âm thanh không hợp lệ.') from None
    if sys.byteorder != 'little':
        pcm.byteswap()
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return output.getvalue()


def _load_model(settings):
    global _model, _model_key
    # File identity allows replacement in place without reusing a stale model.
    paths = [Path(settings['checkpoint']), Path(settings['vocab']),
             Path(settings['vocoder']) / 'config.yaml',
             Path(settings['vocoder']) / 'pytorch_model.bin']
    key = tuple((str(path.resolve()), path.stat().st_size, path.stat().st_mtime_ns) for path in paths)
    key += (settings['model'], settings['device'])
    if _model is None or _model_key != key:
        cache = model_directory().parent / 'cache'
        for name, subfolder in (('MPLCONFIGDIR', 'matplotlib'), ('NUMBA_CACHE_DIR', 'numba'),
                                ('XDG_CACHE_HOME', 'xdg')):
            if not os.getenv(name):
                location = cache / subfolder
                location.mkdir(parents=True, exist_ok=True)
                os.environ[name] = str(location)
        import torch
        from f5_tts.api import F5TTS
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        candidate = F5TTS(model=settings['model'], ckpt_file=settings['checkpoint'],
                          vocab_file=settings['vocab'], vocoder_local_path=settings['vocoder'],
                          device=settings['device'])
        _model, _model_key = candidate, key
    return _model


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


def synthesize(text, speed, reference_path, reference_text):
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
    reference_seconds = _validate_reference(reference_path)
    status = availability()
    if not status['ready']:
        raise CloningError(status['reason'])
    if not _lock.acquire(blocking=False):
        raise CloningError('Bộ nhân bản cục bộ đang xử lý tác vụ khác. Hãy chờ hoàn tất.')
    try:
        engine = _load_model(_settings())
        # Upstream starts one inference thread for every sentence batch. Feed it
        # one bounded call at a time to keep long paragraphs within CPU/RAM limits.
        # The margin accounts for upstream's added 50 ms and punctuation/space.
        budget = int(len(reference_text.strip().encode('utf-8')) / (reference_seconds + .1)
                     * (20 - reference_seconds) * float(speed) * .8)
        if budget < 8:
            raise CloningError('Lời mẫu quá ngắn so với âm thanh. Nhập đủ lời khớp đoạn 3–8 giây.')
        def rendered_parts():
            for batch in _batches(text.strip(), min(180, budget)):
                audio, rate, _ = engine.infer(
                    ref_file=str(reference_path), ref_text=reference_text.strip(),
                    gen_text=batch, speed=float(speed), nfe_step=32,
                    show_info=lambda *_: None, progress=None,
                )
                yield _wav(audio, rate)
        return _join_wavs(rendered_parts())
    except CloningError:
        raise
    except Exception:
        raise CloningError('Không nạp/chạy được F5-Hmong cục bộ. Kiểm tra checkpoint F5TTS_Base, '
                           'vocab đi kèm, Vocos, phiên bản thư viện và RAM. Chưa có bản đọc hoàn tất.') from None
    finally:
        _lock.release()
