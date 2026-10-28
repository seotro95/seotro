"""Install a private voice update into an existing Windows portable installation.

This file is copied to the update ZIP as ``install_update.py``. It deliberately
uses only Python's standard library and never downloads or publishes recordings.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import sys
import uuid
import wave


ROOT_FILES = frozenset({
    'MO_TOOL.bat', 'TAI_GIONG_DA_NGON_NGU.bat', 'DOC_TRUOC.md',
    'HUONG_DAN_CAN_MOC.txt', 'THIRD_PARTY_NOTICES.md',
    'requirements-international.txt', 'requirements-runtime.txt',
    'requirements-qwen.txt', 'BUILD_INFO.json', 'MANIFEST.sha256',
})
LANGUAGES = frozenset({'en-US', 'en-GB', 'ko', 'ru', 'ja', 'fr', 'es', 'th'})
IDENTIFIER = re.compile(r'[0-9a-f]{32}')
DIGEST = re.compile(r'[0-9a-f]{64}')
MAX_MANIFEST = 2 * 1024 * 1024
MAX_AUDIO = 128 * 1024 * 1024


def _relative(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or any(character in value for character in ':\x00<>"|?*')
            or any(part in {'', '.', '..'} or part != part.rstrip(' .')
                   or PureWindowsPath(part).is_reserved() for part in value.split('/'))):
        raise ValueError('Đường dẫn trong gói cập nhật không hợp lệ.')
    path = PurePosixPath(value)
    if path.is_absolute():
        raise ValueError('Đường dẫn trong gói cập nhật phải là đường dẫn tương đối.')
    return path


def _contained(root, relative):
    """Reject links/junctions even when they point inside the installation."""
    path = root
    for part in _relative(relative).parts:
        path = path / part
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Không cập nhật qua liên kết thư mục hoặc tệp.')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Đường dẫn cập nhật nằm ngoài thư mục đã chọn.')
    return path


def _regular_file(root, relative, maximum=None):
    path = _contained(root, relative)
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Thiếu tệp thường trong gói cập nhật: ' + relative)
    if maximum is not None and path.stat().st_size > maximum:
        raise ValueError('Tệp trong gói cập nhật quá lớn: ' + relative)
    return path


def _sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def _read_manifest(root):
    path = _regular_file(root, 'manifest.json', MAX_MANIFEST)
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError, ValueError) as exc:
        raise ValueError('Không đọc được manifest thư viện giọng.') from exc
    if (not isinstance(value, dict) or type(value.get('schema_version')) is not int
            or value['schema_version'] != 1 or not isinstance(value.get('voices'), list)):
        raise ValueError('Manifest thư viện giọng không đúng định dạng phiên bản 1.')
    identifiers = set()
    for record in value['voices']:
        if not isinstance(record, dict):
            raise ValueError('Hồ sơ giọng không hợp lệ.')
        ident, name = record.get('id'), record.get('name')
        if (not isinstance(ident, str) or not IDENTIFIER.fullmatch(ident)
                or ident in identifiers or not isinstance(name, str)
                or not 1 <= len(name.strip()) <= 80
                or any(ord(character) < 32 or ord(character) == 127 for character in name)
                or record.get('language') not in LANGUAGES):
            raise ValueError('Mã, tên hoặc ngôn ngữ của giọng trong manifest không hợp lệ.')
        engine = 'vieneu' if record['language'].startswith('en-') else 'voxcpm'
        if record.get('engine', engine) != engine:
            raise ValueError('Bộ tạo giọng trong manifest không khớp ngôn ngữ.')
        identifiers.add(ident)
    if 'count' in value and value['count'] != len(value['voices']):
        raise ValueError('Số giọng trong manifest không khớp danh sách.')
    return value


def _verify_digest(path, expected):
    if not isinstance(expected, str) or not DIGEST.fullmatch(expected) or _sha256(path) != expected:
        raise ValueError('SHA256 của tệp giọng không khớp; hãy tải lại gói cập nhật.')


def _verify_voice(pack, record):
    ident = record['id']
    reference = record.get('reference_audio')
    original = record.get('original_audio')
    # Stable filenames prevent new records from colliding with another voice.
    if reference != f'voices/{ident}.wav' or original != f'originals/{ident}.mp3':
        raise ValueError('Tên tệp mẫu giọng không khớp mã giọng trong manifest.')
    wav = _regular_file(pack, reference, 64 * 1024 * 1024)
    mp3 = _regular_file(pack, original, MAX_AUDIO)
    _verify_digest(wav, record.get('reference_sha256'))
    _verify_digest(mp3, record.get('source_sha256', record.get('original_sha256')))
    if 'source_bytes' in record and record['source_bytes'] != mp3.stat().st_size:
        raise ValueError('Kích thước MP3 gốc không khớp manifest.')
    try:
        with wave.open(str(wav), 'rb') as audio:
            frames, rate = audio.getnframes(), audio.getframerate()
            channels, width = audio.getnchannels(), audio.getsampwidth()
            duration = frames / rate if rate else 0
            if (audio.getcomptype() != 'NONE' or channels not in {1, 2}
                    or width not in {1, 2, 3, 4} or not 8000 <= rate <= 192000
                    or not 3 <= duration <= 30):
                raise ValueError('Mẫu giọng phải là WAV PCM dài từ 3 đến 30 giây.')
            count = 0
            while block := audio.readframes(65536):
                count += len(block)
            if count != frames * channels * width:
                raise ValueError('Dữ liệu PCM trong mẫu giọng bị thiếu.')
    except (wave.Error, EOFError) as exc:
        raise ValueError('Không đọc được mẫu giọng WAV PCM.') from exc
    for key, actual in (('reference_frames', frames), ('reference_sample_rate', rate)):
        if key in record and record[key] != actual:
            raise ValueError('Thông số WAV không khớp manifest.')
    if 'duration' in record:
        declared = record['duration']
        if (isinstance(declared, bool) or not isinstance(declared, (int, float))
                or not math.isfinite(declared) or not math.isclose(declared, duration, abs_tol=1e-6)):
            raise ValueError('Thời lượng WAV không khớp manifest.')
    return [(reference, wav), (original, mp3)]


def _payload_files(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Gói cập nhật thiếu thư mục payload.')
    result = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        _contained(root, relative)
        if path.is_dir():
            continue
        parts = _relative(relative).parts
        permitted = (relative in ROOT_FILES or
                     len(parts) == 2 and parts[0] == 'app' and path.suffix == '.py' or
                     len(parts) >= 3 and parts[:2] == ('app', 'static'))
        if not permitted:
            raise ValueError('Tệp ngoài phạm vi cập nhật được phép: ' + relative)
        result.append((relative, _regular_file(root, relative, 64 * 1024 * 1024)))
    if not any(relative == 'app/app.py' for relative, _ in result):
        raise ValueError('Gói cập nhật thiếu app/app.py.')
    return result


@contextmanager
def installation_lock(target):
    data = _contained(target, 'app/.data')
    data.mkdir(parents=True, exist_ok=True)
    path = _contained(target, 'app/.data/server.lock')
    handle = path.open('a+b')
    try:
        if handle.seek(0, 2) == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Voice Studio đang chạy. Hãy đóng tool rồi chạy cập nhật lại.') from exc
        yield
    finally:
        handle.close()


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def _merged_manifest(existing, incoming):
    merged = dict(existing or incoming)
    records = {voice['id']: voice for voice in (existing or {}).get('voices', [])}
    records.update({voice['id']: voice for voice in incoming['voices']})
    merged.update(schema_version=1, voices=list(records.values()), count=len(records))
    merged['privacy'] = 'private-do-not-publish'
    return merged


def _atomic_copy(source, destination):
    temporary = destination.with_name(destination.name + '.update-' + uuid.uuid4().hex)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _apply(target, operations, expected_digests=None):
    """Stage everything before replacing any file, retaining recoverable backups."""
    changed = []
    for relative, source in operations:
        destination = _contained(target, relative)
        if destination.exists() and not destination.is_file():
            raise ValueError('Đích cập nhật đã tồn tại nhưng không phải tệp: ' + relative)
        digest = hashlib.sha256(source).hexdigest() if isinstance(source, bytes) else _sha256(source)
        if expected_digests and relative in expected_digests and digest != expected_digests[relative]:
            raise ValueError('Tệp giọng đã thay đổi trong khi chuẩn bị cập nhật.')
        if destination.is_file() and _sha256(destination) == digest:
            continue
        changed.append((relative, source, digest))
    if not changed:
        return {'updated_files': 0, 'backup': None}
    backup_parent = _contained(target, 'update-backups')
    backup_parent.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    backup = backup_parent / stamp
    backup.mkdir()
    staged, applied, created_directories, journal = backup/'staged', [], [], []
    try:
        for relative, source, expected in changed:
            destination = _contained(target, relative)
            staged_file = staged / relative
            staged_file.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(source, bytes):
                staged_file.write_bytes(source)
            else:
                shutil.copy2(source, staged_file)
            if _sha256(staged_file) != expected:
                raise ValueError('Tệp đã thay đổi hoặc sao chép không toàn vẹn; chưa áp dụng cập nhật.')
            existed = destination.exists()
            if existed:
                saved = backup/'files'/relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, saved)
            journal.append({'path': relative, 'existed': existed,
                            'new_sha256': _sha256(staged_file)})
        (backup/'journal.json').write_bytes(_json_bytes({'status': 'staged', 'files': journal}))
        for record in journal:
            relative = record['path']
            destination = _contained(target, relative)
            missing = []
            parent = destination.parent
            while parent != target and not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                created_directories.append(directory)
            os.replace(staged/relative, destination)
            applied.append(record)
        (backup/'journal.json').write_bytes(_json_bytes({'status': 'complete', 'files': journal}))
    except BaseException as exc:
        failures = []
        for record in reversed(applied):
            try:
                destination = _contained(target, record['path'])
                if record['existed']:
                    _atomic_copy(backup/'files'/record['path'], destination)
                else:
                    destination.unlink(missing_ok=True)
            except (OSError, ValueError) as rollback_error:
                failures.append(str(rollback_error))
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                pass
        (backup/'journal.json').write_bytes(_json_bytes(
            {'status': 'rollback-incomplete' if failures else 'rolled-back',
             'files': journal, 'rollback_errors': failures}))
        if failures:
            raise RuntimeError('Cập nhật lỗi và cần khôi phục từ bản sao: ' + str(backup)) from exc
        raise
    finally:
        shutil.rmtree(staged, ignore_errors=True)
    return {'updated_files': len(changed), 'backup': str(backup)}


def install_update(package_root, target):
    package = Path(package_root).resolve(strict=True)
    destination = Path(target).expanduser().resolve(strict=True)
    if not destination.is_dir():
        raise ValueError('Chọn thư mục của bản Voice Studio Portable đã giải nén.')
    _regular_file(destination, 'runtime/python.exe')
    _regular_file(destination, 'app/app.py')
    pack = _contained(package, 'voice-pack')
    incoming = _read_manifest(pack)
    if not incoming['voices']:
        raise ValueError('Gói cập nhật không chứa giọng nào.')
    voices = []
    for record in incoming['voices']:
        voices.extend(_verify_voice(pack, record))
    payload = _payload_files(_contained(package, 'payload'))
    with installation_lock(destination):
        library = _contained(destination, 'app/voice-library')
        existing = _read_manifest(library) if _contained(library, 'manifest.json').exists() else None
        operations = payload + [('app/voice-library/' + relative, source) for relative, source in voices]
        operations.append(('app/voice-library/manifest.json', _json_bytes(_merged_manifest(existing, incoming))))
        expected_digests = {}
        for record in incoming['voices']:
            expected_digests['app/voice-library/' + record['reference_audio']] = record['reference_sha256']
            expected_digests['app/voice-library/' + record['original_audio']] = record.get('source_sha256', record.get('original_sha256'))
        result = _apply(destination, operations, expected_digests)
    return {**result, 'installed_voices': len(incoming['voices']),
            'catalog_voices': len(_merged_manifest(existing, incoming)['voices'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Cập nhật giọng mặc định riêng vào Voice Studio Portable')
    parser.add_argument('--target', required=True, type=Path,
                        help='Thư mục bản Portable có runtime/python.exe và app/app.py')
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent,
                        help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        result = install_update(args.package, args.target)
    except (OSError, ValueError, RuntimeError) as exc:
        print('Không cập nhật được: ' + str(exc), file=sys.stderr, flush=True)
        return 1
    print(f"Đã cài {result['installed_voices']} giọng mặc định riêng; thư viện có {result['catalog_voices']} giọng.", flush=True)
    if result['backup']:
        print('Bản sao trước cập nhật: ' + result['backup'], flush=True)
    else:
        print('Các tệp đã đúng phiên bản; không cần ghi lại.', flush=True)
    print('Mở MO_TOOL.bat. Chạy TAI_GIONG_DA_NGON_NGU.bat một lần để chuẩn bị các giọng quốc tế.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
