"""Prepare private Turbo samples once and reuse the preset inference path.

Only speaker embeddings and codec tokens live here; neither SDK assets nor the
user's original reference files are changed. Cached arrays are lossless and
remain inside the local studio data folder.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import tempfile
import time
import zipfile

import numpy as np


SCHEMA = 1
MAX_CACHE_BYTES = 1024 * 1024
MAX_REFERENCE_BYTES = 64 * 1024 * 1024
LOCK_WAIT_SECONDS = 180


def _file_identity(value):
    if not value:
        return None
    path = Path(value).resolve()
    try:
        stat = path.stat()
    except OSError:
        return {'path': str(path), 'missing': True}
    # Hugging Face paths resolve to content-addressed blobs. For local models,
    # size and modification time also invalidate a replaced encoder.
    return {'path': str(path), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def _cache_key(model, reference, precision):
    reference = Path(reference)
    if reference.stat().st_size > MAX_REFERENCE_BYTES:
        raise ValueError('Mẫu giọng quá lớn để chuẩn bị cho Turbo.')
    with reference.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    engine = model.engine
    codec = getattr(engine, '_codec_enc_path', None)
    resolver = getattr(engine, '_resolve_root_file', None)
    speaker = resolver(getattr(engine, 'speaker_encoder_filename', 'speaker_encoder.onnx')) if resolver else None
    identity = {
        'schema': SCHEMA, 'reference_sha256': digest,
        'sdk': importlib.metadata.version('vieneu'),
        'backend': getattr(model, 'backend', None), 'precision': precision,
        'model': getattr(model, 'backbone_repo', None),
        'checkpoint': getattr(engine, 'checkpoint_path', None),
        'config': getattr(engine, 'cfg', {}),
        'codec': _file_identity(codec),
        'codec_data': _file_identity(Path(codec).with_suffix('.data')) if codec else None,
        'speaker': _file_identity(speaker),
        'preprocessing': 'sdk-preclean-denoise-false-use-ref-codes-true',
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def _voice(embedding, codes, codebooks):
    # Preserve every codec book exposed by the loaded graph (the bundled
    # Turbo model uses sixteen), rather than rounding through JSON or slicing.
    if (not isinstance(embedding, np.ndarray) or embedding.dtype != np.float32
            or embedding.shape != (192,) or not np.isfinite(embedding).all()
            or not np.any(embedding)):
        raise ValueError('Dữ liệu nhận diện giọng Turbo không hợp lệ.')
    if (not isinstance(codes, np.ndarray) or codes.dtype != np.int64
            or codes.ndim != 2 or codes.shape[1] != codebooks or not 1 <= codes.shape[0] <= 2048
            or np.any(codes < 0) or np.any(codes >= 65536)):
        raise ValueError('Mã âm thanh mẫu giọng Turbo không hợp lệ.')
    return {'speaker_emb': embedding, 'codes': codes}


def _read(path, key, codebooks):
    try:
        if path.stat().st_size > MAX_CACHE_BYTES:
            return None
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if ({entry.filename for entry in entries} != {'schema.npy', 'key.npy', 'speaker_emb.npy', 'codes.npy'}
                    or len(entries) != 4 or sum(entry.file_size for entry in entries) > MAX_CACHE_BYTES):
                return None
            # Validate NPY headers before NumPy can allocate arrays described by
            # a damaged cache. The ZIP size limit alone does not bound those
            # declared shapes.
            for entry in entries:
                with archive.open(entry) as stream:
                    version = np.lib.format.read_magic(stream)
                    if version == (1, 0):
                        shape, _, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
                    elif version == (2, 0):
                        shape, _, dtype = np.lib.format.read_array_header_2_0(stream, max_header_size=4096)
                    else:
                        return None
                    if dtype.hasobject:
                        return None
                    if entry.filename == 'speaker_emb.npy' and (shape != (192,) or dtype != np.float32):
                        return None
                    if entry.filename == 'codes.npy' and (len(shape) != 2 or shape[1] != codebooks
                            or not 1 <= shape[0] <= 2048 or dtype != np.int64):
                        return None
                    if entry.filename in {'schema.npy', 'key.npy'} and (shape != () or dtype.itemsize > 512):
                        return None
        with np.load(path, allow_pickle=False, max_header_size=4096) as arrays:
            schema, stored_key = arrays['schema'], arrays['key']
            if schema.shape != () or schema.dtype.kind not in 'iu' or int(schema) != SCHEMA:
                return None
            if stored_key.shape != () or stored_key.dtype.kind != 'U' or str(stored_key) != key:
                return None
            return _voice(arrays['speaker_emb'], arrays['codes'], codebooks)
    except (OSError, ValueError, KeyError, EOFError, RuntimeError, zipfile.BadZipFile):
        return None


def _write(path, key, voice):
    descriptor, temporary = tempfile.mkstemp(prefix='.turbo-reference-', suffix='.npz', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            np.savez(stream, schema=np.asarray(SCHEMA, dtype=np.int64), key=np.asarray(key), **voice)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def _exclusive(path, cancel_path):
    # OS locks are released even if a worker crashes. Keep this lock file:
    # deleting a lock file could let new and existing workers lock different
    # inodes. Windows' byte-range locking and Unix flock both work across the
    # shared thread pool and the separate render processes.
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, 'r+b') as stream:
        if os.name == 'nt':
            import msvcrt
            def lock():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            def unlock():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def lock():
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            def unlock():
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        started = time.monotonic()
        while True:
            if cancel_path is not None and Path(cancel_path).exists():
                raise InterruptedError('Đã dừng chuẩn bị mẫu giọng Turbo.')
            try:
                lock()
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() - started >= LOCK_WAIT_SECONDS:
                    raise TimeoutError('Chuẩn bị mẫu giọng Turbo mất quá lâu; hãy thử lại.') from error
                time.sleep(.05)
        try:
            yield
        finally:
            unlock()


def prepared_turbo_voice(model, reference, data, *, precision='fp32', cancel_path=None):
    """Return a preset-compatible dict from the selected sample, never a fallback.

    Concurrent render processes encode a new clip once. Further chunks and
    application restarts load its small private arrays without hashing the WAV
    or acquiring the SDK enrollment lock during speech synthesis.
    """
    key = _cache_key(model, reference, precision)
    codebooks = getattr(model.engine, 'n_vq', getattr(model.engine, 'cfg', {}).get('n_vq', 16))
    if type(codebooks) is not int or not 1 <= codebooks <= 32:
        raise ValueError('Cấu hình bộ mã âm thanh Turbo không hợp lệ.')
    directory = Path(data) / 'cache' / 'turbo-references'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (key + '.npz')
    voice = _read(path, key, codebooks)
    if voice is not None:
        return voice
    with _exclusive(path.with_suffix('.lock'), cancel_path):
        voice = _read(path, key, codebooks)
        if voice is None:
            embedding, codes = model.encode_reference(str(reference), denoise=False)
            voice = _voice(embedding, codes, codebooks)
            _write(path, key, voice)
        return voice
