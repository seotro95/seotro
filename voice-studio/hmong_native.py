"""Experimental, bounded Hmong VITS speech plus OpenVoice V2 timbre transfer.

Inference is offline and FP32. Model weights are separately pinned/verified;
availability and text validation never import Torch or download anything.
No native pronunciation, speaker similarity, or 30x speed claim is implied.
"""
from __future__ import annotations

import hashlib
import importlib.util
from importlib import metadata
import io
import json
import math
import os
from collections import OrderedDict
from pathlib import Path
import threading
from types import SimpleNamespace

from hmong_engine import EngineError, _file_fingerprint, _reference_identity
from hmong_native_models import model_directory, verify_models
from hmong_text import HmongTextError, normalize_speech_text, normalize_text
from hmong_native_vendor.vits.symbols import symbols

MAX_SECONDS = 120
SAMPLE_RATE = 22050
REFERENCE_CACHE_SIZE = 16
AUDIO_PROFILES = frozenset({'legacy-v1', 'clear-v1'})
_SYMBOL_IDS = {symbol: index for index, symbol in enumerate(symbols)}
_INPUT_SYMBOLS = frozenset(_SYMBOL_IDS) - {'_'}


def _mark_clear_audio(samples, watermark, device):
    """Add the 16 kHz marker residual without low-passing the speech itself.

    WavMark's 16,000 sample input is one second at 16 kHz, not one second
    of the native 22,050 Hz waveform. Only its small residual is resampled
    back. Fading that residual avoids a new edge at either splice.
    """
    import numpy as np
    import soxr
    import torch
    if (samples.ndim != 1 or not np.isfinite(samples).all()
            or len(samples) < SAMPLE_RATE):
        raise EngineError('Đoạn gắn dấu nhận diện âm thanh không hợp lệ.')
    original = samples[:SAMPLE_RATE]
    signal = soxr.resample(original, SAMPLE_RATE, 16000, quality='HQ')
    bits = np.unpackbits(np.frombuffer(b'SEOT', dtype=np.uint8))
    message = torch.tensor(bits, dtype=torch.float32, device=device).unsqueeze(0)
    tensor = torch.from_numpy(np.ascontiguousarray(signal, dtype=np.float32)).to(device).unsqueeze(0)
    marked = watermark.encode(tensor, message)[0].detach().cpu().numpy()
    if marked.shape != signal.shape or not np.isfinite(marked).all():
        raise EngineError('Dấu nhận diện trả âm thanh không hợp lệ.')
    residual = marked - signal
    signal_power = float(np.mean(signal.astype(np.float64) ** 2))
    residual_power = float(np.mean(residual.astype(np.float64) ** 2))
    # Fail closed on an unstable marker instead of emitting audibly damaged
    # speech or silently dropping the marker. Normal pinned-model SNR is >40 dB.
    if residual_power > max(signal_power * .01, 1e-12):
        raise EngineError('Dấu nhận diện làm thay đổi âm thanh quá mức. Hãy tạo lại đoạn này.')
    residual = soxr.resample(residual, 16000, SAMPLE_RATE, quality='HQ')
    if residual.shape != original.shape or not np.isfinite(residual).all():
        raise EngineError('Dấu nhận diện sau chuyển tần số không hợp lệ.')
    fade = round(.02 * SAMPLE_RATE)
    envelope = np.sin(np.linspace(0, np.pi / 2, fade)) ** 2
    residual[:fade] *= envelope
    residual[-fade:] *= envelope[::-1]
    if float(np.max(np.abs(residual))) > max(.05, .5 * float(np.max(np.abs(original)))):
        raise EngineError('Dấu nhận diện có đỉnh âm thanh không hợp lệ.')
    result = samples.copy()
    result[:SAMPLE_RATE] = original + residual
    if not np.isfinite(result).all():
        raise EngineError('Âm thanh sau gắn dấu nhận diện không hợp lệ.')
    return result


def runtime_settings():
    """Keep old F5 INT8 preferences from disabling the FP32 native engine."""
    device = os.getenv('HMOOB_DEVICE', 'auto').strip().lower()
    requested_precision = os.getenv('HMOOB_PRECISION', 'auto').strip().lower()
    if device not in {'auto', 'cpu', 'cuda'}:
        raise EngineError('Bộ đọc nhanh hỗ trợ HMOOB_DEVICE=auto, cpu hoặc cuda.')
    if requested_precision not in {'auto', 'fp32', 'int8'}:
        raise EngineError('Bộ đọc nhanh dùng FP32; đặt HMOOB_PRECISION=auto hoặc fp32.')
    return {'device': device, 'precision': 'fp32', 'requested_precision': requested_precision,
            'compatibility_note': ('Đã bỏ tùy chọn INT8 của F5 cũ; bộ đọc nhanh dùng FP32.'
                                   if requested_precision == 'int8' else None)}


