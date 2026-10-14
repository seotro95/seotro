"""Verified updates before startup, with rollback and backups of changed source files."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VIDEO_STUDIO_DATA', str(ROOT / 'data'))).expanduser().resolve()
BASE = 'https://github.com/seotro95/seotro/raw/refs/heads/video-studio-vn/releases/'
MANIFEST = BASE + 'latest.json'
DEFAULTS = {'auto_update':True, 'last_checked':0, 'update_requested':False}


def settings():
    path = DATA / 'settings.json'
    try:
        return {**DEFAULTS, **json.loads(path.read_text(encoding='utf-8'))}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save_settings(changes):
    DATA.mkdir(parents=True, exist_ok=True)
    current = {**settings(), **changes}
    temporary = DATA / 'settings.tmp'
    temporary.write_text(json.dumps(current, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, DATA / 'settings.json')
    return current


def version_tuple(version):
    parts = version.split('.')
    if len(parts) != 3 or any(not p.isdigit() or len(p) > 5 for p in parts):
        raise ValueError('Số phiên bản không hợp lệ.')
    return tuple(map(int, parts))


def local_version():
    return json.loads((ROOT / 'version.json').read_text(encoding='utf-8'))['version']


def remote_manifest():
    request = urllib.request.Request(MANIFEST, headers={'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request, timeout=10) as response:
        manifest = json.loads(response.read(65537))
    version_tuple(manifest['version'])
    digest = manifest['sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Checksum bản cập nhật không hợp lệ.')
    if manifest.get('filename') != 'VideoStudioVN-' + manifest['version'] + '.zip':
        raise ValueError('Tên gói cập nhật không hợp lệ.')
    return manifest


def check_update():
    try:
        remote = remote_manifest()
        return {'current':local_version(),'latest':remote['version'],
                'available':version_tuple(remote['version']) > version_tuple(local_version()),
                'message':'Đã kiểm tra phiên bản trên GitHub.'}
    except Exception:
        return {'current':local_version(),'latest':None,'available':False,
                'message':'Không kết nối được máy chủ cập nhật. Các model đã tải vẫn dùng được offline.'}


def download_archive(manifest, target):
    digest, count = hashlib.sha256(), 0
    with urllib.request.urlopen(BASE + manifest['filename'], timeout=30) as source, target.open('wb') as out:
        while chunk := source.read(1024 * 1024):
            count += len(chunk)
            if count > 20 * 1024 ** 2:
                raise ValueError('Gói cập nhật vượt giới hạn 20 MB.')
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != manifest['sha256']:
        raise ValueError('Checksum bản cập nhật không khớp; tiếp tục dùng bản hiện tại.')


def apply_archive(archive, manifest):
    """Replace shipped code only; never replace media, models, environment or executables."""
    extensions = {'.py','.js','.css','.html','.txt','.md','.bat','.json'}
    required = {'app.py','engine.py','launcher.py','requirements.txt','version.json','static/index.html'}
    DATA.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DATA) as scratch:
        staging = Path(scratch)
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None or sum(e.file_size for e in bundle.infolist()) > 50 * 1024 ** 2:
                raise ValueError('Gói cập nhật lỗi hoặc quá lớn.')
            files = []
            for entry in bundle.infolist():
                parts = Path(entry.filename).parts
                if len(parts) < 2 or parts[0] != 'video-studio' or '..' in parts or '\\' in entry.filename:
                    raise ValueError('Đường dẫn trong gói cập nhật không hợp lệ.')
                relative = Path(*parts[1:])
                if relative.parts[0] in ('data','.venv','bin','models') or ((entry.external_attr >> 16) & 0o170000) == 0o120000:
                    raise ValueError('Gói cập nhật không được thay dữ liệu hoặc môi trường.')
                if entry.is_dir():
                    continue
                if relative.suffix not in extensions and relative.name != '.gitignore':
                    raise ValueError('Loại tệp cập nhật không được hỗ trợ.')
                if not (ROOT / relative).resolve().is_relative_to(ROOT.resolve()):
                    raise ValueError('Đường dẫn cập nhật thoát khỏi thư mục tool.')
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(entry))
                if relative in files:
                    raise ValueError('Gói cập nhật có tên tệp trùng lặp.')
                files.append(relative)
        if not required.issubset({str(p).replace('\\','/') for p in files}):
            raise ValueError('Gói cập nhật thiếu tệp bắt buộc.')
        if json.loads((staging / 'version.json').read_text())['version'] != manifest['version']:
            raise ValueError('Phiên bản bên trong gói không khớp.')
        backup = DATA / 'update-backups' / (local_version() + '-' + str(time.time_ns()))
        backup.mkdir(parents=True)
        applied = []
        # The version marker is committed last.
        files.sort(key=lambda p: p.name == 'version.json')
        try:
            for relative in files:
                target = ROOT / relative
                if target.exists():
                    saved = backup / relative
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, saved)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + '.update-tmp')
                if temporary.exists():
                    raise ValueError('Có tệp cập nhật tạm chưa được xử lý; chưa ghi đè.')
                try:
                    shutil.copyfile(staging / relative, temporary)
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
                applied.append(relative)
        except Exception:
            for relative in reversed(applied):
                target, saved = ROOT / relative, backup / relative
                if saved.exists():
                    shutil.copy2(saved, target)
                else:
                    target.unlink(missing_ok=True)
            raise
    return 'Đã cập nhật lên ' + manifest['version'] + '. Bản cũ được giữ trong data/update-backups.'


def startup_update(force=False):
    current = settings()
    if os.environ.get('VIDEO_STUDIO_AUTO_UPDATE') == '0' and not force:
        return 'Đã tắt cập nhật mã nguồn cho môi trường phát triển.'
    requested = force or current.get('update_requested')
    if not requested and (not current['auto_update'] or time.time() - current['last_checked'] < 86400):
        return 'Tiếp tục dùng bản hiện tại.'
    DATA.mkdir(parents=True, exist_ok=True)
    lock = DATA / '.update-lock'
    try:
        lock.mkdir()
    except FileExistsError:
        return 'Một phiên khác đang cập nhật; chưa thay đổi tệp.'
    try:
        manifest = remote_manifest()
        save_settings({'last_checked':time.time(), 'update_requested':False})
        if version_tuple(manifest['version']) <= version_tuple(local_version()):
            return 'Tool đang dùng phiên bản mới nhất.'
        with tempfile.TemporaryDirectory(dir=DATA) as scratch:
            archive = Path(scratch) / 'update.zip'
            download_archive(manifest, archive)
            return apply_archive(archive, manifest)
    except Exception:
        return 'Chưa cập nhật được; tiếp tục dùng bản hiện tại. Có thể thử lại bằng cap_nhat.bat.'
    finally:
        lock.rmdir()
