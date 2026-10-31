"""Read the locally converted, verified VoxCPM2 GGUF preparation record.

This module performs no download or conversion. Installation verifies the public
original checkpoint and exact AudioVAE conversion separately; inference checks
the resulting GGUF hash before loading it into the pinned native runtime.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


MODEL_REPOSITORY = 'openbmb/VoxCPM2'
MODEL_REVISION = '32279effe8c19989596f05d353d1447f51d9e915'
NATIVE_REVISION = '2597b300f5961999387c84c65f2e8e79c088a571'
MODEL_DIRECTORY = 'voxcpm2-native'
MODEL_FILENAME = 'voxcpm2-q8_0.gguf'
MARKER_NAME = 'voxcpm-native.ready'
SUPPORTED_LANGUAGES = frozenset({
    'ar', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'he', 'hi', 'id', 'it',
    'ja', 'km', 'ko', 'lo', 'ms', 'my', 'nl', 'no', 'pl', 'pt', 'ru', 'sv',
    'sw', 'th', 'tl', 'tr', 'vi', 'zh',
})
_verified_models = set()


def language_code(language):
    code = {'en-US': 'en', 'en-GB': 'en'}.get(language, language) if isinstance(language, str) else None
    if code not in SUPPORTED_LANGUAGES:
        raise ValueError('Ngôn ngữ này chưa được VoxCPM2 native hỗ trợ.')
    return code


def prepared_model(data, verify=False):
    models = Path(data).resolve() / 'models'
    record = json.loads((models / MARKER_NAME).read_text(encoding='utf-8'))
    if (not isinstance(record, dict) or type(record.get('schema')) is not int
            or record.get('schema') != 1 or record.get('backend') != 'voxcpm_native'
            or record.get('repository') != MODEL_REPOSITORY
            or record.get('revision') != MODEL_REVISION
            or record.get('native_source_revision') != NATIVE_REVISION
            or record.get('model_dir') != MODEL_DIRECTORY
            or record.get('filename') != MODEL_FILENAME
            or record.get('quantization', 'q8_0') != 'q8_0'):
        raise ValueError('Bản ghi VoxCPM2 native không đúng nguồn và phiên bản đã xác minh.')
    size, digest = record.get('size'), record.get('sha256')
    if (type(size) is not int or not 4 <= size <= 8 * 1024**3
            or not isinstance(digest, str) or len(digest) != 64
            or any(char not in '0123456789abcdef' for char in digest)):
        raise ValueError('Bản ghi VoxCPM2 native thiếu kích thước hoặc SHA256 hợp lệ.')
    model = models / MODEL_DIRECTORY / MODEL_FILENAME
    if not model.resolve().is_relative_to(models.resolve()):
        raise ValueError('Mô hình VoxCPM2 native nằm ngoài thư mục dữ liệu.')
    before = model.stat()
    if before.st_size != size:
        raise ValueError('Mô hình VoxCPM2 native chưa được chuyển đổi đầy đủ.')
    with model.open('rb') as stream:
        if stream.read(4) != b'GGUF':
            raise ValueError('Mô hình VoxCPM2 native không phải GGUF hợp lệ.')
    state = (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino, before.st_dev)
    key = (str(model.resolve()), state, digest)
    if verify and key not in _verified_models:
        with model.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = model.stat()
        current = (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino, after.st_dev)
        if actual != digest or current != state:
            raise ValueError('SHA256 mô hình VoxCPM2 native không khớp. Chuyển đổi lại mô hình đã xác minh.')
        _verified_models.clear()
        _verified_models.add(key)
    return model, record