def validate_text(text):
    """Keep RPA letters intact and treat written hyphens as word boundaries.

    The shared formatter folds Unicode dashes to ASCII ``-``, which is absent
    from this model's symbols. Keeping the boundary as a space accepts normal
    hyphenated Hmong without dropping letters or guessing another spelling.
    """
    try:
        result = normalize_speech_text(text).replace('-', ' ').lower()
        return normalize_text(result, vocabulary=_INPUT_SYMBOLS)
    except HmongTextError as exc:
        error = EngineError(str(exc))
        error.code = exc.code
        error.unsupported_characters = exc.unsupported_characters
        raise error from None


def availability():
    requested = os.getenv('HMOOB_DEVICE', 'auto').strip().lower()
    dependencies = all(importlib.util.find_spec(name) is not None for name in
                       ('torch', 'numpy', 'soundfile', 'soxr', 'scipy', 'librosa'))
    reason = None
    settings = None
    try:
        settings = runtime_settings()
        if requested == 'cuda' and metadata.version('torch').endswith('+cpu'):
            reason = 'Bộ chạy hiện tại chỉ có CPU. Mở launcher để tự chọn CPU hoặc cài bộ NVIDIA trong tools.'
        if reason is None:
            verify_models()
    except (EngineError, metadata.PackageNotFoundError) as exc:
        reason = str(exc) if isinstance(exc, EngineError) else 'Thiếu thư viện PyTorch trong bộ chạy.'
    if reason is None and not dependencies:
        reason = 'Thiếu thư viện tạo giọng. Chạy MO_VOICE_STUDIO_HMONG.bat để cài đặt.'
    return {'ready': reason is None, 'reason': reason or
            'Đủ tệp để thử VITS + OpenVoice V2; cần nghe kiểm tra tiếng Hmong và độ giống giọng.',
            'device': requested, 'model_dir': str(model_directory()), 'dependencies': dependencies,
            'dialect_verified': False, 'backend': 'vits_openvoice_v2', 'precision': 'fp32',
            'compatibility_note': settings['compatibility_note'] if settings else None,
            'quality_steps': {}, 'target_30x_verified': False}


