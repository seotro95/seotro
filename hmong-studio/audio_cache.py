"""Bounded local PCM cache for exact Hmong inference inputs.

Entries contain audio and integrity metadata only. Text/reference contents never
appear in filenames or metadata. A hit reuses an earlier real inference result;
it is not evidence of faster synthesis of new speech.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import wave

SCHEMA = 1
CACHE_VERSION = 'hmong-pcm-v1'
MAX_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 512
MAX_ENTRY_BYTES = 32 * 1024 * 1024
_KEY = re.compile(r'[0-9a-f]{64}')
_BLOCK = 64 * 1024


def reference_digest(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 200 * 1024 * 1024:
        raise ValueError('Không tìm thấy mẫu giọng hợp lệ cho cache.')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(_BLOCK), b''):
            digest.update(block)
    return digest.hexdigest()


def _inspect(path):
    path = Path(path)
    size = path.stat().st_size
    if path.is_symlink() or not 44 < size <= MAX_ENTRY_BYTES:
        raise ValueError('invalid cache WAV size')
    nonzero = False
    with wave.open(str(path), 'rb') as reader:
        if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate(),
                reader.getcomptype()) != (1, 2, 24000, 'NONE'):
            raise ValueError('invalid cache WAV format')
        frames = reader.getnframes()
        if not 0 < frames <= (MAX_ENTRY_BYTES - 44) // 2:
            raise ValueError('invalid cache WAV frames')
        remaining = frames
        while remaining:
            count = min(remaining, _BLOCK // 2)
            data = reader.readframes(count)
            if len(data) != count * 2:
                raise ValueError('truncated cache WAV')
            nonzero = nonzero or any(data)
            remaining -= count
    if not nonzero:
        raise ValueError('silent cache WAV')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(_BLOCK), b''):
            digest.update(block)
    return {'size': size, 'frames': frames, 'sha256': digest.hexdigest()}


class AudioCache:
    def __init__(self, root=None, *, max_bytes=MAX_BYTES, max_entries=MAX_ENTRIES):
        if (isinstance(max_bytes, bool) or not isinstance(max_bytes, int)
                or not 1 <= max_bytes <= MAX_BYTES
                or isinstance(max_entries, bool) or not isinstance(max_entries, int)
                or not 1 <= max_entries <= MAX_ENTRIES):
            raise ValueError('invalid cache limits')
        self.root = Path(root or os.getenv('HMONG_AUDIO_CACHE_DIR') or
                         Path(__file__).resolve().parent / '.data' / 'audio-cache').expanduser().resolve()
        self.max_bytes, self.max_entries = max_bytes, max_entries
        disabled = os.getenv('HMONG_AUDIO_CACHE_DISABLED', '0')
        reads = os.getenv('HMONG_AUDIO_CACHE_READS', '1')
        if disabled not in {'0', '1'} or reads not in {'0', '1'}:
            raise ValueError('HMONG_AUDIO_CACHE_DISABLED và HMONG_AUDIO_CACHE_READS phải là 0 hoặc 1.')
        self.enabled = os.getenv('HMONG_AUDIO_CACHE', '1') != '0' and disabled != '1'
        self.reads_enabled = self.enabled and reads == '1'

    @staticmethod
    def key(**parts):
        raw = json.dumps({'version': CACHE_VERSION, **parts}, sort_keys=True,
                         ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def _paths(self, key):
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            raise ValueError('invalid cache key')
        return self.root / (key + '.wav'), self.root / (key + '.json')

    def _discard(self, key):
        for path in self._paths(key):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def read(self, key):
        if not self.reads_enabled:
            return None
        audio, metadata = self._paths(key)
        try:
            if metadata.is_symlink() or metadata.stat().st_size > 1024:
                raise ValueError('invalid cache metadata')
            record = json.loads(metadata.read_text(encoding='utf-8'))
            info = _inspect(audio)
            if (not isinstance(record, dict) or record.get('schema') != SCHEMA
                    or record.get('key') != key
                    or any(record.get(name) != value for name, value in info.items())):
                raise ValueError('cache checksum mismatch')
            os.utime(audio, None)
            return audio
        except (OSError, ValueError, TypeError, EOFError, wave.Error):
            self._discard(key)
            return None

    def _trim(self, incoming_key, incoming_size, owned=()):
        entries = []
        orphan_bytes = 0
        now = time.time()
        for path in self.root.iterdir():
            if path in owned:
                continue
            if path.name.startswith('.cache-entry-') and path.name.endswith('.tmp'):
                # Cancellation can leave a temporary. Never remove another
                # currently-writing process's recent temporary file.
                if now - path.stat().st_mtime > 120:
                    path.unlink(missing_ok=True)
                else:
                    orphan_bytes += path.stat().st_size
            elif path.suffix == '.wav' and _KEY.fullmatch(path.stem):
                if path.stem == incoming_key:
                    continue
                metadata = path.with_suffix('.json')
                size = path.lstat().st_size + (metadata.lstat().st_size if metadata.exists() else 0)
                entries.append((path.stat().st_mtime, path.stem, size))
            elif path.suffix == '.json' and _KEY.fullmatch(path.stem):
                if not path.with_suffix('.wav').exists():
                    path.unlink(missing_ok=True)
        total = sum(item[2] for item in entries) + incoming_size + orphan_bytes
        count = len(entries) + 1
        for _, key, size in sorted(entries):
            if total <= self.max_bytes and count <= self.max_entries:
                break
            self._discard(key)
            audio, metadata = self._paths(key)
            if not audio.exists() and not metadata.exists():
                total -= size
                count -= 1
        return total <= self.max_bytes and count <= self.max_entries

    def store(self, key, source):
        if not self.enabled:
            return False
        audio, metadata = self._paths(key)
        temporary = []
        try:
            info = _inspect(source)
            if info['size'] + 256 > self.max_bytes:
                return False
            self.root.mkdir(parents=True, exist_ok=True)
            for _ in range(2):
                descriptor, name = tempfile.mkstemp(prefix='.cache-entry-', suffix='.tmp', dir=self.root)
                os.close(descriptor)
                temporary.append(Path(name))
            with Path(source).open('rb') as reader, temporary[0].open('wb') as writer:
                shutil.copyfileobj(reader, writer, length=_BLOCK)
            copied = _inspect(temporary[0])
            if copied != info:
                raise ValueError('cache source changed while copying')
            record = {'schema': SCHEMA, 'key': key, **info}
            temporary[1].write_text(json.dumps(record, sort_keys=True), encoding='utf-8')
            # Our pending files are counted as the incoming entry, not orphans.
            if not self._trim(key, info['size'] + temporary[1].stat().st_size, temporary):
                return False
            os.replace(temporary[0], audio)
            os.replace(temporary[1], metadata)
            return True
        except (OSError, ValueError, TypeError, EOFError, wave.Error):
            return False
        finally:
            for path in temporary:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
