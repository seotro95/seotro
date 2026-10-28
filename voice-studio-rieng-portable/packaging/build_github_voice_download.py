"""Repackage a verified Windows release with a password-encrypted voice update.

Only ciphertext enters GitHub. This builder has no decryption operation, password
argument or access to private reference recordings. The base runtime, code, model
weights and licenses are copied byte for byte from the checked public release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import stat
import tempfile
import unittest
import urllib.request
import zipfile


BASE_URL = ('https://github.com/seotro95/seotro/releases/download/'
            'voice-studio-rieng-1.7-portable-40648603647/'
            'Voice-Studio-Rieng-1.7.0-Portable-Windows-x64.zip')
BASE_SHA256 = 'b8a089d2431a743c5b3f3c68692c2075bae59bf2715c15d4531ec46b1c6900a4'
BASE_ROOT = 'Voice-Studio-Rieng-1.7.0-Portable'
ROOT = 'Voice-Studio-Rieng-1.7.0-19-Giong-GitHub'
FILENAME = ROOT+'-Windows-x64.zip'
UPDATE_ROOT = 'Voice-Studio-Rieng-1.7.0-Cap-Nhat-19-Giong-GitHub'
UPDATE_FILENAME = UPDATE_ROOT+'.zip'
REPAIR_ROOT = 'Voice-Studio-Sua-Loi-Nhap-Mat-Khau'
REPAIR_FILENAME = REPAIR_ROOT+'.zip'
REPAIR_FILES = ('SUA_LOI_CAI_19_GIONG.bat', 'install_secure_voices.ps1')
BLOCK = 1024*1024
DELIVERY_FILES = ('CAI_19_GIONG.bat', 'install_secure_voices.ps1',
                  'delivery/manifest.json', 'delivery/voices.vspack')
README = '''VOICE STUDIO RIÊNG 1.7.0 - 19 GIỌNG - TẢI TỪ GITHUB

1. Tải ZIP đầy đủ này từ GitHub, rồi giải nén TOÀN BỘ vào thư mục mới.
   Không chạy trực tiếp trong cửa sổ xem nội dung ZIP.
2. Mở CAI_19_GIONG.bat. Trong cửa sổ nhập mật khẩu, bấm nút Dán để dán
   mật khẩu đã sao chép từ cuộc trò chuyện, rồi bấm Cài đặt.
   Gói giọng được mã hóa để bản thu riêng không xuất hiện công khai trên GitHub.
3. Khi báo cài xong 19 giọng, mở MO_TOOL.bat. Có thể nghe thử từng mẫu.

Nếu tool đang mở, hãy đóng tool rồi chạy lại CAI_19_GIONG.bat.
Mật khẩu không được lưu trong gói hoặc trang GitHub. Hãy giữ lại mật khẩu.

Ba giọng tiếng Anh dùng bộ Turbo đi kèm. Các mẫu Hàn, Nga, Nhật, Pháp,
Tây Ban Nha và Thái cần chạy TAI_GIONG_DA_NGON_NGU.bat một lần khi có Internet.
Bộ này tải model khoảng 5 GB và thư viện CPU vào runtime riêng.
Nên để trống ít nhất 15 GB cho lần tải/cài đầu; sau đó mở lại MO_TOOL.bat.
Tốc độ phụ thuộc CPU và nội dung; chưa bảo đảm tạo 1 giờ voice trong 2 phút.
Giọng tạo theo mẫu cần được nghe kiểm tra độ giống, phát âm và cảm xúc.

TXT/SRT được xử lý bởi bản 1.7 đã kiểm tra trên Windows. Mốc SRT được giữ
và lời được căn trong từng ô; ô quá ngắn có thể làm lời đọc nhanh hơn.
Không nhập nội dung bí mật hoặc mật khẩu vào trang GitHub.
'''
UPDATE_README = '''VOICE STUDIO RIÊNG - CẬP NHẬT 19 GIỌNG TỪ GITHUB

1. Giải nén TOÀN BỘ ZIP này ra thư mục mới. Đóng Voice Studio đang chạy.
2. Mở CAI_19_GIONG.bat, dùng nút Dán trong cửa sổ nhập mật khẩu rồi bấm Cài đặt.
3. Chọn thư mục Voice Studio Portable cũ có thư mục runtime và app.
4. Khi báo cài xong, mở MO_TOOL.bat trong thư mục tool vừa chọn.

Gói mã hóa bảo vệ bản thu riêng khi tải qua GitHub; mật khẩu không nằm trên
GitHub và không được lưu trong ZIP. Hãy giữ lại mật khẩu.
Gói này chỉ mở thư viện giọng trong bản Portable đang dùng; không thay mã ứng dụng bằng bản cũ. Dùng ZIP đầy đủ mới khi muốn nâng cấp ứng dụng. Lịch sử, model và giọng cá nhân đang có được giữ lại.

Ba giọng tiếng Anh dùng Turbo đi kèm bản Portable đầy đủ. Các giọng Hàn, Nga,
Nhật, Pháp, Tây Ban Nha và Thái cần chạy TAI_GIONG_DA_NGON_NGU.bat một lần
trong thư mục tool khi có Internet để tải khoảng 5 GB model cùng thư viện CPU.
Nên để trống ít nhất 15 GB cho lần tải/cài đầu. Sau đó mở lại MO_TOOL.bat.
Tốc độ 2 phút tạo 1 giờ voice chưa được bảo đảm; cần nghe kiểm tra giọng tạo.
'''
REPAIR_README = '''VOICE STUDIO - SỬA BƯỚC DÁN MẬT KHẨU CÀI 19 GIỌNG

Dùng gói nhỏ này nếu đã tải và giải nén bản đầy đủ nhưng cửa sổ dòng lệnh
báo mật khẩu chưa đúng. Không cần tải lại bản đầy đủ hoặc các model.

1. Giải nén TOÀN BỘ ZIP sửa lỗi này vào một thư mục mới.
2. Đóng Voice Studio, mở SUA_LOI_CAI_19_GIONG.bat.
3. Chọn thư mục bản đầy đủ đã giải nén, có runtime, app và delivery.
4. Sao chép mật khẩu được gửi trong chat. Trong cửa sổ nhập mật khẩu,
   bấm nút Dán; có thể bật Hiện mật khẩu để kiểm tra, rồi bấm Cài đặt.
5. Khi cài xong, mở MO_TOOL.bat trong thư mục tool đã chọn.

Mật khẩu vẫn là mật khẩu đã gửi riêng trong cuộc trò chuyện. Gói sửa lỗi
không chứa mật khẩu hoặc bản thu; nó mở gói giọng sẵn có trên máy bạn.
Lịch sử, model và các giọng cá nhân đang có được giữ lại.

Các giọng quốc tế cần bộ đọc đã chuẩn bị bằng TAI_GIONG_DA_NGON_NGU.bat.
Nếu chưa chuẩn bị, chạy tệp đó một lần có Internet để tải model cùng thư viện.
'''


def sha256(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def safe_path(value):
    if (not isinstance(value, str) or not value or '\\' in value or
            any(character in value for character in '\x00:<>"|?*')):
        raise ValueError('Unsafe archive path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {'', '.', '..'} or
            part != part.rstrip(' .') or PureWindowsPath(part).is_reserved()
            for part in value.rstrip('/').split('/')):
        raise ValueError('Unsafe archive path')
    return path


def verify_delivery(directory):
    directory = Path(directory)
    for name in DELIVERY_FILES:
        file = directory/name
        if file.is_symlink() or not file.is_file():
            raise ValueError('Missing regular delivery file: '+name)
        for parent in file.parents:
            if parent == directory.parent:
                break
            if parent.is_symlink():
                raise ValueError('Delivery paths must not be symlinks')
    manifest = json.loads((directory/'delivery/manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('format') != 'voice-studio-private-delivery-v1' or
            manifest.get('encrypted_file') != 'voices.vspack' or
            manifest.get('updater_root') != 'Voice-Studio-Rieng-1.7.0-Cap-Nhat-19-Giong'):
        raise ValueError('Unsupported encrypted delivery manifest')
    encrypted = directory/'delivery/voices.vspack'
    if (type(manifest.get('encrypted_size')) is not int or
            encrypted.stat().st_size != manifest['encrypted_size'] or
            encrypted.stat().st_size < 96 or sha256(encrypted) != manifest.get('encrypted_sha256')):
        raise ValueError('Encrypted voice package size/SHA256 mismatch')
    with encrypted.open('rb') as source:
        if source.read(8) != b'VSPACK01':
            raise ValueError('Encrypted voice package header mismatch')
    # The public metadata is deliberately restricted to format and checksums.
    # Names, transcripts and original audio hashes stay inside the ciphertext.
    if set(manifest) != {'format', 'encrypted_file', 'encrypted_sha256', 'encrypted_size',
                        'plaintext_sha256', 'plaintext_size', 'updater_root'}:
        raise ValueError('Unexpected private metadata in public delivery manifest')
    if (type(manifest.get('plaintext_size')) is not int or not 0 < manifest['plaintext_size'] < 128*BLOCK or
            not isinstance(manifest.get('plaintext_sha256'), str) or
            len(manifest['plaintext_sha256']) != 64 or
            any(character not in '0123456789abcdef' for character in manifest['plaintext_sha256'])):
        raise ValueError('Invalid decrypted package size/SHA256 metadata')
    return manifest


def download_base(path):
    path = Path(path)
    if path.is_file() and sha256(path) == BASE_SHA256:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name+'.partial')
    try:
        with urllib.request.urlopen(BASE_URL, timeout=120) as source, pending.open('wb') as output:
            shutil.copyfileobj(source, output, BLOCK)
        if sha256(pending) != BASE_SHA256:
            raise ValueError('Public Windows base SHA256 mismatch')
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)
    return path


def _new_entry(name, size, root=ROOT):
    entry = zipfile.ZipInfo(root+'/'+name, (1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry._compresslevel = 6
    entry.external_attr = 0o100644 << 16
    entry.file_size = size
    return entry


def build_bundle(base_archive, delivery, output, expected_base=BASE_SHA256,
                 base_root=BASE_ROOT, root_name=ROOT, expected_version='1.7.0'):
    base_archive, delivery, output = Path(base_archive), Path(delivery), Path(output)
    if not base_archive.is_file() or sha256(base_archive) != expected_base:
        raise ValueError('Public Windows base SHA256 mismatch; refusing to package')
    manifest = verify_delivery(delivery)
    output.mkdir(parents=True, exist_ok=True)
    destination = output/(root_name+'-Windows-x64.zip')
    if destination.exists():
        raise ValueError('Refusing to overwrite an existing GitHub package')
    pending = destination.with_name(destination.name+'.partial')
    hashes, reused, seen = {}, 0, set()
    try:
        with zipfile.ZipFile(base_archive) as original, zipfile.ZipFile(
                pending, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as target:
            entries = original.infolist()
            old_names = {entry.filename for entry in entries}
            if len(old_names) != len(entries):
                raise ValueError('Duplicate names in public Windows base')
            build = json.loads(original.read(base_root+'/BUILD_INFO.json'))
            if build.get('version') != expected_version or not build.get('bundled_runtime'):
                raise ValueError('Unexpected Windows base version/runtime')
            required = {'runtime/python.exe', 'app/app.py', 'MO_TOOL.bat',
                        'TAI_GIONG_DA_NGON_NGU.bat'}
            for entry in entries:
                path = safe_path(entry.filename)
                if path.parts[0] != base_root:
                    raise ValueError('Unexpected public Windows base root')
                if entry.is_dir():
                    continue
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    raise ValueError('Unsupported encrypted/link entry in Windows base')
                relative = '/'.join(path.parts[1:])
                if not relative or relative.casefold() in seen:
                    raise ValueError('Duplicate or empty Windows base path')
                seen.add(relative.casefold())
                if relative.startswith(('app/voice-library/', 'app/.data/voices/')):
                    raise ValueError('Public base unexpectedly contains private voices')
                if relative in {'BUILD_INFO.json', 'MANIFEST.sha256'}:
                    continue
                if relative in DELIVERY_FILES or relative == 'README_GITHUB_19_GIONG.txt':
                    raise ValueError('Base conflicts with encrypted delivery files')
                digest = hashlib.sha256()
                new = _new_entry(relative, entry.file_size, root_name)
                with original.open(entry) as source, target.open(new, 'w', force_zip64=True) as sink:
                    for block in iter(lambda: source.read(BLOCK), b''):
                        digest.update(block)
                        sink.write(block)
                hashes[relative] = digest.hexdigest()
                reused += 1
            if not required <= hashes.keys():
                raise ValueError('Public Windows base lacks required launch files')
            build.update(encrypted_private_pack_bundled=True, private_voice_library_bundled=False,
                         encrypted_private_voice_count=19, private_voice_unlock_required=True,
                         github_delivery_source_commit=os.environ.get('GITHUB_SHA'),
                         verified_public_base_sha256=expected_base,
                         private_delivery_format=manifest['format'],
                         private_delivery_plaintext_published=False)
            additional = {'BUILD_INFO.json': (json.dumps(build, ensure_ascii=False, indent=2)+'\n').encode(),
                          'README_GITHUB_19_GIONG.txt': README.replace('1.7.0', expected_version).replace('bản 1.7', 'bản '+expected_version.rsplit('.', 1)[0]).encode('utf-8')}
            for relative in DELIVERY_FILES:
                file = delivery/relative
                content = file.read_bytes()
                additional[relative] = content
            for relative, content in additional.items():
                target.writestr(_new_entry(relative, len(content), root_name), content)
                hashes[relative] = hashlib.sha256(content).hexdigest()
            checksums = ''.join(digest+'  '+name+'\n' for name, digest in sorted(hashes.items())).encode()
            target.writestr(_new_entry('MANIFEST.sha256', len(checksums), root_name), checksums)
        with zipfile.ZipFile(pending) as checked:
            if checked.testzip() is not None:
                raise ValueError('GitHub bundle ZIP CRC check failed')
            if len(set(checked.namelist())) != len(checked.namelist()):
                raise ValueError('Duplicate output archive names')
            if any('/voice-library/' in name or '/voice-pack/' in name for name in checked.namelist()):
                raise ValueError('Plaintext private catalog found in output ZIP')
        pending.replace(destination)
    finally:
        pending.unlink(missing_ok=True)
    digest = sha256(destination)
    Path(str(destination)+'.sha256').write_text(digest+'  '+destination.name+'\n', encoding='ascii')
    report = {'format': 'voice-studio-encrypted-github-bundle-v1', 'file': destination.name,
              'sha256': digest, 'bytes': destination.stat().st_size, 'zip_crc': 'passed',
              'verified_base_sha256': expected_base, 'reused_base_files': reused,
              'encrypted_voice_count': 19, 'plaintext_voice_files_published': False,
              'password_included': False, 'user_unlock_required': True,
              'windows_ps_crypto_test': 'required by publishing workflow; recorded separately',
              'voice_unlock_preserves_current_application': True}
    destination.with_suffix('.qa.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
    return destination


def build_update(delivery, output):
    delivery, output = Path(delivery), Path(output)
    verify_delivery(delivery)
    output.mkdir(parents=True, exist_ok=True)
    destination = output/UPDATE_FILENAME
    if destination.exists():
        raise ValueError('Refusing to overwrite an existing encrypted update')
    pending = destination.with_name(destination.name+'.partial')
    hashes = {}
    try:
        with zipfile.ZipFile(pending, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            files = {name: (delivery/name).read_bytes() for name in DELIVERY_FILES}
            files['DOC_TRUOC_CAP_NHAT_GITHUB.txt'] = UPDATE_README.encode('utf-8')
            for name, content in files.items():
                archive.writestr(_new_entry(name, len(content), UPDATE_ROOT), content)
                hashes[name] = hashlib.sha256(content).hexdigest()
            checksums = ''.join(digest+'  '+name+'\n' for name, digest in sorted(hashes.items())).encode()
            archive.writestr(_new_entry('MANIFEST.sha256', len(checksums), UPDATE_ROOT), checksums)
        with zipfile.ZipFile(pending) as checked:
            if checked.testzip() is not None:
                raise ValueError('Encrypted update ZIP CRC mismatch')
        pending.replace(destination)
    finally:
        pending.unlink(missing_ok=True)
    digest = sha256(destination)
    Path(str(destination)+'.sha256').write_text(digest+'  '+destination.name+'\n', encoding='ascii')
    report = {'format': 'voice-studio-encrypted-github-update-v1', 'file': destination.name,
              'bytes': destination.stat().st_size, 'sha256': digest, 'zip_crc': 'passed',
              'encrypted_voice_count': 19, 'plaintext_voice_files_published': False,
              'password_included': False, 'user_unlock_required': True}
    destination.with_suffix('.qa.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
    return destination


def build_repair(delivery, output):
    """Ship only the paste-friendly installer; reuse the user's downloaded pack."""
    delivery, output = Path(delivery), Path(output)
    files = {}
    for name in REPAIR_FILES:
        path = delivery/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > BLOCK:
            raise ValueError('Missing or invalid password input repair file: '+name)
        files[name] = path.read_bytes()
    files['DOC_TRUOC_SUA_LOI.txt'] = REPAIR_README.encode('utf-8')
    checksums = ''.join(hashlib.sha256(content).hexdigest()+'  '+name+'\n'
                        for name, content in sorted(files.items())).encode()
    files['MANIFEST.sha256'] = checksums
    output.mkdir(parents=True, exist_ok=True)
    destination = output/REPAIR_FILENAME
    if destination.exists():
        raise ValueError('Refusing to overwrite an existing password input repair')
    pending = destination.with_name(destination.name+'.partial')
    try:
        with zipfile.ZipFile(pending, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, content in files.items():
                archive.writestr(_new_entry(name, len(content), REPAIR_ROOT), content)
        with zipfile.ZipFile(pending) as checked:
            expected = {REPAIR_ROOT+'/'+name for name in files}
            if checked.testzip() is not None or set(checked.namelist()) != expected:
                raise ValueError('Password input repair ZIP check failed')
        pending.replace(destination)
    finally:
        pending.unlink(missing_ok=True)
    digest = sha256(destination)
    Path(str(destination)+'.sha256').write_text(digest+'  '+destination.name+'\n', encoding='ascii')
    report = {'format': 'voice-studio-github-input-repair-v1', 'file': destination.name,
              'bytes': destination.stat().st_size, 'sha256': digest, 'zip_crc': 'passed',
              'existing_full_download_required': True, 'includes_private_voice_packet': False,
              'password_included': False, 'fix': 'paste-friendly Windows password input'}
    destination.with_suffix('.qa.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
    return destination


class BuilderTests(unittest.TestCase):
    def test_preserves_base_and_adds_only_encrypted_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            delivery = directory/'delivery-source'; (delivery/'delivery').mkdir(parents=True)
            for name in DELIVERY_FILES[:2]:
                (delivery/name).write_bytes(b'generic installer code')
            encrypted = b'VSPACK01'+b'x'*88
            (delivery/'delivery/voices.vspack').write_bytes(encrypted)
            manifest = {'format': 'voice-studio-private-delivery-v1', 'encrypted_file': 'voices.vspack',
                        'encrypted_sha256': hashlib.sha256(encrypted).hexdigest(), 'encrypted_size': len(encrypted),
                        'plaintext_sha256': 'a'*64, 'plaintext_size': 12,
                        'updater_root': 'Voice-Studio-Rieng-1.7.0-Cap-Nhat-19-Giong'}
            (delivery/'delivery/manifest.json').write_text(json.dumps(manifest))
            base = directory/'base.zip'
            with zipfile.ZipFile(base, 'w') as archive:
                for name, content in {'runtime/python.exe': b'python', 'app/app.py': b'generic app',
                                      'MO_TOOL.bat': b'launch', 'TAI_GIONG_DA_NGON_NGU.bat': b'prepare',
                                      'BASE-LICENSE.txt': b'keep license', 'MANIFEST.sha256': b'old',
                                      'BUILD_INFO.json': json.dumps({'version': '1.7.0', 'bundled_runtime': True}).encode()}.items():
                    archive.writestr(BASE_ROOT+'/'+name, content)
            bundle = build_bundle(base, delivery, directory/'output', sha256(base))
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(archive.read(ROOT+'/runtime/python.exe'), b'python')
                self.assertEqual(archive.read(ROOT+'/BASE-LICENSE.txt'), b'keep license')
                self.assertEqual(archive.read(ROOT+'/delivery/voices.vspack'), encrypted)
                metadata = json.loads(archive.read(ROOT+'/BUILD_INFO.json'))
                self.assertTrue(metadata['private_voice_unlock_required'])
                self.assertFalse(metadata['private_delivery_plaintext_published'])
                for line in archive.read(ROOT+'/MANIFEST.sha256').decode().splitlines():
                    expected, name = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256(archive.read(ROOT+'/'+name)).hexdigest(), expected)
            # A newly built release must keep its new source and metadata while
            # using the same encrypted legacy reference packet.
            current_base = directory/'base-1.8.zip'
            current_root = 'Voice-Studio-Rieng-1.8.0-Portable'
            current_full = 'Voice-Studio-Rieng-1.8.0-19-Giong-GitHub'
            with zipfile.ZipFile(base) as original, zipfile.ZipFile(current_base, 'w') as current:
                for entry in original.infolist():
                    relative = entry.filename[len(BASE_ROOT)+1:]
                    content = original.read(entry)
                    if relative == 'BUILD_INFO.json':
                        content = json.dumps({'version': '1.8.0', 'bundled_runtime': True}).encode()
                    current.writestr(current_root+'/'+relative, content)
                current.writestr(current_root+'/app/voxcpm_acceleration.py', b'new acceleration module')
            full = build_bundle(current_base, delivery, directory/'current-output',
                                sha256(current_base), current_root, current_full, '1.8.0')
            with zipfile.ZipFile(full) as archive:
                self.assertEqual(archive.read(current_full+'/app/voxcpm_acceleration.py'), b'new acceleration module')
                self.assertEqual(json.loads(archive.read(current_full+'/BUILD_INFO.json'))['version'], '1.8.0')
                self.assertEqual(archive.read(current_full+'/delivery/voices.vspack'), encrypted)
                self.assertIn('bản 1.8', archive.read(current_full+'/README_GITHUB_19_GIONG.txt').decode())
            with self.assertRaisesRegex(ValueError, 'version/runtime'):
                build_bundle(current_base, delivery, directory/'bad-version', sha256(current_base),
                             current_root, current_full, '1.7.0')
            update = build_update(delivery, directory/'output')
            with zipfile.ZipFile(update) as archive:
                self.assertEqual(archive.read(UPDATE_ROOT+'/delivery/voices.vspack'), encrypted)
                self.assertFalse(any('/runtime/' in name for name in archive.namelist()))
            (delivery/REPAIR_FILES[0]).write_bytes(b'generic paste repair launcher')
            repair = build_repair(delivery, directory/'output')
            with zipfile.ZipFile(repair) as archive:
                self.assertEqual(archive.read(REPAIR_ROOT+'/'+REPAIR_FILES[0]), b'generic paste repair launcher')
                self.assertFalse(any(name.endswith('.vspack') or '/delivery/' in name or '/runtime/' in name
                                     for name in archive.namelist()))
                for line in archive.read(REPAIR_ROOT+'/MANIFEST.sha256').decode().splitlines():
                    expected, name = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256(archive.read(REPAIR_ROOT+'/'+name)).hexdigest(), expected)
            (delivery/'delivery/voices.vspack').write_bytes(encrypted+b'bad')
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                verify_delivery(delivery)

    def test_rejects_unsafe_windows_archive_names(self):
        for path in ('../escape', '/absolute', 'root/../escape', 'root/C:drive',
                     'root/back\\slash', 'root/CON.txt', 'root/trailing. '):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_path(path)


def main():
    parser = argparse.ArgumentParser(description='Build a GitHub Windows download containing encrypted reference voices')
    parser.add_argument('--base-archive', type=Path)
    parser.add_argument('--delivery-dir', type=Path, default=Path(__file__).with_name('github-delivery'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--base-sha256', default=BASE_SHA256)
    parser.add_argument('--base-root', default=BASE_ROOT)
    parser.add_argument('--version', default='1.7.0')
    parser.add_argument('--bundle-root', default=ROOT)
    parser.add_argument('--full-only', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BuilderTests))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    if not args.output:
        parser.error('--output is required')
    base = args.base_archive or args.output.parent/'verified-public-base.zip'
    if args.version != '1.7.0' and not args.base_archive:
        parser.error('A new version requires its checksum-verified native Windows base')
    if not args.full_only:
        build_repair(args.delivery_dir, args.output)
    if not args.base_archive:
        download_base(base)
    build_bundle(base, args.delivery_dir, args.output, args.base_sha256,
                 args.base_root, args.bundle_root, args.version)
    if not args.full_only:
        build_update(args.delivery_dir, args.output)


if __name__ == '__main__':
    main()
