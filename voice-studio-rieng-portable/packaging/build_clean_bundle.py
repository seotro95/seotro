"""Clean the pinned full Windows distribution without changing inference assets.

Only an audited list of installers, documentation, stdlib tests and browser
source maps is removed. Installed Python distributions, metadata, libraries,
models and encrypted recordings are retained. This command never reads an
existing user installation and does not establish fresh Windows or GPU QA.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import uuid
import zipfile


SOURCE_SHA256 = 'a4646d2ab03d0ea9f605961dc7cde8fee4c512cc70344764564f3130fd3e2864'
SOURCE_NAME = 'Voice-Studio-1.12.1-Full-Windows-x64'
OUTPUT_NAME = 'Voice-Studio-1.12.1-Clean-Full-Windows-x64'
_OLD_CPU = frozenset({'CPU-INTERNATIONAL-INT8-BENCHMARK.json', 'CPU-SHARED-MODEL-BENCHMARK.json',
                      'CPU-SHORT-SPEECH-BENCHMARK.json', 'CPU-SRT-SHORT-SAMPLES.json'})
_OLD_QA = frozenset({'BASE-1.10-MANIFEST.sha256', 'BASE-1.10-PORTABLE-QA.json',
                     'BASE-1.10-SHARED-MODEL-QA.json'})
_OLD_GUIDES = frozenset({'DOC_TRUOC_PORTABLE.txt', 'README_GITHUB_19_GIONG.txt',
                         'DOC_TRUOC.md', 'DOC_TRUOC_FULL.txt'})
_APP_OVERLAY = ('native_synthesis.py', 'native_paths.py')
_REQUIRED = frozenset({
    'BUILD_INFO.json', 'MANIFEST.sha256', 'MO_TOOL.bat', 'HUONG_DAN_CAN_MOC.txt',
    'requirements-runtime.txt', 'requirements-international.txt', 'THIRD_PARTY_NOTICES.md',
    'runtime/python.exe', 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe',
    'app/app.py', 'app/launcher.py', 'app/static/index.html', 'app/static/app.js', 'app/static/style.css',
    'app/.data/models/vieneu_nano.ready', 'app/.data/models/vieneu.ready',
    'app/.data/models/voxcpm-native.ready', 'app/.data/models/voxcpm2-native/voxcpm2-q8_0.gguf',
    'runtime-native/cpu/audiocpp.dll', 'runtime-native/cuda/audiocpp.dll',
    'CAI_19_GIONG.bat', 'install_secure_voices.ps1', 'delivery/manifest.json', 'delivery/voices.vspack',
    'WINDOWS-NATIVE-VOXCPM-QA.json',
})

GUIDE = '''VOICE STUDIO 1.12.1 — BẢN WINDOWS ĐẦY ĐỦ, ĐÃ DỌN GỌN (CLEAN-1)

1. Giải nén TOÀN BỘ ZIP vào thư mục mới có quyền ghi. Không ghi đè lên tool
   đang mở. Giữ nguyên cấu trúc app, runtime, runtime-native, ffmpeg và delivery.
2. Nếu cần mở bộ 19 giọng riêng, chạy CAI_19_GIONG.bat và nhập mật khẩu cũ
   bạn đã có. Gói không chứa mật khẩu hoặc các bản thu riêng đã giải mã.
3. Chạy MO_TOOL.bat. Python, FFmpeg, Nano/Turbo và VoxCPM2 native Q8 cùng
   thư viện CPU/CUDA12 đã có sẵn; không cần cài lại Python.

VỚI MÁY GTX 1060 6 GB / XEON 28 NHÂN VẬT LÝ / RAM 128 GB
Chọn đúng mẫu giọng và ngôn ngữ. Với giọng quốc tế, thử bộ VoxCPM2 native Q8,
CUDA và chế độ Nhanh rồi bấm đo giọng để nghe và đo thực tế. CUDA giữ một model.
Driver NVIDIA phải tương thích CUDA12. Có thể thử CPU với tối đa 7 tác vụ x
4 luồng ở chế độ Nhanh; hãy đo trước với đoạn ngắn trên máy của bạn.
Chưa xác minh suy luận GPU trên GTX1060, giọng riêng, toàn bộ 1 giờ lời đọc
hoặc mục tiêu 1 giờ voice trong 2 phút / tốc độ ngang Turbo.

GIỮ DỮ LIỆU CŨ
Đóng cả hai tool và sao lưu thư mục cũ. Hợp nhất app\\.data và app\\voice-library
cũ vào đúng vị trí của bản mới. Trong app\\.data\\models, bỏ qua tệp trùng để giữ
các model/marker mới. Không thay runtime-native mới bằng thư mục DLL cũ.
Nếu còn dùng VoxCPM PyTorch tùy chọn, có thể giữ runtime-international cũ.

BẢN ĐÃ DỌN
Đã bỏ bộ cài Python thừa, tài liệu và bộ kiểm thử Python, bản đồ mã nguồn
giao diện, báo cáo benchmark cũ và hướng dẫn trùng/lỗi thời. Không thay model,
DLL hoặc mã ứng dụng; việc dọn tệp không tự làm tốc độ suy luận nhanh hơn.
CLEANUP-REPORT.json liệt kê chính xác tệp đã bỏ và các thay đổi hướng dẫn.
BUNDLED-PACKAGES.txt ghi phiên bản thư viện thực sự được đóng gói.
requirements-runtime.txt là công thức dựng, không phải danh sách phiên bản
chính xác của runtime hiện có. Giữ metadata và giấy phép của mọi thư viện.
MANIFEST.sha256 kiểm tra từng tệp; .zip.sha256 đi cạnh ZIP kiểm tra cả gói.

WINDOWS-NATIVE-VOXCPM-QA.json là kiểm tra mã ứng dụng/model của bản nguồn.
BUILD_INFO.json phân biệt kết quả kế thừa và kiểm tra lại gói Clean.
'''


def file_sha256(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def removal_reason(name, size):
    if name == 'runtime/python-3.12.10-amd64.exe': return 'redundant-python-installer'
    if name.startswith('runtime/Doc/'): return 'python-offline-documentation'
    if name.startswith(('runtime/Lib/test/', 'runtime/Lib/idlelib/idle_test/')): return 'python-unit-tests'
    if name.startswith('runtime/Lib/site-packages/gradio/') and name.endswith(('.js.map', '.css.map')):
        return 'browser-source-maps'
    if name == 'runtime/Lib/site-packages/scipy-1.18.1-cp312-cp312-win_amd64.whl' and size == 0:
        return 'empty-wheel-placeholder'
    if name in _OLD_CPU: return 'old-cpu-benchmark-reports'
    if name in _OLD_QA: return 'old-base-manifest-and-qa'
    if name in _OLD_GUIDES: return 'superseded-user-guides'
    return None


def _members(archive):
    files, folded = {}, set()
    infos = archive.infolist()
    if not 1 <= len(infos) <= 50000 or sum(i.file_size for i in infos) > 16 * 1024**3:
        raise ValueError('Unexpected source archive size or member count')
    for info in infos:
        raw = info.filename
        path = PurePosixPath(raw)
        parts = path.parts
        if (not parts or parts[0] != SOURCE_NAME or len(parts) < 2
                or path.is_absolute() or '\\' in raw or ':' in raw or '\x00' in raw
                or any(p in {'.', '..'} or p.endswith((' ', '.')) for p in parts)
                or '/'.join(parts) != raw.rstrip('/')
                or any(re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', p) for p in parts)
                or stat.S_IFMT(info.external_attr >> 16) not in {0, stat.S_IFREG, stat.S_IFDIR}
                or info.flag_bits & 1):
            raise ValueError('Unsafe or unexpected source ZIP member: ' + raw)
        key = '/'.join(parts[1:])
        if key.casefold() in folded:
            raise ValueError('Duplicate or case-colliding source ZIP member: ' + key)
        folded.add(key.casefold())
        if not info.is_dir(): files[key] = info
    missing = _REQUIRED - files.keys()
    if missing: raise ValueError('Source full ZIP is missing: ' + ', '.join(sorted(missing)))
    if any(name in files for name in ('CLEANUP-REPORT.json', 'BUNDLED-PACKAGES.txt', 'DOC_TRUOC.txt')):
        raise ValueError('Source is already cleaned or has conflicting outputs')
    return files


def _read(archive, info, limit=8 * 1024**2):
    if info.file_size > limit: raise ValueError('Unexpectedly large source metadata: ' + info.filename)
    value = archive.read(info)
    if len(value) != info.file_size: raise ValueError('Incomplete source metadata')
    return value


def _manifest(archive, files):
    payload = _read(archive, files['MANIFEST.sha256']).decode('utf-8')
    records = {}
    for line in payload.splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match or match[2] in records: raise ValueError('Invalid or duplicate source file manifest record')
        records[match[2]] = match[1]
    if set(records) != files.keys() - {'MANIFEST.sha256'}:
        raise ValueError('Source file manifest does not exactly cover the ZIP')
    return records


def _inventory(archive, files):
    packages = {}
    for name, info in files.items():
        if not re.fullmatch(r'runtime/Lib/site-packages/[^/]+\.dist-info/METADATA', name): continue
        metadata = BytesParser().parsebytes(_read(archive, info, 2 * 1024**2), headersonly=True)
        package, version = metadata.get('Name'), metadata.get('Version')
        if (not package or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', package)
                or not version or len(version) > 200 or any(c.isspace() for c in version)):
            raise ValueError('Invalid bundled distribution metadata: ' + name)
        normalized = re.sub(r'[-_.]+', '-', package).casefold()
        if normalized in packages: raise ValueError('Duplicate bundled distribution: ' + package)
        packages[normalized] = (package, version)
    if not packages: raise ValueError('Source is missing Python distribution metadata')
    text = ('# Actual distributions bundled in the Windows Python 3.12.10 runtime.\n'
            '# Read directly from retained *.dist-info/METADATA; not the build recipe.\n')
    return (text + ''.join(f'{name}=={version}\n' for name, version in sorted(packages.values(), key=lambda x:x[0].casefold()))).encode('utf-8'), len(packages)


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _zip_info(name):
    info = zipfile.ZipInfo(OUTPUT_NAME + '/' + name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def _protected(name):
    return (name.startswith(('app/', 'runtime-native/', 'delivery/'))
            or name.lower().endswith(('.dll', '.pyd'))
            or name in {'CAI_19_GIONG.bat', 'install_secure_voices.ps1',
                        'runtime/python.exe', 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe'})


def _app_source(name):
    return (name.startswith('app/') and not name.startswith('app/.data/')
            and PurePosixPath(name).suffix.lower() in {'.py', '.ps1', '.html', '.css', '.js'})


def _app_digest(digests):
    records = {name: value for name, value in digests.items() if _app_source(name)}
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _app_overlays(directory, original):
    if directory is None: return {}
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('App overlay must be a real application source directory')
    if 'app/native_synthesis.py' not in original or 'app/native_paths.py' in original:
        raise ValueError('Unexpected source baseline for the two-file native path correction')
    result = {}
    for name in _APP_OVERLAY:
        path = directory / name
        if (path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= 256 * 1024
                or not path.resolve().is_relative_to(directory.resolve())):
            raise ValueError('Missing, unsafe or unbounded native path correction source: ' + name)
        payload = path.read_bytes()
        ast.parse(payload.decode('utf-8-sig'), filename=name)
        result['app/' + name] = payload
    if hashlib.sha256(result['app/native_synthesis.py']).hexdigest() == original['app/native_synthesis.py']:
        raise ValueError('The native binding overlay does not contain a correction')
    return result


def build_clean(source_archive, output, *, app_overlay=None, _expected_sha256=SOURCE_SHA256):
    source_archive, output = Path(source_archive), Path(output)
    checksum = Path(str(output) + '.sha256')
    if output.suffix.lower() != '.zip': raise ValueError('Output must be a ZIP path')
    if output.exists() or output.is_symlink() or checksum.exists() or checksum.is_symlink():
        raise FileExistsError('Choose a new output path; existing files are preserved')
    if any(p.is_symlink() for p in output.parents): raise ValueError('Output parent symlinks are not accepted')
    if (not re.fullmatch('[0-9a-f]{64}', _expected_sha256)
            or source_archive.is_symlink() or not source_archive.is_file()
            or file_sha256(source_archive) != _expected_sha256):
        raise ValueError('Pinned full source ZIP SHA256 mismatch; no contents were used')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(output.name + '.' + uuid.uuid4().hex + '.assembling')
    checksum_staging = Path(str(staging) + '.sha256')
    published = []
    try:
        with zipfile.ZipFile(source_archive) as source:
            files = _members(source)
            original = _manifest(source, files)
            app_changes = _app_overlays(app_overlay, original)
            revision = 'clean-2' if app_changes else 'clean-1'
            info = json.loads(_read(source, files['BUILD_INFO.json']))
            if info.get('version') != '1.12.1' or info.get('encrypted_private_pack_bundled') is not True:
                raise ValueError('Expected the complete 1.12.1 source distribution')
            inventory, package_count = _inventory(source, files)
            launcher = _read(source, files['MO_TOOL.bat'])
            if launcher.count(b'title Voice Studio Rieng 1.9.0 Portable') != 1:
                raise ValueError('Unexpected source launcher title')
            guide = GUIDE
            if app_changes:
                guide = (guide.replace('(CLEAN-1)', '(CLEAN-2)')
                         .replace('Không thay model,\nDLL hoặc mã ứng dụng; việc dọn tệp không tự làm tốc độ suy luận nhanh hơn.',
                                  'Giữ nguyên model và DLL. Mã native đã được sửa lỗi đọc model khi thư mục\n'
                                  'có dấu tiếng Việt; việc dọn tệp không tự làm tốc độ suy luận nhanh hơn.')
                         .replace('là kiểm tra mã ứng dụng/model của bản nguồn.',
                                  'là kiểm tra model và mã ứng dụng bản nguồn,\n'
                                  'trước khi sửa đường dẫn tiếng Việt; không phải kiểm tra lại mã Clean-2.'))
            changes = {
                'MO_TOOL.bat': launcher.replace(b'title Voice Studio Rieng 1.9.0 Portable', b'title Voice Studio Rieng 1.12.1 Clean Portable'),
                'HUONG_DAN_CAN_MOC.txt': _read(source, files['HUONG_DAN_CAN_MOC.txt']).replace(b'PORTABLE-QA.json', b'WINDOWS-NATIVE-VOXCPM-QA.json'),
                'requirements-runtime.txt': (b'# Build recipe only; actual bundled versions are in BUNDLED-PACKAGES.txt.\n'
                                             + _read(source, files['requirements-runtime.txt'])),
                'DOC_TRUOC.txt': guide.encode('utf-8'),
                'BUNDLED-PACKAGES.txt': inventory,
            }
            changes.update(app_changes)
            app_records = [{'path': name, 'source_sha256': original.get(name),
                            'clean_sha256': hashlib.sha256(payload).hexdigest()}
                           for name, payload in sorted(app_changes.items())]
            final_app_digests = {**original, **{name: hashlib.sha256(payload).hexdigest()
                                              for name, payload in app_changes.items()}}
            info.update(package_type='windows-x64-portable-cleaned', package_revision=revision,
                        source_full_archive_sha256=_expected_sha256,
                        cleanup_report='CLEANUP-REPORT.json', bundled_package_inventory='BUNDLED-PACKAGES.txt',
                        cleanup_changes_inference_assets=bool(app_changes),
                        cleanup_changes_model_or_native_library_assets=False,
                        native_unicode_path_correction_applied=bool(app_changes), cleaned_windows_package_qa='not_run',
                        cleaned_windows_package_qa_scope=None)
            if app_changes:
                info.update(
                    inherited_windows_native_qa_report='WINDOWS-NATIVE-VOXCPM-QA.json',
                    inherited_windows_native_qa_scope='Pinned original application before the Unicode-path correction only',
                    inherited_windows_native_qa_source_commit=info.get('application_source_commit'),
                    inherited_source_windows_native_offline_smoke=info.get('current_native_windows_offline_smoke'),
                    application_source_commit=os.environ.get('GITHUB_SHA'), application_source_modified=True,
                    app_source_modified_files=app_records,
                    original_app_source_sha256=_app_digest(original), app_source_sha256=_app_digest(final_app_digests),
                    current_native_windows_offline_smoke='not_run', current_windows_validation_scope=None,
                    current_windows_app_http_smoke_passed=False, current_windows_nanoturbo_inference_repeated=False,
                    current_windows_private_voice_unlock_tested=False,
                )
            changes['BUILD_INFO.json'] = _json(info)
            removals, categories, category_bytes, digests = [], Counter(), Counter(), {}
            protected = {}
            with staging.open('xb') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED,
                                                               compresslevel=5, allowZip64=True) as target:
                for name, entry in sorted(files.items()):
                    if name == 'MANIFEST.sha256': continue
                    reason = removal_reason(name, entry.file_size)
                    digest = hashlib.sha256()
                    destination = None
                    try:
                        if not reason and name not in changes:
                            destination = target.open(_zip_info(name), 'w', force_zip64=True)
                        with source.open(entry) as incoming:
                            for block in iter(lambda: incoming.read(1024**2), b''):
                                digest.update(block)
                                if destination is not None: destination.write(block)
                    finally:
                        if destination is not None: destination.close()
                    actual = digest.hexdigest()
                    if actual != original[name]: raise ValueError('Source manifest SHA256 mismatch: ' + name)
                    if reason:
                        if _protected(name): raise ValueError('Cleanup would alter a protected inference asset')
                        removals.append({'path': name, 'reason': reason, 'bytes': entry.file_size, 'sha256': actual})
                        categories[reason] += 1
                        category_bytes[reason] += entry.file_size
                    elif name not in changes:
                        digests[name] = actual
                        if _protected(name): protected[name] = actual
                replaced = [{'path': name, 'source_sha256': original[name],
                             'clean_sha256': hashlib.sha256(value).hexdigest()}
                            for name, value in sorted(changes.items()) if name in original]
                report = {
                    'schema': 1, 'package_revision': revision, 'source_full_archive_sha256': _expected_sha256,
                    'source_file_count': len(files), 'removed_file_count': len(removals),
                    'removed_uncompressed_bytes': sum(row['bytes'] for row in removals),
                    'categories': {name: {'files': categories[name], 'uncompressed_bytes': category_bytes[name]}
                                   for name in sorted(categories)},
                    'removed_files': removals, 'replaced_files': replaced,
                    'added_files': sorted(set(changes) - set(original)) + ['CLEANUP-REPORT.json'],
                    'bundled_distribution_count': package_count,
                    'all_source_files_sha256_verified': True,
                    'app_model_native_and_encrypted_voice_assets_unchanged': not bool(app_changes),
                    'model_native_and_encrypted_voice_assets_unchanged': True,
                    'all_other_app_sources_unchanged': True,
                    'app_source_modified_files': app_records,
                    'original_app_source_sha256': _app_digest(original),
                    'app_source_sha256': _app_digest(final_app_digests),
                    'protected_asset_sha256': protected,
                    'installed_distribution_metadata_and_licenses_preserved': True,
                    'old_installation_or_user_data_read': False,
                    'windows_clean_package_qa': 'not_run', 'gpu_inference_test': 'not_run',
                    'target_30x_guaranteed': False,
                }
                changes['CLEANUP-REPORT.json'] = _json(report)
                for name, value in sorted(changes.items()):
                    target.writestr(_zip_info(name), value, compresslevel=5)
                    digests[name] = hashlib.sha256(value).hexdigest()
                if set(protected) != {name for name in original if _protected(name) and name not in app_changes}:
                    raise ValueError('Protected inference assets were not all retained')
                manifest = ''.join(digest + '  ' + name + '\n' for name, digest in sorted(digests.items()))
                target.writestr(_zip_info('MANIFEST.sha256'), manifest.encode('utf-8'), compresslevel=5)
        digest = file_sha256(staging)
        with checksum_staging.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(digest + '  ' + output.name + '\n')
        # Hard-link publication is atomic and refuses existing names on POSIX/NTFS.
        os.link(staging, output); published.append(output)
        os.link(checksum_staging, checksum); published.append(checksum)
        return output, checksum
    except BaseException:
        for path in reversed(published): path.unlink(missing_ok=True)
        raise
    finally:
        staging.unlink(missing_ok=True)
        checksum_staging.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--app-overlay', type=Path, help='Explicit two-file native Windows Unicode-path correction')
    args = parser.parse_args(argv)
    for path in build_clean(args.source_archive, args.output, app_overlay=args.app_overlay): print(path, flush=True)


if __name__ == '__main__': main()
