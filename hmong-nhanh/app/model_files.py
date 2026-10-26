"""Verify release-pinned model identities before loading executable configuration."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import threading

from model_manifest import PINNED_MODELS

BASE = Path(__file__).resolve().parent
MODEL_FILES = tuple(PINNED_MODELS)
_integrity_cache = {}
_integrity_lock = threading.Lock()


class EngineError(RuntimeError):
    pass


def model_directory():
    data = Path(os.getenv('HMONG_STUDIO_DATA_DIR', str(BASE / '.data')))
    return Path(os.getenv('HMONG_F5_MODEL_DIR', str(data / 'models'))).expanduser().resolve()


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _invalid(relative):
    return EngineError(
        'Không xác minh được ' + relative + ' theo bộ mô hình đã cố định của bản này '
        '(thiếu tệp, sai kích thước hoặc SHA-256). Chạy bước cài đặt mô hình để tải lại '
        'F5-Hmong/Vocos chính thức. Nếu dùng HMONG_F5_CHECKPOINT, HMONG_F5_VOCAB hoặc '
        'HMONG_F5_VOCODER, trỏ tới đúng bộ đó; tool không nạp trọng số/cấu hình khác.')


def _fingerprint(paths):
    fingerprint = []
    for relative in MODEL_FILES:
        try:
            path = paths[relative]
            record = PINNED_MODELS[relative]
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_size != record['size']:
                raise _invalid(relative)
            # Resolve on every check so replacing a symlink target invalidates
            # the cache too. ctime catches same-size edits with restored mtime.
            fingerprint.append((relative, str(path.resolve()), info.st_dev, info.st_ino,
                                info.st_size, info.st_mtime_ns, info.st_ctime_ns,
                                record['sha256']))
        except (OSError, ValueError, KeyError, TypeError):
            raise _invalid(relative) from None
    return tuple(fingerprint)


def _verify_paths(paths):
    with _integrity_lock:
        key = _fingerprint(paths)
        if key in _integrity_cache:
            return key
        for relative in MODEL_FILES:
            try:
                if _sha256(paths[relative]) != PINNED_MODELS[relative]['sha256']:
                    raise _invalid(relative)
            except OSError:
                raise _invalid(relative) from None
        # A concurrent replacement during hashing must not become a cached pass.
        if _fingerprint(paths) != key:
            raise EngineError('Tệp mô hình thay đổi trong lúc kiểm tra. Đóng tác vụ sửa/tải mô hình rồi thử lại.')
        _integrity_cache.clear()
        _integrity_cache[key] = True
        return key


def verify_models(root=None):
    """Check official files in any directory; local receipts cannot grant trust."""
    root = Path(root).expanduser() if root is not None else model_directory()
    return _verify_paths({relative: root / relative for relative in MODEL_FILES})


def verify_model_paths(settings):
    """Verify the actual checkpoint/vocab/vocoder overrides that F5 will open."""
    try:
        vocoder = Path(settings['vocoder']).expanduser()
        paths = {
            'f5-hmong/model_159952.safetensors': Path(settings['checkpoint']).expanduser(),
            'f5-hmong/vocab.txt': Path(settings['vocab']).expanduser(),
            'vocos/config.yaml': vocoder / 'config.yaml',
            'vocos/pytorch_model.bin': vocoder / 'pytorch_model.bin',
        }
    except (KeyError, TypeError, ValueError):
        raise EngineError('Đường dẫn mô hình chưa hợp lệ. Chọn đúng bộ F5-Hmong/Vocos của tool.') from None
    return _verify_paths(paths)
