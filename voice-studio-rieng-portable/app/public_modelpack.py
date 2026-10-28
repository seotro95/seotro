"""Explicit installer transport for the official public Apache-2.0 VoxCPM2 model.

Importing this module never downloads anything. No application files, recordings
or credentials are sent to the release host. Split assets are read directly as a
ZIP, avoiding another five-gigabyte joined archive.
"""
from __future__ import annotations

import bisect
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import urllib.request
import zipfile

REPOSITORY = 'openbmb/VoxCPM2'
REVISION = '32279effe8c19989596f05d353d1447f51d9e915'
RELEASE_URL = 'https://github.com/seotro95/seotro/releases/download/voxcpm2-modelpack-40630731327/'
MANIFEST_NAME = 'MODELPACK_MANIFEST.json'
MANIFEST_SHA256 = '88948ee35ab21caf3851b8171f40909885b3327aa1ed440351c5abef24b5fa05'
PROVENANCE_SHA256 = '87e6fb965c2aa58634d47f4eb35a4ff7199f2cc4c5c1ef8b43738b183023f481'
FOLDER = 'voxcpm2-original'
OWNER = {'format': 'voice-studio-public-model-download-v1', 'repository': REPOSITORY, 'revision': REVISION}
BLOCK = 1024 * 1024


