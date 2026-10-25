"""Persistent external voice samples with immutable audio/transcript selections.

The source language is unrestricted. The transcript must match the selected
audio in its original language; neither translation nor a built-in voice is
substituted when a selection is unavailable.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from fastapi import HTTPException

import builtin_references

BASE = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_SOURCE_SECONDS = 600
ID_PATTERN = re.compile(r'custom-[0-9a-f]{32}')
SAMPLE_PATTERN = re.compile(r'reference-[0-9a-f]{32}\.wav')
FORMAT_EXTENSIONS = {'WAV': 'wav', 'WAVEX': 'wav', 'RF64': 'wav',
                     'MP3': 'mp3', 'FLAC': 'flac', 'OGG': 'ogg'}


class _NeedsDecoder(Exception):
    """The native decoder cannot inspect this container."""


def directory():
    return Path(os.getenv('HMONG_STUDIO_DATA_DIR', str(BASE / '.data'))) / 'custom_voices'


def _folder(voice):
    if not isinstance(voice, str) or ID_PATTERN.fullmatch(voice) is None:
        raise HTTPException(404, 'Không tìm thấy giọng đã tải lên.')
    folder = directory() / voice
    if folder.is_symlink() or not folder.is_dir():
        raise HTTPException(404, 'Không tìm thấy giọng đã tải lên.')
    return folder


def _read_json(path):
    if path.is_symlink() or path.stat().st_size > 32768:
        raise ValueError('Invalid metadata file')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Invalid metadata value')
    return value


def _valid_name(value):
    return (isinstance(value, str) and 1 <= len(value.strip()) <= 80
            and not any(ord(character) < 32 or ord(character) == 127 for character in value))


def _metadata(voice):
    folder = _folder(voice)
    try:
        data = _read_json(folder / 'metadata.json')
        duration = data.get('duration')
        expected = 'source.' + FORMAT_EXTENSIONS[data['format']]
        source = folder / expected
        if (data.get('id') != voice or not _valid_name(data.get('name'))
                or data.get('source') != expected or source.is_symlink() or not source.is_file()
                or isinstance(duration, bool) or not isinstance(duration, (int, float))
                or not math.isfinite(duration) or not 3 <= duration <= MAX_SOURCE_SECONDS):
            raise ValueError('Invalid source metadata')
        return data
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(422, 'Dữ liệu giọng đã tải lên bị thiếu hoặc hỏng. Tải lại mẫu gốc; công cụ không đổi sang giọng mặc định.') from None


def _inspect(path):
    try:
        import soundfile
        if path.is_symlink() or not path.is_file():
            raise ValueError('Not a regular file')
        size = path.stat().st_size
        if not 0 < size <= MAX_UPLOAD_BYTES:
            raise HTTPException(413, 'Tệp giọng tối đa 50 MB và không được rỗng.')
        try:
            info = soundfile.info(str(path))
        except (RuntimeError, OSError):
            raise _NeedsDecoder from None
        duration = info.frames / info.samplerate
        if (info.format not in FORMAT_EXTENSIONS or not 1 <= info.channels <= 2
                or not 8000 <= info.samplerate <= 192000 or not math.isfinite(duration)
                or not 3 <= duration <= MAX_SOURCE_SECONDS):
            raise ValueError('Unsupported source format or duration')
        return info.format, duration
    except ImportError:
        raise HTTPException(503, 'Chưa cài thư viện đọc âm thanh. Mở lại MO_HMONG_NHANH.bat.') from None
    except (OSError, RuntimeError, ValueError, ZeroDivisionError):
        raise HTTPException(422, 'Chọn âm thanh hợp lệ dài từ 3 giây đến 10 phút; mẫu WAV/MP3/FLAC/OGG cần mono hoặc stereo.') from None


def register(upload_path, name, filename):
    """Copy a validated upload and publish the complete voice atomically."""
    if not _valid_name(name):
        raise HTTPException(422, 'Tên giọng cần từ 1 đến 80 ký tự, không chứa ký tự điều khiển.')
    path = Path(upload_path)
    root = directory()
    root.mkdir(parents=True, exist_ok=True)
    ident = 'custom-' + uuid.uuid4().hex
    temporary = Path(tempfile.mkdtemp(prefix='.upload-', dir=root))
    try:
        converted = False
        try:
            audio_format, duration = _inspect(path)
        except _NeedsDecoder:
            from audio_import import AudioImportError, DecoderUnavailable, decode_to_wav
            try:
                path = decode_to_wav(path, temporary / 'source.wav', MAX_SOURCE_SECONDS)
            except DecoderUnavailable as exc:
                raise HTTPException(503, str(exc)) from None
            except AudioImportError as exc:
                raise HTTPException(422, str(exc)) from None
            try:
                audio_format, duration = _inspect(path)
            except _NeedsDecoder:
                raise HTTPException(422, 'Không kiểm tra được WAV sau giải mã. Thử xuất lại mẫu âm thanh.') from None
            converted = True
        source_name = 'source.' + FORMAT_EXTENSIONS[audio_format]
        if path != temporary / source_name:
            shutil.copyfile(path, temporary / source_name)
        # The user's filename is display metadata only, never a filesystem path.
        original_name = str(filename or '').replace('\\', '/').rsplit('/', 1)[-1]
        original_name = ''.join(character for character in original_name if ord(character) >= 32 and ord(character) != 127)[:200]
        metadata = {'id': ident, 'name': name.strip(), 'source': source_name,
                    'original_name': original_name, 'format': audio_format,
                    'converted': converted,
                    'duration': duration, 'created_at': datetime.now(timezone.utc).isoformat()}
        (temporary / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
        temporary.rename(root / ident)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return ident


def list_ids():
    root = directory()
    if not root.is_dir():
        return []
    entries = []
    for folder in root.iterdir():
        if ID_PATTERN.fullmatch(folder.name) is None:
            continue
        try:
            data = _metadata(folder.name)
        except HTTPException:
            continue
        entries.append((str(data.get('created_at', '')), folder.name))
    return [ident for _, ident in sorted(entries)]


def name(voice):
    return _metadata(voice)['name']


def original(voice):
    data = _metadata(voice)
    return _folder(voice) / data['source']


def settings(voice):
    metadata = _metadata(voice)
    duration = metadata['duration']
    default = {'text': '', 'start': 0, 'end': min(8, duration), 'duration': duration}
    folder = _folder(voice)
    try:
        saved = _read_json(folder / 'settings.json')
        selection = builtin_references.ReferenceSettings.model_validate(saved)
        filename = saved.get('sample')
        if (not selection.text.strip() or not 3 <= selection.end - selection.start <= 8
                or selection.end > duration or not isinstance(filename, str)
                or SAMPLE_PATTERN.fullmatch(filename) is None):
            return default
        sample = folder / filename
        if sample.is_symlink() or not sample.is_file():
            return default
        return {**selection.model_dump(), 'duration': duration, 'sample': filename}
    except (OSError, ValueError, TypeError):
        return default


def save(voice, selection):
    """Select exactly the supplied clip, retaining older immutable selections."""
    source = original(voice)
    duration = _metadata(voice)['duration']
    if (not selection.text.strip() or not 3 <= selection.end - selection.start <= 8
            or selection.end > duration):
        raise HTTPException(422, 'Chọn đoạn mẫu dài 3–8 giây trong bản gốc và chép đúng lời bằng ngôn ngữ của đoạn đó; không dịch lời mẫu.')
    folder = _folder(voice)
    filename = 'reference-' + uuid.uuid4().hex + '.wav'
    with tempfile.TemporaryDirectory(prefix='.reference-', dir=folder) as temporary:
        sample = Path(temporary) / 'reference.wav'
        builtin_references._extract(source, sample, selection.start, selection.end)
        from cloning_engine import CloningError, _validate_reference
        try:
            _validate_reference(sample)
        except CloningError as exc:
            raise HTTPException(422, str(exc)) from None
        data = {**selection.model_dump(), 'text': selection.text.strip(), 'sample': filename}
        metadata = Path(temporary) / 'settings.json'
        metadata.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        sample.replace(folder / filename)
        metadata.replace(folder / 'settings.json')
    return {**data, 'duration': duration}


def selected(voice):
    saved = settings(voice)
    if not saved['text'].strip() or not saved.get('sample'):
        raise HTTPException(422, 'Giọng đã tải lên chưa có mẫu sẵn sàng. Chọn đoạn 3–8 giây và lưu đúng lời của đoạn đó trước khi tạo voice.')
    return _folder(voice) / saved['sample'], saved['text']
