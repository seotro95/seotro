"""Bounded, offline F5-Hmong inference for Hmoob VoiceLab.

The community checkpoint is experimental. Having model files is not evidence
that Hmong White pronunciation or similarity to a reference has been verified.
No model, ASR model, or vocabulary is downloaded by this module.
"""
from __future__ import annotations

import hashlib
import importlib.util
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import threading
import wave

from hmong_text import HmongTextError, iter_batches, normalize_text


BASE = Path(__file__).resolve().parent
QUALITY_STEPS = {"turbo": 4, "draft": 8, "fast": 16, "standard": 32}
MODEL_FILES = (
    "f5-hmong/model_159952.safetensors",
    "f5-hmong/vocab.txt",
    "vocos/config.yaml",
    "vocos/pytorch_model.bin",
)
_integrity_cache = {}
_integrity_lock = threading.Lock()


class EngineError(RuntimeError):
    """An actionable inference failure safe to show in the interface."""


def model_directory():
    data = Path(os.getenv("VOICE_STUDIO_DATA_DIR", os.getenv("HMOOB_DATA_DIR", str(BASE / ".data-hmong"))))
    return Path(os.getenv("HMOOB_MODEL_DIR", str(data / "models"))).expanduser().resolve()


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _windows_file_information():
    import ctypes
    from ctypes import wintypes

    class FileBasicInfo(ctypes.Structure):
        _fields_ = [(name, ctypes.c_longlong) for name in
                    ("CreationTime", "LastAccessTime", "LastWriteTime", "ChangeTime")]
        _fields_.append(("FileAttributes", wintypes.DWORD))

    query = ctypes.WinDLL("kernel32", use_last_error=True).GetFileInformationByHandleEx
    query.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
    query.restype = wintypes.BOOL
    return query, FileBasicInfo


def _file_fingerprint(path, stat):
    change_time = stat.st_ctime_ns
    if os.name == "nt":
        # Windows st_ctime is creation time, so it cannot invalidate a cache
        # after an overwrite whose last-write time has been restored.
        change_time = None
        try:
            import ctypes
            import msvcrt
            query, info_type = _windows_file_information()
            info = info_type()
            with path.open("rb") as handle:
                if (query(msvcrt.get_osfhandle(handle.fileno()), 0, ctypes.byref(info), ctypes.sizeof(info))
                        and info.ChangeTime > 0):
                    change_time = info.ChangeTime
        except (AttributeError, ImportError, OSError, ValueError):
            pass
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, change_time


def verify_models(root=None):
    """Verify all files once per filesystem identity; never trust size alone."""
    root = Path(root) if root is not None else model_directory()
    try:
        manifest_path = root / "verified-models.json"
        manifest_stat = manifest_path.stat()
        if manifest_stat.st_size > 100_000:
            raise ValueError("manifest too large")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = manifest["files"]
        manifest_identity = _file_fingerprint(manifest_path, manifest_stat)
        fingerprint = [(str(root.resolve()), *manifest_identity)]
        cacheable = manifest_identity[-1] is not None
        for relative in MODEL_FILES:
            path = root / relative
            record = records[relative]
            expected = record["sha256"]
            if (not isinstance(expected, str) or len(expected) != 64
                    or any(ch not in "0123456789abcdef" for ch in expected)):
                raise ValueError("invalid hash")
            stat = path.stat()
            if not path.is_file() or stat.st_size != record["size"] or stat.st_size <= 0:
                raise ValueError("file size")
            identity = _file_fingerprint(path, stat)
            cacheable = cacheable and identity[-1] is not None
            fingerprint.append((relative, *identity, expected))
        key = tuple(fingerprint)
        with _integrity_lock:
            if cacheable and key in _integrity_cache:
                return key
            for relative in MODEL_FILES:
                if _sha256(root / relative) != records[relative]["sha256"]:
                    raise ValueError("checksum mismatch")
            _integrity_cache.clear()
            if cacheable:
                _integrity_cache[key] = True
        return key
    except (OSError, ValueError, KeyError, TypeError):
        raise EngineError("Thiếu mô hình hoặc kiểm tra SHA-256 không đạt. Chạy MO_VOICE_STUDIO_HMONG.bat "
                          "hoặc python prepare_hmong.py bằng mạng được phép; không dùng tệp chưa xác minh.") from None


