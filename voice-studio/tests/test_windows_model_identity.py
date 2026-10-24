"""Windows model cache tokens require a journal sequence and exclude open writers."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

import hmong_engine as engine
import hmong_native_models as models


class BasicInfo(ctypes.Structure):
    _fields_ = [('ChangeTime', ctypes.c_longlong)]


def usn_record(major=2, usn=0x123456789ABCD):
    size, offset = {2: (60, 24), 3: (76, 40)}[major]
    raw = bytearray(b'\xa5' * size)
    struct.pack_into('<IHH', raw, 0, size, major, 0)
    struct.pack_into('<q', raw, offset, usn)
    return bytes(raw)


class Kernel:
    def __init__(self, reply):
        self.reply = reply
        self.closed = []
        self.opened = []
        self.change_time = 456
        self.handle = 37
        self.control_success = self.query_success = True
        self.returned = None

    def create(self, path, access, share, security, disposition, flags, template):
        self.opened.append((path, access, share, security, disposition, flags, template))
        assert access == 0x80000000 and share == 1  # Never share writes.
        assert disposition == 3 and security is template is None
        return self.handle

    def query(self, handle, information_class, output, size):
        assert handle == self.handle and information_class == 0
        assert size == ctypes.sizeof(BasicInfo)
        ctypes.cast(output, ctypes.POINTER(BasicInfo)).contents.ChangeTime = self.change_time
        return self.query_success

    def control(self, handle, code, request, request_size, output, capacity, returned, overlapped):
        assert handle == self.handle and code == 0x900EB
        assert request_size == 4 and ctypes.string_at(request, 4) == struct.pack('<HH', 2, 3)
        assert capacity == 4096 and overlapped is None
        ctypes.memmove(output, bytes(self.reply), min(len(self.reply), capacity))
        ctypes.cast(returned, ctypes.POINTER(ctypes.c_uint32)).contents.value = (
            len(self.reply) if self.returned is None else self.returned)
        return self.control_success

    def close(self, handle):
        self.closed.append(handle)
        return True


def fake_kernel(monkeypatch, kernel):
    monkeypatch.setattr(engine, '_windows_file_information', lambda: (kernel.query, BasicInfo))
    monkeypatch.setattr(engine, '_windows_usn_api', lambda: (kernel.create, kernel.control, kernel.close))


@pytest.mark.parametrize('major', [2, 3])
def test_windows_reads_the_full_64_bit_usn_from_the_correct_record_layout(monkeypatch, major):
    kernel = Kernel(usn_record(major))
    fake_kernel(monkeypatch, kernel)
    assert engine._windows_change_identity(Path('model with spaces.pth')) == (456, 0x123456789ABCD)
    assert kernel.closed == [37]


@pytest.mark.parametrize('failure', [
    'unsupported', 'short', 'unknown-version', 'oversized-record', 'undersized-record',
    'oversized-response', 'zero-usn', 'negative-usn', 'no-change-time', 'query-failed',
])
def test_untrusted_windows_journal_information_disables_caching(monkeypatch, failure):
    raw = bytearray(usn_record())
    kernel = Kernel(raw)
    if failure == 'unsupported':
        kernel.control_success = False
    elif failure == 'short':
        kernel.returned = 7
    elif failure == 'unknown-version':
        struct.pack_into('<H', raw, 4, 4)
    elif failure == 'oversized-record':
        struct.pack_into('<I', raw, 0, len(raw) + 1)
    elif failure == 'undersized-record':
        struct.pack_into('<I', raw, 0, 32)
    elif failure == 'oversized-response':
        kernel.returned = 4097
    elif failure in {'zero-usn', 'negative-usn'}:
        struct.pack_into('<q', raw, 24, 0 if failure == 'zero-usn' else -1)
    elif failure == 'no-change-time':
        kernel.change_time = 0
    else:
        kernel.query_success = False
    fake_kernel(monkeypatch, kernel)
    assert engine._windows_change_identity(Path('model.pth')) is None
    assert kernel.closed == [37]


def test_open_writer_or_denied_access_prevents_a_cache_token(monkeypatch):
    kernel = Kernel(usn_record())
    kernel.handle = ctypes.c_void_p(-1).value
    fake_kernel(monkeypatch, kernel)
    assert engine._windows_change_identity(Path('model.pth')) is None
    assert len(kernel.opened) == 1
    assert kernel.closed == []


def test_windows_fingerprint_keeps_five_fields_and_never_trusts_creation_time(monkeypatch):
    monkeypatch.setattr(engine, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(engine, '_windows_change_identity', lambda path: None)
    stat = SimpleNamespace(st_dev=1, st_ino=2, st_size=3, st_mtime_ns=4, st_ctime_ns=999)
    assert engine._file_fingerprint(Path('model.pth'), stat) == (1, 2, 3, 4, None)


@pytest.fixture
def tiny_native(tmp_path, monkeypatch):
    records = {}
    for index, (name, original) in enumerate(models.MODEL_RECORDS.items()):
        raw = ('tiny native fixture ' + str(index)).encode()
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        records[name] = dict(original, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(models, 'MODEL_RECORDS', records)
    (tmp_path / models.MANIFEST_NAME).write_text(json.dumps({
        'version': 1, 'backend': 'hmong_native', 'files': records,
    }), encoding='utf-8')
    models._integrity_cache.clear()
    yield tmp_path
    models._integrity_cache.clear()


def test_missing_usn_hashes_again_even_when_all_other_metadata_matches(tiny_native, monkeypatch):
    monkeypatch.setattr(engine, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(engine, '_windows_change_identity', lambda path: None)
    real_hash = models._sha256
    calls = []

    def checksum(path):
        calls.append(path)
        return real_hash(path)

    monkeypatch.setattr(models, '_sha256', checksum)
    models.verify_models(tiny_native)
    models.verify_models(tiny_native)
    assert len(calls) == 2 * len(models.MODEL_RECORDS)
    assert not models._integrity_cache
    path = tiny_native / next(iter(models.MODEL_RECORDS))
    previous = path.stat()
    path.write_bytes(b'!' * previous.st_size)
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    with pytest.raises(models.EngineError, match='SHA-256'):
        models.verify_models(tiny_native)


def test_changed_usn_invalidates_cache_when_change_time_and_mtime_are_identical(tiny_native, monkeypatch):
    monkeypatch.setattr(engine, 'os', SimpleNamespace(name='nt'))
    sequences = {}
    monkeypatch.setattr(engine, '_windows_change_identity', lambda path: (456, sequences.get(str(path), 100)))
    models.verify_models(tiny_native)
    assert models._integrity_cache
    path = tiny_native / next(iter(models.MODEL_RECORDS))
    previous = path.stat()
    path.write_bytes(b'!' * previous.st_size)
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    sequences[str(path)] = 101
    with pytest.raises(models.EngineError, match='SHA-256'):
        models.verify_models(tiny_native)


def test_repeated_overwrites_with_an_open_writer_and_restored_mtime_are_rejected(tiny_native):
    models.verify_models(tiny_native)
    path = tiny_native / next(iter(models.MODEL_RECORDS))
    raw = path.read_bytes()
    previous = path.stat()
    with path.open('r+b') as writer:
        writer.write(raw)
        writer.flush()
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        models.verify_models(tiny_native)
        writer.seek(0)
        writer.write(b'!' * len(raw))
        writer.flush()
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        with pytest.raises(models.EngineError, match='SHA-256'):
            models.verify_models(tiny_native)
