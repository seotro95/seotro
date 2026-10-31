"""Stage the complete, cleaned Windows package, then archive its frozen inventory.

The stage/ZIP split permits real Windows checks without publishing their job
history, generated speech or logs. All source and extra-model bytes are verified
before use; only the inventory frozen at assembly is eligible for publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import uuid
import zipfile

import build_clean_bundle as clean
import build_full_update as full
import prepare_complete_models as models

SOURCE_ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 32 * 1024**3
MAX_FILES = 100000
OWNER = '.voice-studio-complete-stage.json'
EXTRA_MANIFEST = 'EXTRA-TREE-MANIFEST.sha256'
EXTRA_METADATA = frozenset({
    'EXTRA-PACK-OWNER.json', 'EXTRA-MODEL-PLAN.json', 'EXTRA-MODEL-PINS.json',
    'EXTRA-MODEL-CPU-QA.json', 'TORCH-INSTALL-REPORT.json', 'QWEN-INSTALL-REPORT.json',
    'QWEN-RUNTIME-REQUIREMENTS.txt', 'BUNDLED-QWEN-PACKAGES.txt',
})
EXTRA_PREFIXES = ('app/.data/models/omnivoice/', 'app/.data/models/native-asr/',
                  'app/.data/models/qwen-customvoice/', 'app/.data/models/qwen-base/', 'runtime-qwen/')
EXTRA_MARKERS = frozenset('app/.data/models/' + name + '.ready'
                          for name in ('omnivoice', 'qwen', 'qwen_clone'))
EXTRA_BUILD_METADATA = frozenset({'TORCH-INSTALL-REPORT.json', 'QWEN-INSTALL-REPORT.json',
                                  'EXTRA-PACK-OWNER.json'})
VENDOR_SKILLS_PATH = re.compile(
    r'runtime-qwen/Lib/site-packages/([A-Za-z_][A-Za-z0-9_]*)/\.agents/(.+)')
GUIDE = '''VOICE STUDIO {version} — BẢN WINDOWS ĐẦY ĐỦ

Giải nén toàn bộ ZIP vào thư mục mới có quyền ghi rồi chạy MO_TOOL.bat.
Python, FFmpeg, Nano/Turbo, VoxCPM2 native Q8, OmniVoice, model nhận dạng
và hai model Qwen 0.6B cùng runtime Qwen CPU đã được đóng gói.
Chạy CAI_19_GIONG.bat nếu cần mở 19 mẫu giọng riêng, dùng mật khẩu bạn đã có.
Không chia sẻ các mẫu đã giải mã hoặc mật khẩu. Gói chỉ chứa bộ mẫu mã hóa.

Chọn đúng giọng và ngôn ngữ. Nút “Thử … CUDA” giữ bộ OmniVoice đang chọn
và dùng 8 bước. Với bộ VoxCPM, nút chuyển sang VoxCPM2 native và dùng 4 bước.
Nút tạo mẫu đo thật, giữ mẫu giọng, ngôn ngữ và kịch bản bạn đang nhập.
Có thể chọn CPU nhiều tác vụ cho VoxCPM2 native. Nghe mẫu trên máy của bạn;
ít bước hơn có thể giảm chất lượng. Qwen đi kèm dùng CPU.
Chưa chứng minh nhanh ngang Turbo hay tạo 1 giờ lời đọc trong 2 phút.
GPU GTX 1060 và các mẫu giọng riêng cần được đo trên máy thực tế.

Để giữ dữ liệu: đóng tool, sao lưu bản cũ rồi hợp nhất app\\.data và
app\\voice-library vào bản mới. Bỏ qua model trùng tên để giữ model mới.
Không thay runtime hoặc runtime-native mới bằng DLL của bản cũ.

BUILD_INFO.json ghi rõ phạm vi kiểm thử. Các báo cáo INHERITED-* thuộc
bản nền 1.12.1. EXTRA-MODEL-CPU-QA.json chỉ kiểm tra các thành phần bổ sung;
nó không thay cho kiểm tra toàn bộ gói. Báo cáo kiểm tra gói sau khi ghép,
nếu có, nằm trong THONG_TIN/FINAL-WINDOWS-QA. MANIFEST.sha256 kiểm tra từng
tệp; tệp .zip.sha256 đi cạnh ZIP kiểm tra toàn bộ gói tải về.
'''


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _safe_name(name):
    if not isinstance(name, str): raise ValueError('Invalid relative filename')
    path = PurePosixPath(name)
    if (not path.parts or path.is_absolute() or '\\' in name or ':' in name
            or '\x00' in name or path.as_posix() != name
            or any(p in {'.', '..'} or p.endswith((' ', '.')) for p in path.parts)
            or any(re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', p) for p in path.parts)):
        raise ValueError('Unsafe relative filename: ' + name)
    return path


def _real_root(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink roots or ancestors are not accepted')
    return path


def _tree(root):
    root = _real_root(root)
    if not root.is_dir(): raise ValueError('Expected a real directory: ' + str(root))
    files, folded, total = {}, set(), 0
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            _safe_name(relative)
            if path.is_symlink(): raise ValueError('Symlinks are not accepted: ' + relative)
            key = relative.casefold()
            if key in folded: raise ValueError('Case-colliding directory entries: ' + relative)
            folded.add(key)
            if path.is_dir(): continue
            if not stat.S_ISREG(path.stat().st_mode): raise ValueError('Non-regular file: ' + relative)
            files[relative] = path
            total += path.stat().st_size
            if len(files) > MAX_FILES or total > MAX_BYTES:
                raise ValueError('Directory exceeds bounded package size or file count')
    return files


def _parse_manifest(payload):
    records, folded = {}, set()
    for line in payload.decode('utf-8-sig').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match: raise ValueError('Invalid SHA256 manifest record')
        name = match[2]; _safe_name(name)
        if name.casefold() in folded: raise ValueError('Duplicate manifest filename: ' + name)
        folded.add(name.casefold()); records[name] = match[1]
        if len(records) > MAX_FILES: raise ValueError('Manifest has too many files')
    if not records: raise ValueError('Empty file manifest')
    return records


def _manifest_bytes(records):
    return ''.join(digest + '  ' + name + '\n' for name, digest in sorted(records.items())).encode('utf-8')


def _read_small(path, limit=8 * 1024**2):
    if path.stat().st_size > limit: raise ValueError('Oversized package metadata: ' + path.name)
    return path.read_bytes()


def _extra_removal_reason(name):
    if not name.startswith('runtime-qwen/'): return None
    # Wheels can bundle development documentation below their top-level Python
    # package. Treat these files solely as verified, nonshipping package data.
    if VENDOR_SKILLS_PATH.fullmatch(name): return 'qwen-vendor-development-skills'
    if name.startswith('runtime-qwen/Doc/'): return 'qwen-python-offline-documentation'
    if name.startswith(('runtime-qwen/Lib/test/', 'runtime-qwen/Lib/idlelib/idle_test/')):
        return 'qwen-python-unit-tests'
    if (name.startswith('runtime-qwen/Lib/site-packages/gradio/')
            and name.endswith(('.js.map', '.css.map'))):
        return 'qwen-browser-source-maps'
    if '__pycache__' in PurePosixPath(name).parts or name.endswith(('.pyc', '.pyo')):
        return 'qwen-generated-python-bytecode'
    return None


def _extras(root):
    files = _tree(root)
    if EXTRA_MANIFEST not in files: raise ValueError('Missing full extra-model tree manifest')
    records = _parse_manifest(_read_small(files[EXTRA_MANIFEST]))
    if set(records) != files.keys() - {EXTRA_MANIFEST}:
        raise ValueError('Extra-model manifest must cover every artifact file exactly')
    required = {'EXTRA-PACK-OWNER.json', 'EXTRA-MODEL-PINS.json', 'EXTRA-MODEL-CPU-QA.json',
                'BUNDLED-QWEN-PACKAGES.txt', 'runtime-qwen/python.exe',
                'runtime-qwen/VOICE-STUDIO-QWEN.json'} | EXTRA_MARKERS
    if not required <= records.keys(): raise ValueError('Incomplete prepared extra-model artifact')
    path_errors = []
    for name in records:
        if name not in EXTRA_METADATA and name not in EXTRA_MARKERS and not name.startswith(EXTRA_PREFIXES):
            path_errors.append('Unknown extra-model artifact path: ' + name)
        elif _private_path(name, allow_bytecode=bool(_extra_removal_reason(name)), allow_vendor_docs=True):
            path_errors.append('Excluded private/cache extra-model path: ' + name)
    if path_errors:
        raise ValueError(f'Rejected extra-model paths ({len(path_errors)} total; first 20):\n'
                         + '\n'.join(path_errors[:20]))
    for name, digest in records.items():
        if clean.file_sha256(files[name]) != digest: raise ValueError('Extra-model SHA256 mismatch: ' + name)
    if json.loads(_read_small(files['EXTRA-PACK-OWNER.json'])) != models.OWNER:
        raise ValueError('Unexpected extra-model artifact owner')
    models.validate_qa(Path(root), json.loads(_read_small(files['EXTRA-MODEL-CPU-QA.json'])))
    models.validate_prepared_models(Path(root))
    return files, records


def _source_commit(root):
    try:
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True,
                                text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch('[0-9a-f]{40}', value) else None


def _private_path(name, *, allow_bytecode=False, allow_vendor_docs=False):
    checked_name = name
    vendor = VENDOR_SKILLS_PATH.fullmatch(name) if allow_vendor_docs else None
    if vendor:
        checked_name = ('runtime-qwen/Lib/site-packages/' + vendor[1]
                        + '/_bundled_development_docs/' + vendor[2])
    parts = PurePosixPath(checked_name).parts
    return (any(p in {'.git', '.aws', '.agents', '.codex', 'voice-library'} for p in parts)
            or (name.startswith('app/.data/') and not name.startswith('app/.data/models/'))
            or (not allow_bytecode and ('__pycache__' in parts or name.endswith(('.pyc', '.pyo')))))


def _app_source(name):
    return name.startswith('app/') and not name.startswith('app/.data/')


def _write(root, name, payload, records):
    _safe_name(name)
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream: stream.write(payload)
    records[name] = hashlib.sha256(payload).hexdigest()


def stage(source_archive, extras_directory, output, *, source_root=None,
          _expected_source_sha256=clean.SOURCE_SHA256):
    """Create a new staged portable; never reads an installed user's directory."""
    source_archive, output = _real_root(source_archive), _real_root(output)
    source_root = _real_root(source_root or SOURCE_ROOT)
    if output.exists(): raise FileExistsError('Choose a new stage directory')
    if (not re.fullmatch('[0-9a-f]{64}', _expected_source_sha256)
            or not source_archive.is_file() or clean.file_sha256(source_archive) != _expected_source_sha256):
        raise ValueError('Pinned full source ZIP SHA256 mismatch')
    overlays, version = full._sources(source_root)
    if version != models.OWNER['version']: raise ValueError('Current app and extra-model versions differ')
    overlays = {name: value for name, value in overlays.items() if name != 'DOC_TRUOC.md'}
    overlays['HUONG_DAN_CAN_MOC.txt'] = overlays['HUONG_DAN_CAN_MOC.txt'].replace(
        b'PORTABLE-QA.json', b'THONG_TIN/FINAL-WINDOWS-QA/WINDOWS-COMPLETE-QA.json')
    overlays['requirements-runtime.txt'] = (
        b'# Build recipe only; actual bundled versions are in BUNDLED-PACKAGES.txt.\n'
        + overlays['requirements-runtime.txt'])
    extra_files, extra_records = _extras(extras_directory)
    # Keep staging paths short: the bundled tokenizer snapshot and Torch wheel
    # contain long relative paths, and the final package name is already long.
    temporary = output.with_name('.stage-' + uuid.uuid4().hex[:12] + '.assembling')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary.mkdir()
    try:
        records, removed, extra_removed, renamed, replaced = {}, [], [], [], []
        with zipfile.ZipFile(source_archive) as archive:
            files = clean._members(archive)
            original = clean._manifest(archive, files)
            base_info = json.loads(clean._read(archive, files['BUILD_INFO.json']))
            if base_info.get('version') != '1.12.1' or base_info.get('encrypted_private_pack_bundled') is not True:
                raise ValueError('Expected the complete pinned 1.12.1 distribution')
            inventory, package_count = clean._inventory(archive, files)
            total = sum(info.file_size for info in files.values()) + sum(p.stat().st_size for p in extra_files.values())
            if total > MAX_BYTES or len(files) + len(extra_files) > MAX_FILES:
                raise ValueError('Combined package exceeds bounded size or file count')
            for name, entry in sorted(files.items()):
                if name == 'MANIFEST.sha256': continue
                reason = clean.removal_reason(name, entry.file_size)
                if _private_path(name): reason = 'excluded-history-cache-or-private-reference'
                if _app_source(name) and name not in overlays: reason = 'superseded-application-source'
                target = ('INHERITED-1.12.1-' + name if '/' not in name and
                          (name == 'BUILD_INFO.json' or 'QA' in name) else name)
                destination = None
                if not reason and name not in overlays:
                    destination = temporary / target; destination.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with archive.open(entry) as incoming:
                    if destination is not None:
                        with destination.open('xb') as outgoing:
                            for block in iter(lambda: incoming.read(1024**2), b''):
                                digest.update(block); outgoing.write(block)
                    else:
                        for block in iter(lambda: incoming.read(1024**2), b''): digest.update(block)
                if digest.hexdigest() != original[name]: raise ValueError('Source manifest SHA256 mismatch: ' + name)
                if reason:
                    removed.append({'path': name, 'reason': reason, 'bytes': entry.file_size, 'sha256': original[name]})
                elif name in overlays:
                    replaced.append({'path': name, 'source_sha256': original[name],
                                     'current_sha256': hashlib.sha256(overlays[name]).hexdigest()})
                else:
                    records[target] = original[name]
                    if target != name: renamed.append({'source': name, 'destination': target})
        for name, payload in overlays.items(): _write(temporary, name, payload, records)
        for name, digest in extra_records.items():
            if name in records: raise ValueError('Extras would overwrite a retained source asset: ' + name)
            reason = _extra_removal_reason(name)
            if reason:
                extra_removed.append({'path': name, 'reason': reason,
                                      'bytes': extra_files[name].stat().st_size, 'sha256': digest})
                continue
            if name in EXTRA_BUILD_METADATA:
                continue  # Build-only metadata; source verification above still covers it.
            target = temporary / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(extra_files[name], target)
            if clean.file_sha256(target) != digest: raise ValueError('Extra-model copy SHA256 mismatch: ' + name)
            records[name] = digest
        _write(temporary, 'BUNDLED-PACKAGES.txt', inventory, records)
        _write(temporary, 'DOC_TRUOC.txt', GUIDE.format(version=version).encode('utf-8'), records)
        info = {
            'version': version, 'package_type': 'windows-x64-portable-complete',
            'source_full_archive_sha256': _expected_source_sha256,
            'application_source_commit': _source_commit(source_root),
            'application_source_sha256': full.application_digest(overlays),
            'application_sources_replaced_from_current_checkout': True,
            'native_source_revision': full.NATIVE_REVISION, 'voxcpm2_model_revision': full.MODEL_REVISION,
            'extra_model_pins': 'EXTRA-MODEL-PINS.json',
            'extra_model_tree_manifest_sha256': clean.file_sha256(extra_files[EXTRA_MANIFEST]),
            'model_components': ['Nano', 'Turbo', 'VoxCPM2-native-Q8', 'OmniVoice',
                                 'native-ASR', 'Qwen3-TTS-CustomVoice-0.6B', 'Qwen3-TTS-Base-0.6B'],
            'encrypted_private_pack_bundled': True, 'decoded_private_recordings_bundled': False,
            'main_runtime_inventory': 'BUNDLED-PACKAGES.txt', 'qwen_runtime_inventory': 'BUNDLED-QWEN-PACKAGES.txt',
            'windows_complete_package_qa': 'at-assembly-not-run',
            'extra_model_cpu_qa': 'EXTRA-MODEL-CPU-QA.json',
            'extra_model_cpu_qa_scope': 'Prepared extra model/runtime components before final assembly only',
            'omnivoice_inference_test': 'not_run',
            'inherited_qa_reports': [row['destination'] for row in renamed if 'QA' in row['source']],
            'inherited_qa_scope': 'Pinned original 1.12.1 application only; not current application or assembled package',
            'gpu_inference_test': 'not_run', 'target_30x_guaranteed': False,
            'old_installation_or_user_data_read': False,
        }
        _write(temporary, 'BUILD_INFO.json', _json(info), records)
        report = {'schema': 1, 'source_full_archive_sha256': _expected_source_sha256,
                  'all_source_files_sha256_verified': True, 'all_extra_files_sha256_verified': True,
                  'source_file_count': len(files), 'removed_file_count': len(removed),
                  'removed_files': removed, 'renamed_inherited_evidence': renamed,
                  'extra_removed_files': extra_removed, 'extra_removed_file_count': len(extra_removed),
                  'extra_removed_uncompressed_bytes': sum(row['bytes'] for row in extra_removed),
                  'total_removed_file_count': len(removed) + len(extra_removed),
                  'replaced_files': replaced, 'current_application_files': sorted(n for n in overlays if _app_source(n)),
                  'added_files': sorted(set(records) - set(original)),
                  'bundled_main_distribution_count': package_count,
                  'nonshipping_extra_build_metadata': sorted(set(extra_records) & EXTRA_BUILD_METADATA),
                  'model_native_and_encrypted_voice_assets_unchanged': True,
                  'windows_complete_package_qa': 'at-assembly-not-run'}
        _write(temporary, 'CLEANUP-REPORT.json', _json(report), records)
        manifest = _manifest_bytes(records)
        (temporary / 'MANIFEST.sha256').write_bytes(manifest)
        (temporary / OWNER).write_bytes(_json({'format': 'voice-studio-complete-stage-v1', 'version': version,
                    'archive_root': output.name, 'manifest_sha256': hashlib.sha256(manifest).hexdigest(),
                    'file_count': len(records), 'source_full_archive_sha256': _expected_source_sha256}))
        # mkdir publication never overwrites a pre-existing directory, including a racing caller.
        output.mkdir()
        try:
            for child in temporary.iterdir(): shutil.move(str(child), str(output / child.name))
        except BaseException:
            shutil.rmtree(output); raise
        return output
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def archive(stage_directory, output, *, qa_dir=None):
    """Archive only frozen assembly files; ignore generated test/job files."""
    root, output = _real_root(stage_directory), _real_root(output)
    checksum = Path(str(output) + '.sha256')
    if output.suffix.lower() != '.zip': raise ValueError('Output must be a ZIP path')
    if output.exists() or checksum.exists(): raise FileExistsError('Choose a new output ZIP and checksum')
    for name in (OWNER, 'MANIFEST.sha256'):
        if (root / name).is_symlink() or not (root / name).is_file(): raise ValueError('Missing stage ownership/inventory')
    owner = json.loads(_read_small(root / OWNER))
    manifest = _read_small(root / 'MANIFEST.sha256')
    if (owner.get('format') != 'voice-studio-complete-stage-v1' or owner.get('version') != models.OWNER['version']
            or owner.get('manifest_sha256') != hashlib.sha256(manifest).hexdigest()):
        raise ValueError('Stage ownership or frozen manifest mismatch')
    _safe_name(owner.get('archive_root'))
    if len(PurePosixPath(owner['archive_root']).parts) != 1: raise ValueError('Invalid archive root')
    records = _parse_manifest(manifest)
    if len(records) != owner.get('file_count'): raise ValueError('Frozen inventory count mismatch')
    files, total = {}, 0
    for name, digest in records.items():
        if name in {OWNER, 'MANIFEST.sha256'} or _private_path(name): raise ValueError('Unexpected frozen inventory file')
        path = root / name
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise ValueError('Frozen file missing or replaced by symlink: ' + name)
        total += path.stat().st_size
        if total > MAX_BYTES: raise ValueError('Stage exceeds bounded package size')
        if clean.file_sha256(path) != digest: raise ValueError('Staged file SHA256 mismatch: ' + name)
        files[name] = path
    qa_files = {}
    if qa_dir is not None:
        qa_root = _real_root(qa_dir)
        if not qa_root.is_dir(): raise ValueError('QA directory must exist')
        for path in sorted(qa_root.iterdir()):
            if path.is_symlink(): raise ValueError('QA symlinks are not accepted')
            if not path.is_file() or path.suffix.lower() != '.json': continue
            _safe_name(path.name)
            payload = _read_small(path); json.loads(payload)
            total += len(payload)
            if total > MAX_BYTES: raise ValueError('Final QA exceeds bounded package size')
            name = 'THONG_TIN/FINAL-WINDOWS-QA/' + path.name
            if name in records: raise ValueError('QA report conflicts with frozen inventory')
            qa_files[name] = payload; records[name] = hashlib.sha256(payload).hexdigest()
            if len(qa_files) > 16: raise ValueError('Too many final QA reports')
        if not qa_files: raise ValueError('QA directory has no JSON reports')
    if len(records) + 1 > MAX_FILES: raise ValueError('Final archive has too many files')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.' + uuid.uuid4().hex + '.assembling')
    checksum_temporary = Path(str(temporary) + '.sha256'); published = []
    try:
        with temporary.open('xb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED,
                                                           compresslevel=5, allowZip64=True) as target:
            for name, path in sorted(files.items()):
                item = zipfile.ZipInfo(owner['archive_root'] + '/' + name, (1980, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED; item.external_attr = 0o100644 << 16
                digest = hashlib.sha256()
                with path.open('rb') as source, target.open(item, 'w', force_zip64=True) as destination:
                    for block in iter(lambda: source.read(1024**2), b''):
                        digest.update(block); destination.write(block)
                if digest.hexdigest() != records[name]: raise ValueError('Staged file changed during archiving: ' + name)
            for name, payload in sorted(qa_files.items()): target.writestr(owner['archive_root'] + '/' + name, payload)
            target.writestr(owner['archive_root'] + '/MANIFEST.sha256', _manifest_bytes(records))
        digest = clean.file_sha256(temporary)
        with checksum_temporary.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(digest + '  ' + output.name + '\n')
        os.link(temporary, output); published.append(output)
        os.link(checksum_temporary, checksum); published.append(checksum)
        return output, checksum
    except BaseException:
        for path in reversed(published): path.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True); checksum_temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    assemble = commands.add_parser('stage')
    assemble.add_argument('--source-archive', required=True, type=Path)
    assemble.add_argument('--extras-directory', required=True, type=Path)
    assemble.add_argument('--output', required=True, type=Path)
    assemble.add_argument('--source-root', type=Path, default=SOURCE_ROOT)
    pack = commands.add_parser('archive')
    pack.add_argument('--stage', required=True, type=Path)
    pack.add_argument('--output', required=True, type=Path)
    pack.add_argument('--qa-dir', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'stage':
        result = stage(args.source_archive, args.extras_directory, args.output, source_root=args.source_root)
    else: result = archive(args.stage, args.output, qa_dir=args.qa_dir)
    print(result)


if __name__ == '__main__': main()