def availability():
    """Return prerequisites without importing PyTorch or making network calls."""
    root = model_directory()
    requested = os.getenv("HMOOB_DEVICE", "auto").lower()
    dependencies = all(importlib.util.find_spec(name) is not None
                       for name in ("torch", "torchaudio", "f5_tts", "numpy"))
    reason = None
    if requested not in ("auto", "cpu", "cuda", "mps"):
        reason = "HMOOB_DEVICE chỉ nhận auto, cpu, cuda hoặc mps."
    else:
        try:
            verify_models(root)
        except EngineError as exc:
            reason = str(exc)
    if reason is None and not dependencies:
        reason = "Chưa cài thư viện tạo giọng. Chạy MO_VOICE_STUDIO_HMONG.bat hoặc cài requirements-hmong.txt."
    return {
        "ready": reason is None,
        "reason": reason or "Đủ tệp và thư viện để chạy thử F5-Hmong; cần nghe kiểm tra phát âm và độ giống giọng.",
        "device": requested,
        "model_dir": str(root),
        "dependencies": dependencies,
        "dialect_verified": False,
        "quality_steps": QUALITY_STEPS.copy(),
    }


def _reference_identity(path, reference_text):
    path = Path(path)
    try:
        with wave.open(str(path), "rb") as handle:
            if (handle.getnchannels() != 1 or handle.getsampwidth() != 2
                    or handle.getframerate() != 24000):
                raise EngineError("Đoạn mẫu cần là WAV mono PCM 16-bit, 24.000 Hz.")
            seconds = handle.getnframes() / handle.getframerate()
            if not 3 <= seconds <= 8.001:
                raise EngineError("Chọn một đoạn giọng mẫu rõ lời dài 3–8 giây.")
        stat = path.stat()
        return (str(path.resolve()), stat.st_size, stat.st_mtime_ns, reference_text)
    except (OSError, wave.Error, EOFError):
        raise EngineError("Không đọc được đoạn WAV mẫu. Kiểm tra FFmpeg và chọn lại đoạn mẫu.") from None


