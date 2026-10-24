"""Local model locations and integrity checks for Hmong Studio."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import threading

BASE = Path(__file__).resolve().parent
MODEL_FILES = (
    "f5-hmong/model_159952.safetensors",
    "f5-hmong/vocab.txt",
    "vocos/config.yaml",
    "vocos/pytorch_model.bin",
)
_integrity_cache = {}
_integrity_lock = threading.Lock()

class EngineError(RuntimeError):
    pass

def model_directory():
    data = Path(os.getenv("HMONG_STUDIO_DATA_DIR", str(BASE / ".data")))
    return Path(os.getenv("HMONG_F5_MODEL_DIR", str(data / "models"))).expanduser().resolve()

def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_models(root=None):
    """Verify all files once per filesystem identity; never trust size alone."""
    root = Path(root) if root is not None else model_directory()
    try:
        manifest_path = root / "verified-models.json"
        if manifest_path.stat().st_size > 100_000:
            raise ValueError("manifest too large")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = manifest["files"]
        fingerprint = [(str(root.resolve()), manifest_path.stat().st_mtime_ns,
                        manifest_path.stat().st_ctime_ns, manifest_path.stat().st_size)]
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
            fingerprint.append((relative, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, expected))
        key = tuple(fingerprint)
        with _integrity_lock:
            if key in _integrity_cache:
                return key
            for relative in MODEL_FILES:
                if _sha256(root / relative) != records[relative]["sha256"]:
                    raise ValueError("checksum mismatch")
            _integrity_cache.clear()
            _integrity_cache[key] = True
        return key
    except (OSError, ValueError, KeyError, TypeError):
        raise EngineError("Thiếu mô hình hoặc kiểm tra SHA-256 không đạt. Chạy MO_HMONG_NHANH.bat "
                          "hoặc python setup_voice.py bằng mạng được phép; không dùng tệp chưa xác minh.") from None