class SpeechEngine:
    """Reuse a native model set and bounded exact reference embeddings."""

    def __init__(self):
        self._lock = threading.Lock()
        self._model = self._model_key = None
        self._reference = self._reference_key = None
        self._reference_cache = OrderedDict()
        self._progress_callback = None
        self.device = None

    def set_progress_callback(self, callback_or_none):
        if callback_or_none is not None and not callable(callback_or_none):
            raise TypeError('Progress callback must be callable or None')
        self._progress_callback = callback_or_none

    def _notify(self, message):
        if self._progress_callback is not None:
            self._progress_callback(message)

    def _load(self):
        self._notify('Đang kiểm tra mô hình đọc nhanh…')
        root = model_directory()
        integrity = verify_models(root)
        settings = runtime_settings()
        requested = settings['device']
        if settings['compatibility_note']:
            self._notify(settings['compatibility_note'])
        import torch
        device = ('cuda' if torch.cuda.is_available() else 'cpu') if requested == 'auto' else requested
        if device == 'cuda' and not torch.cuda.is_available():
            raise EngineError('Đã chọn CUDA nhưng PyTorch chưa nhận GPU. Chạy tools/install_hmong_cuda.bat hoặc chọn cpu.')
        key = (integrity, device, 'fp32')
        if self._model is not None and self._model_key == key:
            return self._model
        self._model = self._model_key = None
        self._reference = self._reference_key = None
        self._reference_cache.clear()
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        from hmong_native_vendor.vits.models import SynthesizerTrn as NativeVITS
        from hmong_native_vendor.openvoice.models import SynthesizerTrn as Converter
        from hmong_native_vendor.watermark.models.my_model import Model as Watermark
        self._notify('Đang nạp VITS Hmong và bộ chuyển giọng FP32…')
        cfg = json.loads((root / 'native-vits/config.json').read_text(encoding='utf-8'))
        cv = json.loads((root / 'openvoice-v2/config.json').read_text(encoding='utf-8'))
        if cfg['data']['sampling_rate'] != SAMPLE_RATE or cv['data']['sampling_rate'] != SAMPLE_RATE:
            raise EngineError('Tần số mô hình đọc nhanh không khớp cấu hình đã kiểm tra.')
        native = NativeVITS(len(symbols), cfg['data']['filter_length'] // 2 + 1,
                            cfg['train']['segment_size'] // cfg['data']['hop_length'],
                            n_speakers=cfg['data']['n_speakers'], **cfg['model'])
        native.load_state_dict(torch.load(root / 'native-vits/G_60000.pth',
                               map_location='cpu', weights_only=True)['model'], strict=True)
        native.eval().to(device)
        # Algebraically fuses the decoder's weight normalization, no quantization.
        native.dec.remove_weight_norm()
        converter = Converter(0, cv['data']['filter_length'] // 2 + 1,
                              n_speakers=cv['data']['n_speakers'], **cv['model'])
        converter.load_state_dict(torch.load(root / 'openvoice-v2/converter.pth',
                                  map_location='cpu', weights_only=True)['model'], strict=True)
        converter.eval().to(device)
        watermark = Watermark(16000, num_bit=32, n_fft=1000, hop_length=400, num_layers=8)
        watermark.load_state_dict(torch.load(root / 'wavmark/model.pth',
                                  map_location='cpu', weights_only=True), strict=True)
        watermark.eval().to(device)
        self._model = SimpleNamespace(native=native, converter=converter, watermark=watermark,
                                      native_config=cfg, converter_config=cv, precision='fp32',
                                      backend='vits_openvoice_v2')
        self._model_key, self.device = key, device
        return self._model

    def _spectrogram(self, samples, model):
        from hmong_native_vendor.openvoice.mel_processing import spectrogram_torch
        cfg = model.converter_config['data']
        return spectrogram_torch(samples, cfg['filter_length'], SAMPLE_RATE,
                                 cfg['hop_length'], cfg['win_length'], center=False)

    def _prepare_reference(self, path, words, model):
        path = Path(path)
        _reference_identity(path, words)  # Existing 3–8s mono PCM16 24k contract.
        identity = _file_fingerprint(path, path.stat())
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        key = (self._model_key, str(path.resolve()), identity, digest, words)
        if key in self._reference_cache:
            self._reference_cache.move_to_end(key)
            self._reference = self._reference_cache[key]
        else:
            import numpy as np
            import soundfile as sf
            import soxr
            import torch
            # Decode exactly the bytes identified above, even if the file changes.
            samples, rate = sf.read(io.BytesIO(content), dtype='float32', always_2d=True)
            samples = samples.mean(axis=1)
            if not np.isfinite(samples).all() or float(np.mean(samples ** 2)) < 1e-12:
                raise EngineError('Đoạn mẫu chỉ có im lặng hoặc dữ liệu không hợp lệ. Chọn đoạn có tiếng nói.')
            if rate != SAMPLE_RATE:
                samples = soxr.resample(samples, rate, SAMPLE_RATE, quality='HQ')
            tensor = torch.from_numpy(np.ascontiguousarray(samples)).unsqueeze(0).to(self.device)
            self._reference = model.converter.ref_enc(self._spectrogram(tensor, model).transpose(1, 2)).unsqueeze(-1)
            self._reference_cache[key] = self._reference
            if len(self._reference_cache) > REFERENCE_CACHE_SIZE:
                self._reference_cache.popitem(last=False)
        self._reference_key = key
        return self._reference

    def synthesize(self, text, reference_path, reference_text, speed=1.0, quality='fast', *,
                   audio_profile='clear-v1'):
        if not isinstance(text, str) or not text.strip() or len(text) > 400:
            raise EngineError('Mỗi đoạn tạo giọng cần 1–400 ký tự; dùng hàng đợi cho kịch bản dài.')
        if not isinstance(reference_text, str) or len(reference_text) > 2000:
            raise EngineError('Lời mẫu tùy chọn cần là văn bản, tối đa 2.000 ký tự.')
        if (isinstance(speed, bool) or not isinstance(speed, (int, float))
                or not math.isfinite(speed) or not .5 <= speed <= 2):
            raise EngineError('Tốc độ đọc cần từ 0,5 đến 2 lần.')
        if not isinstance(quality, str) or quality not in {'turbo', 'draft', 'fast', 'standard'}:
            raise EngineError('Chế độ chất lượng không hợp lệ.')
        if not isinstance(audio_profile, str) or audio_profile not in AUDIO_PROFILES:
            raise EngineError('Chế độ xử lý âm thanh không hợp lệ.')
        text = validate_text(text)
        if len(text) > 400:
            raise EngineError('Lời đọc sau khi chuyển số vượt 400 ký tự; dùng hàng đợi để chia đoạn.')
        # OpenVoice extracts speaker identity from the selected WAV, not its
        # transcript. Applying the target Hmong vocabulary here rejected valid
        # reference speakers using Vietnamese, Chinese and other languages.
        # Keep metadata unchanged and validate only the words being synthesized.
        if not any(character.isalpha() for character in text):
            raise EngineError('Nội dung cần có từ Hmong RPA, không chỉ dấu câu.')
        with self._lock:
            try:
                model = self._load()
                import numpy as np
                import torch
                from hmong_native_vendor.vits.commons import intersperse
                with torch.inference_mode():
                    self._notify('Đang chuẩn bị giọng mẫu…')
                    target = self._prepare_reference(reference_path, reference_text, model)
                    tokens = intersperse([_SYMBOL_IDS[character] for character in text], 0)
                    tensor = torch.tensor(tokens, dtype=torch.long, device=self.device).unsqueeze(0)
                    lengths = torch.tensor([len(tokens)], dtype=torch.long, device=self.device)
                    max_frames = MAX_SECONDS * SAMPLE_RATE // model.native_config['data']['hop_length']
                    self._notify('Đang đọc tiếng Hmong bằng VITS…')
                    source = model.native.infer(tensor, lengths, noise_scale=.667, noise_scale_w=.8,
                                                length_scale=1 / float(speed), max_len=max_frames)[0][:, 0]
                    if (source.ndim != 2 or not 1024 <= source.shape[-1] <= MAX_SECONDS * SAMPLE_RATE
                            or not torch.isfinite(source).all()):
                        raise EngineError('Bộ đọc trả đoạn âm thanh quá ngắn, quá dài hoặc không hợp lệ.')
                    self._notify('Đang chuyển sang giọng mẫu đã chọn…')
                    spec = self._spectrogram(source, model)
                    source_embedding = model.converter.ref_enc(spec.transpose(1, 2)).unsqueeze(-1)
                    frame_lengths = torch.tensor([spec.shape[-1]], dtype=torch.long, device=self.device)
                    audio = model.converter.voice_conversion(spec, frame_lengths, sid_src=source_embedding,
                                                               sid_tgt=target, tau=.3)[0][0, 0]
                    if not torch.isfinite(audio).all() or len(audio) < 1024:
                        raise EngineError('Bộ chuyển giọng trả âm thanh không hợp lệ.')
                    minimum = SAMPLE_RATE if audio_profile == 'clear-v1' else 16000
                    if len(audio) >= minimum:
                        self._notify('Đang thêm dấu nhận diện âm thanh tạo bằng máy…')
                        if audio_profile == 'legacy-v1':
                            # Preserve pre-upgrade checkpoint/resume semantics.
                            bits = np.unpackbits(np.frombuffer(b'SEOT', dtype=np.uint8))
                            message = torch.tensor(bits, dtype=torch.float32, device=self.device).unsqueeze(0)
                            marked = model.watermark.encode(audio[:16000].unsqueeze(0), message)[0]
                            audio[:16000] = marked
                        else:
                            samples = audio.detach().cpu().numpy().astype('float32', copy=True)
                            samples = _mark_clear_audio(samples, model.watermark, self.device)
                    else:
                        self._notify('Đoạn quá ngắn để gắn WavMark; đang hoàn tất âm thanh tạo bằng máy…')
                    if audio_profile == 'legacy-v1' or len(audio) < minimum:
                        samples = audio.detach().cpu().numpy().astype('float32', copy=True)
                if (samples.ndim != 1 or not 0 < len(samples) <= MAX_SECONDS * SAMPLE_RATE
                        or not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 1e-6):
                    raise EngineError('Âm thanh tạo ra rỗng, im lặng hoặc không hợp lệ.')
                return samples, SAMPLE_RATE
            except EngineError:
                raise
            except (ImportError, OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
                if 'out of memory' in str(exc).lower():
                    raise EngineError('Không đủ bộ nhớ tạo giọng. Chọn đoạn ngắn hơn hoặc HMOOB_DEVICE=cpu.') from None
                raise EngineError('Không tạo được giọng nhanh. Kiểm tra mô hình bằng prepare_hmong_native.py '
                                  '--verify-only; thư viện phải đúng bản requirements-hmong.txt. Chi tiết: '
                                  + str(exc)[:240]) from None
