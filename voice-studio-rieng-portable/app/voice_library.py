"""Resolve private default references without exposing them in the public catalog."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import wave


CATALOG_LANGUAGES = frozenset({'en-US', 'en-GB', 'ko', 'ru', 'ja', 'fr', 'es', 'th'})
CATALOG_ENGINES = frozenset({'vieneu', 'voxcpm'})
_IDENT = re.compile(r'[0-9a-f]{32}')
_SHA256 = re.compile(r'[0-9a-f]{64}')
_MAX_WAV_BYTES = 64 * 1024 * 1024


class ReferenceValidationError(ValueError):
    """A local reference is invalid; messages deliberately omit private paths."""


def library_root() -> Path:
    configured = os.environ.get('VOICE_STUDIO_VOICE_LIBRARY')
    return Path(configured or Path(__file__).resolve().parent / 'voice-library').expanduser().resolve()


def _valid_id(voice_id):
    if not isinstance(voice_id, str) or not _IDENT.fullmatch(voice_id):
        raise ReferenceValidationError('Mã mẫu giọng không hợp lệ.')


def _safe_path(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative
            or '\x00' in relative or any(part in {'', '.', '..'} for part in relative.split('/'))):
        raise ReferenceValidationError('Đường dẫn mẫu giọng không hợp lệ.')
    path = PurePosixPath(relative)
    if path.is_absolute():
        raise ReferenceValidationError('Đường dẫn mẫu giọng không hợp lệ.')
    try:
        resolved = root.joinpath(*path.parts).resolve()
    except (OSError, RuntimeError):
        raise ReferenceValidationError('Không đọc được đường dẫn mẫu giọng.') from None
    if not resolved.is_relative_to(root):
        raise ReferenceValidationError('Mẫu giọng nằm ngoài thư mục thư viện.')
    return resolved


def _catalog_records(root: Path):
    try:
        manifest = _safe_path(root, 'manifest.json')
        if manifest.stat().st_size > 2 * 1024 * 1024:
            return []
        document = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError):
        return []
    if (not isinstance(document, dict) or type(document.get('schema_version')) is not int
            or document['schema_version'] != 1):
        return []
    entries = document.get('voices')
    if not isinstance(entries, list):
        return []
    records, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ident, name, language = entry.get('id'), entry.get('name'), entry.get('language')
        if (not isinstance(ident, str) or not _IDENT.fullmatch(ident) or ident in seen
                or not isinstance(name, str) or not 1 <= len(name.strip()) <= 80
                or any(ord(char) < 32 or ord(char) == 127 for char in name)
                or not isinstance(language, str) or language not in CATALOG_LANGUAGES):
            continue
        engine = 'vieneu' if language in {'en-US', 'en-GB'} else 'voxcpm'
        supplied_engine = entry.get('engine', engine)
        if not isinstance(supplied_engine, str) or supplied_engine not in CATALOG_ENGINES or supplied_engine != engine:
            continue
        seen.add(ident)
        records.append({**entry, 'name': name.strip(), 'engine': engine,
                        'languages': ['en-US', 'en-GB'] if language.startswith('en-') else [language],
                        'native_language': language.split('-')[0], 'category': 'reference',
                        'is_default': True, 'readonly': True})
    return records


def _verify_audio(path: Path, metadata: dict, *, require_hash: bool) -> float:
    if not path.is_file():
        raise FileNotFoundError('Thiếu tệp mẫu giọng.')
    try:
        if path.stat().st_size > _MAX_WAV_BYTES:
            raise ReferenceValidationError('Tệp WAV mẫu giọng quá lớn.')
        if require_hash:
            expected = metadata.get('reference_sha256')
            if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
                raise ReferenceValidationError('Mẫu giọng thiếu mã SHA256 hợp lệ.')
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ReferenceValidationError('SHA256 mẫu giọng không khớp; kiểm tra lại gói giọng.')
        with wave.open(str(path), 'rb') as audio:
            frames, rate = audio.getnframes(), audio.getframerate()
            channels, width = audio.getnchannels(), audio.getsampwidth()
            if (audio.getcomptype() != 'NONE' or channels not in {1, 2} or width not in {1, 2, 3, 4}
                    or not 8000 <= rate <= 192000 or not 3 <= frames / rate <= 30):
                raise ReferenceValidationError('Dùng WAV PCM đọc được, dài từ 3 đến 30 giây.')
            if require_hash:
                for field, actual in (('reference_frames', frames), ('reference_sample_rate', rate)):
                    if field in metadata and metadata[field] != actual:
                        raise ReferenceValidationError('Thông số WAV mẫu giọng không khớp manifest.')
            count = 0
            while block := audio.readframes(65536):
                count += len(block)
            if count != frames * channels * width:
                raise ReferenceValidationError('Dữ liệu WAV mẫu giọng bị thiếu hoặc hỏng.')
            return frames / rate
    except (wave.Error, EOFError):
        raise ReferenceValidationError('Không đọc được mẫu giọng dưới dạng WAV PCM.') from None


def _pack_reference(root: Path, metadata: dict):
    path = _safe_path(root, metadata.get('reference_audio'))
    return path, _verify_audio(path, metadata, require_hash=True)


def catalog_voices() -> list[dict]:
    """List defaults even when their local audio is missing or damaged."""
    root, public = library_root(), []
    for record in _catalog_records(root):
        declared = record.get('duration')
        duration = float(declared) if (isinstance(declared, (int, float)) and not isinstance(declared, bool)
                                      and math.isfinite(declared) and 0 <= declared <= 30) else None
        has_sample, reason = True, None
        try:
            _, duration = _pack_reference(root, record)
        except (OSError, ValueError) as exc:
            has_sample = False
            reason = (str(exc) if isinstance(exc, ReferenceValidationError) else 'Thiếu tệp mẫu giọng.'
                      if isinstance(exc, FileNotFoundError) else 'Không đọc được tệp mẫu giọng.')
        voice = {key: record[key] for key in ('id', 'name', 'category', 'is_default', 'readonly',
                                              'engine', 'languages', 'native_language')}
        voice.update(has_sample=has_sample, sample_url=f"/api/voices/{record['id']}/sample",
                     duration=duration, description='Mẫu giọng mặc định riêng' +
                     (f' · {duration:.1f}s' if duration is not None else ''))
        if reason:
            voice['missing_reason'] = reason
        public.append(voice)
    return public


def _resolve_reference(voice_id: str, data: Path) -> tuple[Path, dict]:
    _valid_id(voice_id)
    root = library_root()
    for record in _catalog_records(root):
        if record['id'] == voice_id:
            path, duration = _pack_reference(root, record)
            return path, {**record, 'duration': duration}
    data = Path(data).resolve()
    record_path = _safe_path(data, f'voices/{voice_id}.json')
    path = _safe_path(data, f'voices/{voice_id}.wav')
    if not record_path.is_file() or not path.is_file():
        raise FileNotFoundError('Không tìm thấy mẫu giọng.')
    try:
        record = json.loads(record_path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError):
        raise ReferenceValidationError('Hồ sơ mẫu giọng không hợp lệ.') from None
    if not isinstance(record, dict) or record.get('id', voice_id) != voice_id:
        raise ReferenceValidationError('Hồ sơ mẫu giọng không khớp mã giọng.')
    duration = _verify_audio(path, record, require_hash=False)
    language = record.get('language')
    if not language:
        languages = record.get('languages', ['vi'])
        if not isinstance(languages, list) or not languages or not isinstance(languages[0], str):
            raise ReferenceValidationError('Ngôn ngữ trong hồ sơ mẫu giọng không hợp lệ.')
        language = languages[0]
    return path, {**record, 'id': voice_id, 'duration': duration,
                  'engine': record.get('engine') or ('vieneu' if language == 'vi' else 'qwen_clone'),
                  'category': record.get('category', 'cloned'), 'readonly': False, 'is_default': False}


def resolve_reference(voice_id: str, data: Path) -> tuple[Path, dict]:
    """Return a verified reference and private metadata for synthesis only."""
    try:
        return _resolve_reference(voice_id, data)
    except FileNotFoundError:
        raise FileNotFoundError('Không tìm thấy mẫu giọng.') from None
    except OSError:
        raise ReferenceValidationError('Không đọc được tệp hoặc hồ sơ mẫu giọng.') from None