def _sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _plain_name(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or '\0' in value:
        raise ValueError('Tên tệp model không an toàn.')
    path = PurePosixPath(value)
    if path.is_absolute() or len(path.parts) != 1 or value in {'.', '..'} or path.name != value:
        raise ValueError('Tên tệp model không an toàn: '+repr(value))
    if value.endswith((' ', '.')) or re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', value):
        raise ValueError('Tên tệp model không tương thích Windows.')
    return value


def _record(record):
    name = _plain_name(record['name'])
    size, digest = record['size'], record['sha256']
    if type(size) is not int or size < 0 or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Thông tin SHA256/kích thước model không hợp lệ.')
    return name, size, digest


def _verified(path, record):
    name, size, digest = _record(record)
    return not path.is_symlink() and path.is_file() and path.stat().st_size == size and _sha256(path) == digest


def _manifest(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > BLOCK or _sha256(path) != MANIFEST_SHA256:
        raise ValueError('SHA256 manifest model không khớp nguồn phát hành.')
    value = json.loads(path.read_text(encoding='utf-8'))
    expected = {'format': 'voice-studio-modelpack-chunks-v1', 'repository': REPOSITORY,
                'revision': REVISION, 'license': 'apache-2.0', 'unpacked_root': FOLDER}
    if any(value.get(key) != field for key, field in expected.items()):
        raise ValueError('Manifest không thuộc phiên bản VoxCPM2 công khai đã chọn.')
    archive = value['archive']
    _record(archive)
    parts = archive['chunks']
    if not isinstance(parts, list) or not 1 <= len(parts) <= 100:
        raise ValueError('Danh sách phần model không hợp lệ.')
    names = []
    for part in parts:
        name, size, _ = _record(part)
        if not name.startswith(archive['name']+'.part') or size <= 0:
            raise ValueError('Phần tải model không hợp lệ.')
        names.append(name.casefold())
    if len(set(names)) != len(names) or sum(part['size'] for part in parts) != archive['size']:
        raise ValueError('Kích thước hoặc tên các phần model không khớp.')
    return value


def _cache(data):
    return Path(data)/'models'/'_public-modelpack'/('voxcpm2-'+REVISION[:12])


def _prepare_cache(data):
    cache = _cache(data)
    # Refuse a redirected cache so replacement/cleanup stays inside its own directory.
    for path in (cache, cache.parent, cache.parent.parent):
        if path.is_symlink():
            raise ValueError('Thư mục tải model không được là liên kết.')
    cache.mkdir(parents=True, exist_ok=True)
    owner = cache/'OWNER.json'
    if owner.is_symlink():
        raise ValueError('Thông tin thư mục tải model không hợp lệ.')
    if owner.exists():
        if json.loads(owner.read_text(encoding='utf-8')) != OWNER:
            raise ValueError('Thư mục tải đang thuộc phiên bản khác.')
    else:
        owner.write_text(json.dumps(OWNER, sort_keys=True)+'\n', encoding='utf-8')
    return cache


def _download(name, destination, expected_size=None, expected_sha256=None):
    _plain_name(name)
    if destination.is_symlink():
        raise ValueError('Tệp tải model không được là liên kết.')
    if destination.is_file():
        if (expected_size is None or destination.stat().st_size == expected_size) and _sha256(destination) == expected_sha256:
            return
    descriptor, temporary = tempfile.mkstemp(prefix=name+'.partial-', dir=destination.parent)
    temporary = Path(temporary)
    try:
        request = urllib.request.Request(RELEASE_URL+name, headers={'User-Agent': 'Voice-Studio-Model-Installer/1.7'})
        digest, total = hashlib.sha256(), 0
        print('Đang tải model công khai: '+name, flush=True)
        with os.fdopen(descriptor, 'wb') as output, urllib.request.urlopen(request, timeout=60) as response:
            for block in iter(lambda: response.read(BLOCK), b''):
                total += len(block)
                if total > (expected_size if expected_size is not None else BLOCK):
                    raise ValueError('Tệp tải model vượt kích thước đã công bố.')
                digest.update(block)
                output.write(block)
        if (expected_size is not None and total != expected_size) or digest.hexdigest() != expected_sha256:
            raise ValueError('SHA256/kích thước phần model tải về không khớp: '+name)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


class ChunkReader(io.RawIOBase):
    """A seekable stream across verified split files; no joined copy on disk."""
    def __init__(self, directory, parts):
        super().__init__()
        self.handles, self.ends, total = [], [], 0
        self.position = 0
        try:
            for part in parts:
                name, size, _ = _record(part)
                self.handles.append((Path(directory)/name).open('rb'))
                total += size
                self.ends.append(total)
        except BaseException:
            self.close()
            raise
        self.total = total

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.position+offset if whence == 1 else self.total+offset if whence == 2 else -1
        if position < 0:
            raise ValueError('Invalid seek')
        self.position = position
        return position

    def read(self, size=-1):
        remaining = max(0, self.total-self.position) if size < 0 else max(0, min(size, self.total-self.position))
        output = bytearray()
        while remaining:
            index = bisect.bisect_right(self.ends, self.position)
            begin = self.ends[index-1] if index else 0
            handle = self.handles[index]
            handle.seek(self.position-begin)
            block = handle.read(min(remaining, self.ends[index]-self.position))
            if not block:
                raise OSError('Phần model bị cắt ngắn trong khi đọc.')
            output.extend(block)
            remaining -= len(block)
            self.position += len(block)
        return bytes(output)

    def close(self):
        for handle in self.handles:
            handle.close()
        super().close()


def _verify_archive(cache, archive):
    total, overall = 0, hashlib.sha256()
    for part in archive['chunks']:
        name, size, expected = _record(part)
        file = cache/name
        if file.is_symlink() or not file.is_file() or file.stat().st_size != size:
            raise ValueError('Phần model bị thiếu hoặc tải chưa đủ: '+name)
        digest = hashlib.sha256()
        with file.open('rb') as source:
            for block in iter(lambda: source.read(BLOCK), b''):
                total += len(block)
                digest.update(block)
                overall.update(block)
        if digest.hexdigest() != expected:
            raise ValueError('SHA256 phần model không khớp: '+name)
    if total != archive['size'] or overall.hexdigest() != archive['sha256']:
        raise ValueError('SHA256 bộ model đầy đủ không khớp.')


def _validate_source(source):
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Thư mục nguồn model không hợp lệ.')
    provenance_path = source/'MODEL_PROVENANCE.json'
    if provenance_path.is_symlink() or provenance_path.stat().st_size > 4*BLOCK or _sha256(provenance_path) != PROVENANCE_SHA256:
        raise ValueError('Thông tin nguồn model không hợp lệ.')
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    if any(provenance.get(key) != value for key, value in
           {'repository': REPOSITORY, 'revision': REVISION, 'license': 'apache-2.0', 'weights_and_config_unchanged': True}.items()):
        raise ValueError('Nguồn/phiên bản/giấy phép model không khớp.')
    files = provenance['files']
    if not isinstance(files, list) or not 1 <= len(files) <= 1000:
        raise ValueError('Danh sách tệp nguồn model không hợp lệ.')
    names = set()
    for record in files:
        name, _, _ = _record(record)
        if name.casefold() in names or name == 'MODEL_PROVENANCE.json':
            raise ValueError('Tên tệp nguồn model bị trùng.')
        names.add(name.casefold())
        if not _verified(source/name, record):
            raise ValueError('SHA256 tệp nguồn model không khớp: '+name)
    if not {'config.json'} <= names or not {'model.safetensors', 'pytorch_model.bin'} & names or not {'audiovae.safetensors', 'audiovae.pth'} & names:
        raise ValueError('Nguồn model thiếu config, model hoặc AudioVAE.')
    if any(file.is_symlink() or not file.is_file() or file.name.casefold() not in names|{'model_provenance.json'} for file in source.iterdir()):
        raise ValueError('Nguồn model có tệp ngoài manifest.')
    config = json.loads((source/'config.json').read_text(encoding='utf-8'))
    if str(config.get('architecture', '')).lower() != 'voxcpm2':
        raise ValueError('Config nguồn không phải VoxCPM2.')
    return source


def _extract(cache, manifest, models):
    destination = models/FOLDER
    temporary = Path(tempfile.mkdtemp(prefix='.voxcpm2-extract-', dir=models))
    try:
        with ChunkReader(cache, manifest['archive']['chunks']) as reader, zipfile.ZipFile(reader) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 1001:
                raise ValueError('Số tệp trong ZIP model không hợp lệ.')
            seen, expanded = set(), 0
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if len(path.parts) != 2 or path.parts[0] != FOLDER or entry.is_dir():
                    raise ValueError('Đường dẫn ZIP model không an toàn.')
                name = _plain_name(path.parts[1])
                if entry.filename != FOLDER+'/'+name or name.casefold() in seen:
                    raise ValueError('Tên tệp ZIP model không an toàn hoặc trùng.')
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    raise ValueError('ZIP model chứa liên kết hoặc tệp mã hóa.')
                seen.add(name.casefold())
                expanded += entry.file_size
                if expanded > max(16*BLOCK, manifest['archive']['size']*2):
                    raise ValueError('ZIP model vượt giới hạn kích thước giải nén.')
                with archive.open(entry) as source, (temporary/name).open('xb') as output:
                    shutil.copyfileobj(source, output, BLOCK)  # ZipExtFile verifies each CRC at EOF.
        _validate_source(temporary)
        if destination.exists() or destination.is_symlink():
            raise ValueError('Thư mục model xuất hiện trong khi giải nén; không ghi đè.')
        temporary.rename(destination)
        return destination
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def ensure_model_source(data: Path) -> Path:
    """Download, verify and atomically extract the pinned original public model."""
    destination = Path(data)/'models'/FOLDER
    if destination.exists() or destination.is_symlink():
        return _validate_source(destination)
    cache = _prepare_cache(data)
    _download(MANIFEST_NAME, cache/MANIFEST_NAME, expected_sha256=MANIFEST_SHA256)
    manifest = _manifest(cache/MANIFEST_NAME)
    for part in manifest['archive']['chunks']:
        _download(part['name'], cache/part['name'], part['size'], part['sha256'])
    print('Đang kiểm tra SHA256 và giải nén model công khai...', flush=True)
    _verify_archive(cache, manifest['archive'])
    return _extract(cache, manifest, destination.parent)


def cleanup_download_parts(data):
    """Remove only this installer's pinned assets after a successful model probe."""
    data = Path(data)
    marker = data/'models/voxcpm.ready'
    cache = _cache(data)
    if not marker.is_file() or marker.is_symlink() or not cache.is_dir() or any(path.is_symlink() for path in (cache, cache.parent, cache.parent.parent)):
        return False
    try:
        ready = json.loads(marker.read_text(encoding='utf-8'))
        if ready.get('repository') != REPOSITORY or ready.get('revision') != REVISION or ready.get('verified_thai_frames', 0) < 2400:
            return False
        if (cache/'OWNER.json').is_symlink() or json.loads((cache/'OWNER.json').read_text(encoding='utf-8')) != OWNER:
            return False
        manifest = _manifest(cache/MANIFEST_NAME)
    except (OSError, ValueError, KeyError, TypeError):
        return False
    for part in manifest['archive']['chunks']:
        file = cache/part['name']
        if not file.is_symlink() and file.is_file():
            file.unlink()
    return True