class SpeechEngine:
    """One loaded model and one cached reference tensor, reused across chunks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._model_key = None
        self._reference = None
        self._reference_key = None
        self._progress_callback = None
        self.device = None

    def set_progress_callback(self, callback_or_none):
        if callback_or_none is not None and not callable(callback_or_none):
            raise TypeError("Progress callback must be callable or None")
        self._progress_callback = callback_or_none

    def _notify(self, message):
        if self._progress_callback is not None:
            self._progress_callback(message)

    def _load(self, quality='fast'):
        root = model_directory()
        self._notify("Đang kiểm tra mô hình…")
        integrity = verify_models(root)
        requested = os.getenv("HMOOB_DEVICE", "auto").lower()
        if requested not in ("auto", "cpu", "cuda", "mps"):
            raise EngineError("HMOOB_DEVICE chỉ nhận auto, cpu, cuda hoặc mps.")
        if self._model is None:
            self._notify("Đang nạp PyTorch…")
        import torch
        if requested == "auto":
            device = ("cuda" if torch.cuda.is_available() else "mps"
                      if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
                      else "cpu")
        else:
            device = requested
        if device == "cuda" and not torch.cuda.is_available():
            raise EngineError("Đã chọn CUDA nhưng PyTorch chưa nhận GPU. Cài bản PyTorch CUDA phù hợp hoặc chọn auto/cpu.")
        if device == "mps" and not (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()):
            raise EngineError("Đã chọn MPS nhưng máy này không có MPS khả dụng. Chọn auto/cpu.")
        requested_precision = os.getenv('HMOOB_PRECISION', 'auto')
        if requested_precision not in {'auto', 'fp32', 'int8'}:
            raise EngineError('HMOOB_PRECISION chỉ nhận auto, fp32 hoặc int8.')
        draft_int8 = device == 'cpu' and requested_precision == 'auto' and quality == 'turbo'
        key = (integrity, device, 'draft-int8' if draft_int8 else requested_precision)
        if self._model is None or self._model_key != key:
            # A quality switch must not hold both full networks in RAM while
            # loading the next one. Reuse one network for all 8/16/32-step jobs.
            self._model = self._model_key = None
            self._reference = self._reference_key = None
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            cache = root.parent / "cache"
            for name, folder in (("MPLCONFIGDIR", "matplotlib"), ("NUMBA_CACHE_DIR", "numba"),
                                 ("XDG_CACHE_HOME", "xdg")):
                if not os.getenv(name):
                    target = cache / folder
                    target.mkdir(parents=True, exist_ok=True)
                    os.environ[name] = str(target)
            from hmong_f5 import load_local_model
            torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
            candidate = None
            if draft_int8:
                try:
                    candidate = load_local_model(root, device, progress=self._notify, precision='int8')
                except (RuntimeError, NotImplementedError):
                    self._notify('Máy này chưa dùng được INT8; đang nạp chế độ tương thích…')
                if candidate is None:
                    import gc
                    gc.collect()
            if candidate is None:
                candidate = load_local_model(root, device, progress=self._notify,
                                             precision='fp32' if draft_int8 else requested_precision)
            self._model = candidate
            self._model_key = key
            self._reference = self._reference_key = None
            self.device = device
        return self._model

    def _prepare_reference(self, path, text, key):
        if self._reference_key != key:
            # Input is already a user-selected, 3–8 second, normalized WAV.
            # Avoid per-chunk pydub/FFmpeg preprocessing and automatic ASR.
            import soundfile
            import torch
            audio, rate = soundfile.read(str(path), dtype="float32", always_2d=True)
            tensor = torch.from_numpy(audio.T.copy())
            if not torch.isfinite(tensor).all() or float(tensor.square().mean()) < 1e-12:
                raise EngineError("Đoạn mẫu chỉ có im lặng hoặc dữ liệu không hợp lệ. Chọn đoạn có tiếng nói.")
            normalized_text = normalize_text(text)
            if not normalized_text.endswith((".", "!", "?")):
                normalized_text += "."
            self._reference = ((tensor, rate), normalized_text)
            self._reference_key = key
        return self._reference

    def synthesize(self, text, reference_path, reference_text, speed=1.0, quality="fast"):
        if not isinstance(text, str) or not text.strip() or len(text) > 400:
            raise EngineError("Mỗi đoạn tạo giọng cần 1–400 ký tự; dùng hàng đợi để đọc kịch bản dài.")
        if not isinstance(reference_text, str) or not reference_text.strip() or len(reference_text) > 2000:
            raise EngineError("Nhập đúng lời Hmong của đoạn mẫu; không tự nhận dạng hoặc đoán lời mẫu.")
        if (isinstance(speed, bool) or not isinstance(speed, (int, float))
                or not math.isfinite(speed) or not 0.5 <= speed <= 2):
            raise EngineError("Tốc độ đọc cần từ 0,5 đến 2 lần.")
        if quality not in QUALITY_STEPS:
            raise EngineError("Chọn turbo (4 bước), draft (8 bước), fast (16 bước) hoặc standard (32 bước).")
        try:
            text = normalize_text(text)
            reference_text = normalize_text(reference_text)
        except HmongTextError as exc:
            raise EngineError(str(exc)) from None
        reference_key = _reference_identity(reference_path, reference_text)
        with self._lock:
            try:
                model = self._load(quality)
                self._notify("Đang chuẩn bị đoạn giọng mẫu…")
                reference, normalized_text = self._prepare_reference(reference_path, reference_text, reference_key)
                from hmong_f5 import infer_batch
                # One bounded batch: no whole-book array or unbounded inference
                # fan-out, and no duplicate copy of a large model per process.
                import numpy as np
                reference_seconds = reference[0].shape[-1] / reference[1]
                pieces = []
                frames = 0
                expected_rate = None
                self._notify("Đang tạo âm thanh…")
                for batch in iter_batches(text, normalized_text, reference_seconds, speed,
                                          max_chars=240, max_new_seconds=min(16, 22 - reference_seconds)):
                    result = infer_batch(reference, normalized_text, batch, model,
                                         steps=QUALITY_STEPS[quality], speed=float(speed), device=self.device)
                    samples, rate = np.asarray(result[0]), result[1]
                    if (isinstance(rate, bool) or not isinstance(rate, int) or not 8000 <= rate <= 96000
                            or samples.ndim != 1 or not 0 < len(samples) <= rate * 120
                            or not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 1e-6
                            or (expected_rate is not None and rate != expected_rate)):
                        raise EngineError("Mô hình trả âm thanh rỗng, im lặng, quá dài hoặc không hợp lệ. Chưa có đoạn hoàn tất.")
                    expected_rate = rate
                    frames += len(samples)
                    if frames > rate * 120:
                        raise EngineError("Một đoạn vượt 2 phút âm thanh. Kiểm tra lời mẫu có khớp đoạn thu hay không.")
                    pieces.append(samples)
                if not pieces:
                    raise EngineError("Không có lời đọc hợp lệ trong đoạn này.")
                return np.concatenate(pieces) if len(pieces) > 1 else pieces[0], expected_rate
            except EngineError:
                raise
            except HmongTextError as exc:
                raise EngineError(str(exc)) from None
            except ImportError:
                raise EngineError("Thiếu thư viện tạo giọng. Chạy MO_VOICE_STUDIO_HMONG.bat bằng Python 3.10–3.12.") from None
            except Exception as exc:
                if type(exc).__name__ in ("OutOfMemoryError",):
                    raise EngineError("Thiếu RAM/VRAM khi tạo giọng. Tắt ứng dụng nặng hoặc chọn HMOOB_DEVICE=cpu.") from None
                raise EngineError("Không chạy được F5-Hmong. Kiểm tra phiên bản thư viện, checkpoint F5TTS_Base, "
                                  "vocabulary, Vocos và RAM; xem hướng dẫn cài giọng.") from None
