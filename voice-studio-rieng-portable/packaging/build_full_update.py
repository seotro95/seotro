"""Reassemble a full Windows portable from the pinned public 1.10 distribution.

The published Windows runtime, FFmpeg, public Nano/Turbo models and encrypted
voice installer are retained byte for byte. Current application code replaces
the old code. No local installation, decoded voice library or user history is
read. Assembly on Linux does not establish native Windows or GPU readiness.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import os
import re
import stat
import struct
import uuid
import zipfile

from build_windows import safe_zip_path, sha256


BASE_SHA256 = '65446c1a1799699b3aadad616461e97cf66c049597c7ae9a5cbf3887f20312f6'
SOURCE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_BASE_COMMIT = '888d1dbbb7153177dbaa31a213efd8ffc428b012'
NATIVE_REVISION = '2597b300f5961999387c84c65f2e8e79c088a571'
MODEL_REVISION = '32279effe8c19989596f05d353d1447f51d9e915'
_FORBIDDEN = frozenset({'.git', '.agents', '.codex', '.aws', '__pycache__',
                        '.pytest_cache', 'voice-library'})
_STATIC_SUFFIXES = frozenset({'.html', '.css', '.js'})
_ROOT_SOURCE = (
    'DOC_TRUOC.md', 'HUONG_DAN_CAN_MOC.txt', 'THIRD_PARTY_NOTICES.md',
    'requirements-runtime.txt', 'requirements-qwen.txt',
    'requirements-international.txt', 'requirements-native-asr.txt',
    'TAI_GIONG_DA_NGON_NGU.bat', 'TAI_GIONG_DA_NGON_NGU_NHANH.bat',
)
_REQUIRED_BASE = frozenset({
    'runtime/python.exe', 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe',
    'app/.data/models/vieneu_nano.ready', 'app/.data/models/vieneu.ready',
    'CAI_19_GIONG.bat', 'install_secure_voices.ps1',
    'delivery/manifest.json', 'delivery/voices.vspack', 'BUILD_INFO.json',
})
_BASE_RENAMES = {
    'BUILD_INFO.json': 'BASE-1.10-BUILD_INFO.json',
    'MANIFEST.sha256': 'BASE-1.10-MANIFEST.sha256',
    'PORTABLE-QA.json': 'BASE-1.10-PORTABLE-QA.json',
    'SHARED-MODEL-QA.json': 'BASE-1.10-SHARED-MODEL-QA.json',
}

GUIDE = '''VOICE STUDIO {version} - GÓI WINDOWS ĐẦY ĐỦ ĐƯỢC GHÉP LẠI

Gói có Python Windows, FFmpeg, model Nano/Turbo và bộ cài 19 mẫu giọng mã hóa
từ bản 1.10 công khai đã kiểm tra SHA256. Mã ứng dụng đã được cập nhật.
{qa_status} Xem BUILD_INFO.json để phân biệt kiểm tra bản nền và bản mới.
Chưa chứng minh mục tiêu tạo 1 giờ lời đọc trong 2 phút hoặc nhanh ngang Turbo.

1. Giải nén TOÀN BỘ ZIP vào một thư mục mới có quyền ghi. Không ghi đè lên
   tool đang mở. Giữ nguyên cấu trúc runtime, ffmpeg, app và delivery.
2. Chạy CAI_19_GIONG.bat nếu cần mở bộ mẫu, dùng mật khẩu bạn đã có từ trước.
   Gói không chứa mật khẩu và không xuất bản các bản thu đã giải mã.
3. Chạy MO_TOOL.bat, kiểm tra phiên bản {version} trên giao diện.
4. Muốn dùng dữ liệu cũ: đóng cả hai tool và sao lưu thư mục cũ. Hợp nhất
   app\\.data và app\\voice-library cũ vào cùng vị trí trong bản mới;
   không xóa thư mục mới trước khi chép. Trong app\\.data\\models, chọn
   Bỏ qua đối với tệp trùng tên để giữ các model và marker mới đã kiểm tra.
   Có thể chép runtime-international cũ nếu còn dùng bộ VoxCPM PyTorch.
   KHÔNG thay runtime-native mới bằng thư mục runtime-native của bản cũ:
   DLL OmniVoice cũ có thể không chứa bộ đọc VoxCPM2 mới.

Python, Nano/Turbo và bộ cài mẫu đã có trong ZIP.
{international_status}
Không tự coi mọi ngôn ngữ là giọng Turbo.

Các tệp BASE-1.10-* là bằng chứng của bản nền cũ; không phải kiểm thử lại
mã hiện tại. MANIFEST.sha256 mô tả chính các tệp trong gói mới, không chứa
checksum của bản thân manifest. Tệp .zip.sha256 đi cạnh ZIP kiểm tra cả ZIP.
'''


def _read_source(path, root):
    path = Path(path)
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('Source symlinks and paths outside source are not accepted')
    if not path.is_file():
        raise ValueError('Required source file is missing: ' + path.name)
    return path.read_bytes()


def _version(payload):
    tree = ast.parse(payload.decode('utf-8'))
    versions = []
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'app' for target in node.targets)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == 'FastAPI'):
            versions.extend(keyword.value.value for keyword in node.value.keywords
                            if keyword.arg == 'version' and isinstance(keyword.value, ast.Constant))
    if len(versions) != 1 or not isinstance(versions[0], str):
        raise ValueError('Current app must declare exactly one FastAPI version')
    value = versions[0]
    if not value or any(character not in '0123456789.' for character in value):
        raise ValueError('Application version must contain digits and dots')
    return value


def _sources(root):
    app = root / 'app'
    static = app / 'static'
    if app.is_symlink() or static.is_symlink() or not app.is_dir() or not static.is_dir():
        raise ValueError('Application/static source directories must be real directories')
    contents = {}
    for path in sorted(app.iterdir()):
        if path.name.startswith(('.', 'test_')) or path.suffix not in {'.py', '.ps1'}:
            continue
        contents['app/' + path.name] = _read_source(path, root)
    for directory, directories, files in os.walk(static, followlinks=False):
        current = Path(directory)
        for name in directories:
            if (current / name).is_symlink():
                raise ValueError('Static source symlink directories are not accepted')
        directories[:] = sorted(name for name in directories
                                if not name.startswith('.') and name not in _FORBIDDEN)
        for name in sorted(files):
            path = current / name
            if path.is_symlink():
                raise ValueError('Static source symlinks are not accepted')
            if not name.startswith('.') and path.suffix.lower() in _STATIC_SUFFIXES:
                contents[path.relative_to(root).as_posix()] = _read_source(path, root)
    for required in ('app/app.py', 'app/launcher.py', 'app/static/index.html',
                     'app/static/app.js', 'app/static/style.css'):
        if required not in contents:
            raise ValueError('Required source file is missing: ' + required)
    for name in _ROOT_SOURCE:
        contents[name] = _read_source(root / name, root)
    contents['MO_TOOL.bat'] = _read_source(root / 'packaging/MO_TOOL.bat', root)
    return contents, _version(contents['app/app.py'])


def _base_members(bundle):
    roots, paths, folded = set(), {}, set()
    for entry in bundle.infolist():
        parts = safe_zip_path(entry)
        if not parts:
            raise ValueError('Empty base archive path')
        roots.add(parts[0])
        if entry.is_dir():
            continue
        if len(parts) < 2:
            raise ValueError('Base archive must have one portable root')
        relative = PurePosixPath(*parts[1:]).as_posix()
        folded_path = relative.casefold()
        if folded_path in folded:
            raise ValueError('Duplicate or case-colliding Windows base path: ' + relative)
        folded.add(folded_path)
        if stat.S_IFMT(entry.external_attr >> 16) not in {0, stat.S_IFREG}:
            raise ValueError('Only regular base archive files are accepted')
        if any(part in _FORBIDDEN for part in parts[1:]):
            continue
        # Only model assets under application data may survive a base refresh.
        if '.data' in parts[1:] and tuple(parts[1:4]) != ('app', '.data', 'models'):
            continue
        if parts[1] == 'app' and tuple(parts[1:4]) != ('app', '.data', 'models'):
            continue  # every application source/static file comes from current source
        paths[relative] = entry
    if len(roots) != 1:
        raise ValueError('Base archive must have one portable root')
    missing = _REQUIRED_BASE - paths.keys()
    if missing:
        raise ValueError('Verified base is missing required files: ' + ', '.join(sorted(missing)))
    return paths


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def application_digest(contents):
    records = {name: hashlib.sha256(value).hexdigest()
               for name, value in contents.items() if name.startswith('app/')}
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _pe_x64(path):
    with path.open('rb') as source:
        header = source.read(64)
        if len(header) < 64 or header[:2] != b'MZ':
            return False
        offset = struct.unpack_from('<I', header, 60)[0]
        if not 64 <= offset <= 1024 * 1024:
            return False
        source.seek(offset)
        signature = source.read(26)
    return (len(signature) == 26 and signature[:4] == b'PE\0\0'
            and struct.unpack_from('<H', signature, 4)[0] == 0x8664
            and struct.unpack_from('<H', signature, 22)[0] & 0x2000 != 0
            and struct.unpack_from('<H', signature, 24)[0] == 0x20b)


def _native_assets(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Native root must be a real directory')
    assets, manifests = {}, {}
    for device in ('cpu', 'cuda'):
        directory = root / device
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('Both Windows CPU and CUDA native directories are required')
        manifest_path = directory / 'native-build.json'
        manifest = json.loads(_read_source(manifest_path, root.resolve()))
        required_libraries = {'audiocpp.dll', 'vcruntime140.dll', 'msvcp140.dll', 'vcomp140.dll'}
        if device == 'cuda':
            required_libraries |= {'cudart64_12.dll', 'cublas64_12.dll', 'cublasLt64_12.dll', 'cufft64_11.dll'}
        if (manifest.get('revision') != NATIVE_REVISION or manifest.get('device') != device
                or 'voxcpm2' not in manifest.get('families', [manifest.get('family')])
                or not isinstance(manifest.get('sha256'), dict)
                or not required_libraries <= manifest['sha256'].keys()):
            raise ValueError('Native runtime must identify the pinned VoxCPM2 Windows build')
        if device == 'cuda' and (manifest.get('cuda_toolkit_major') != 12
                                 or '61' not in manifest.get('cuda_architectures', [])):
            raise ValueError('The CUDA package must include CUDA12/sm61 support')
        for name, expected in manifest['sha256'].items():
            path = directory / name
            if (Path(name).name != name or path.is_symlink() or not path.is_file()
                    or not name.lower().endswith('.dll') or sha256(path) != expected or not _pe_x64(path)):
                raise ValueError('Native Windows DLL provenance or PE x64 validation failed: ' + name)
        for path in directory.rglob('*'):
            if path.is_symlink():
                raise ValueError('Native assets cannot contain symlinks')
            if not path.is_file():
                continue
            relative = path.relative_to(directory)
            if any(part in _FORBIDDEN for part in relative.parts):
                raise ValueError('Development/private metadata is not a native runtime asset')
            # Converter tools are needed only at build time, never for inference.
            if path.suffix.lower() in {'.exe', '.pdb', '.lib', '.exp'}:
                continue
            if path.suffix.lower() == '.dll' and (len(relative.parts) != 1 or path.name not in manifest['sha256']):
                raise ValueError('Unrecorded native DLL in runtime')
            if len(relative.parts) == 1 and path.suffix.lower() not in {'.dll', '.json', '.txt', '.md'}:
                raise ValueError('Unexpected native runtime asset: ' + path.name)
            assets['runtime-native/' + device + '/' + relative.as_posix()] = path
        manifests[device] = manifest
    return assets, manifests


def _native_model_assets(data):
    data = Path(data)
    if data.is_symlink() or not data.is_dir():
        raise ValueError('Prepared native model data must be a real directory')
    marker_path = data / 'models/voxcpm-native.ready'
    record = json.loads(_read_source(marker_path, data.resolve()))
    required = {'schema': 1, 'backend': 'voxcpm_native', 'repository': 'openbmb/VoxCPM2',
                'revision': MODEL_REVISION, 'native_source_revision': NATIVE_REVISION,
                'model_dir': 'voxcpm2-native', 'filename': 'voxcpm2-q8_0.gguf'}
    if any(record.get(key) != value for key, value in required.items()):
        raise ValueError('Native VoxCPM2 model provenance does not match the pinned schema')
    path = data / 'models/voxcpm2-native/voxcpm2-q8_0.gguf'
    if (path.is_symlink() or not path.is_file() or type(record.get('size')) is not int
            or path.stat().st_size != record['size'] or sha256(path) != record.get('sha256')):
        raise ValueError('Native VoxCPM2 model SHA256/size does not match the prepared marker')
    with path.open('rb') as source:
        if source.read(4) != b'GGUF':
            raise ValueError('The native VoxCPM2 model is not GGUF')
    assets = {'app/.data/models/voxcpm-native.ready': marker_path,
              'app/.data/models/voxcpm2-native/voxcpm2-q8_0.gguf': path}
    directory = path.parent
    for item in directory.iterdir():
        if item.is_symlink():
            raise ValueError('Prepared native model assets cannot contain symlinks')
        if item.is_file() and item.suffix.lower() in {'.json', '.txt', '.md'}:
            assets['app/.data/models/voxcpm2-native/' + item.name] = item
    return assets, record


def _windows_qa(path, overlay, native_manifests, model_record):
    value = Path(path).read_bytes()
    record = json.loads(value)
    if (record.get('format') != 'native-voxcpm-windows-pcm-v1'
            or record.get('platform') != 'win32'
            or record.get('native_smoke_passed') is not True
            or record.get('private_reference_audio_included') is not False
            or record.get('app_source_sha256') != application_digest(overlay)
            or record.get('native_cpu_sha256') != native_manifests['cpu']['sha256']['audiocpp.dll']
            or record.get('native_model_sha256') != model_record['sha256']
            or len(record.get('requests', [])) < 3
            or not all(r.get('valid_pcm_audio') is True
                       and r.get('execution', {}).get('device') == 'cpu'
                       and r.get('execution', {}).get('backend') == 'voxcpm_native'
                       for r in record['requests'])):
        raise ValueError('Windows QA must attest actual CPU PCM for this exact source/runtime/model')
    return value


def _zip_info(name):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def build_full(base_archive, output, qa_report=None, *, source_root=None, native_root=None,
               native_model=None, windows_qa=None):
    base_archive, output = Path(base_archive), Path(output)
    checksum = Path(str(output) + '.sha256')
    if output.suffix.lower() != '.zip':
        raise ValueError('Output must be a ZIP path')
    if output.exists() or checksum.exists():
        raise FileExistsError('Choose a new output path; existing files are preserved')
    if base_archive.is_symlink() or sha256(base_archive) != BASE_SHA256:
        raise ValueError('Published base SHA256 mismatch; no contents were used')
    root = Path(source_root or SOURCE_ROOT)
    if root.is_symlink():
        raise ValueError('Source root symlinks are not accepted')
    root = root.resolve()
    overlay, version = _sources(root)
    native_paths, native_manifests, model_record = {}, {}, None
    if (native_root is None) != (native_model is None):
        raise ValueError('Provide both the native Windows runtimes and the prepared native model')
    if native_root is not None:
        native_paths, native_manifests = _native_assets(native_root)
        model_paths, model_record = _native_model_assets(native_model)
        native_paths.update(model_paths)
    if windows_qa is not None:
        if not native_paths:
            raise ValueError('Native Windows QA requires bundled native runtime and model')
        overlay['WINDOWS-NATIVE-VOXCPM-QA.json'] = _windows_qa(windows_qa, overlay, native_manifests, model_record)
    portable_name = 'Voice-Studio-' + version + '-Full-Windows-x64'
    if qa_report is not None:
        from build_speed_update import _qa_report
        overlay['INTERNATIONAL-PACKING-QA.json'] = _qa_report(qa_report)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.' + uuid.uuid4().hex + '.part')
    try:
        with zipfile.ZipFile(base_archive) as source:
            members = _base_members(source)
            base_info = json.loads(source.read(members['BUILD_INFO.json']))
            overlay['BUILD_INFO.json'] = _json_bytes({
                'product': 'Voice Studio Rieng', 'version': version,
                'package_type': 'windows-x64-portable-reassembled',
                'application_source_base_commit': SOURCE_BASE_COMMIT,
                'application_source_commit': os.environ.get('GITHUB_SHA'),
                'application_source_modified': True,
                'verified_base_sha256': BASE_SHA256,
                'base_product_version': base_info.get('version'),
                'base_native_windows_offline_smoke': base_info.get('native_windows_offline_smoke'),
                'current_native_windows_offline_smoke': 'passed' if windows_qa is not None else 'not_run',
                'current_gpu_inference_test': 'not_run',
                'bundled_runtime': True, 'bundled_model_weights': ['vieneu_nano', 'vieneu_turbo'],
                'international_runtime_bundled': bool(native_paths),
                'international_runtime_type': 'native-windows-c-abi' if native_paths else None,
                'international_model_bundled': model_record is not None,
                'international_model': model_record,
                'native_cpu_library_bundled': bool(native_paths),
                'native_cuda_library_bundled': bool(native_paths),
                'encrypted_private_pack_bundled': True,
                'decoded_private_voice_library_bundled': False,
                'personal_history_or_recordings_bundled': False,
                'target_30x_guaranteed': False, 'full_hour_30x_validated': False,
                'real_speech_qa_included': qa_report is not None,
                'file_manifest': 'MANIFEST.sha256',
            })
            overlay['DOC_TRUOC_FULL.txt'] = GUIDE.format(
                version=version,
                qa_status=('Tạo tiếng ngắn trên Windows CPU đã đạt; GPU chưa được đo.'
                           if windows_qa is not None else 'Chưa chạy lại bản ghép này trên Windows hoặc GPU.'),
                international_status=(
                    'Đã kèm VoxCPM2 Q8 GGUF cùng bộ native CPU/CUDA12 có mã sm61.\n'
                    'Chọn đúng mẫu giọng/ngôn ngữ, chọn bộ VoxCPM2 native Q8,\n'
                    'chọn CUDA rồi Nhanh và bấm Đo giọng đang chọn để đo/nghe mẫu.\n'
                    'CPU vẫn có thể chậm; không suy ra tốc độ GPU từ phép thử CPU.\n'
                    'CUDA cần driver NVIDIA tương thích; tốc độ GTX1060 chưa được xác minh.'
                    if native_paths else
                    'Bộ giọng quốc tế VoxCPM2 vẫn cần runtime/model riêng khi chưa cài.\n'
                    'Xem BUILD_INFO.json và TAI_GIONG_DA_NGON_NGU.bat.'),
            ).encode('utf-8')
            digests = {}
            with temporary.open('xb') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED,
                                                               compresslevel=5, allowZip64=True) as target:
                for relative, entry in sorted(members.items()):
                    name = _BASE_RENAMES.get(relative, relative)
                    if name in overlay or name in native_paths or relative == 'MO_TOOL.bat':
                        continue
                    digest = hashlib.sha256()
                    info = _zip_info(portable_name + '/' + name)
                    with source.open(entry) as incoming, target.open(info, 'w', force_zip64=True) as destination:
                        for block in iter(lambda: incoming.read(1024 * 1024), b''):
                            digest.update(block)
                            destination.write(block)
                    digests[name] = digest.hexdigest()
                for relative, path in sorted(native_paths.items()):
                    digest = hashlib.sha256()
                    with path.open('rb') as incoming, target.open(_zip_info(portable_name + '/' + relative), 'w', force_zip64=True) as destination:
                        for block in iter(lambda: incoming.read(1024 * 1024), b''):
                            digest.update(block)
                            destination.write(block)
                    digests[relative] = digest.hexdigest()
                for relative, payload in sorted(overlay.items()):
                    target.writestr(_zip_info(portable_name + '/' + relative), payload, compresslevel=5)
                    digests[relative] = hashlib.sha256(payload).hexdigest()
                manifest = ''.join(digest + '  ' + name + '\n' for name, digest in sorted(digests.items()))
                target.writestr(_zip_info(portable_name + '/MANIFEST.sha256'), manifest.encode('utf-8'), compresslevel=5)
        digest = sha256(temporary)
        temporary.rename(output)
        with checksum.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(digest + '  ' + output.name + '\n')
        return output, checksum
    finally:
        temporary.unlink(missing_ok=True)


def split_release(archive, directory, *, part_bytes=1536 * 1024**2):
    """Split a full ZIP into release-sized raw pieces, retaining whole-ZIP SHA.

    Windows' built-in copy command rejoins them. The generated command checks
    the complete SHA256 with built-in PowerShell before moving the result to
    its final name; it neither disables script policy nor downloads anything.
    """
    archive, directory = Path(archive), Path(directory)
    if (archive.is_symlink() or not archive.is_file()
            or not re.fullmatch(r'[A-Za-z0-9_.-]+\.zip', archive.name)):
        raise ValueError('Release splitting needs a regular ZIP with an ASCII-safe filename')
    if type(part_bytes) is not int or not 1 <= part_bytes < 2 * 1024**3:
        raise ValueError('Release pieces must be positive and smaller than 2GiB')
    if directory.exists():
        raise FileExistsError('Use a new release-parts directory')
    directory.mkdir(parents=True)
    parts, total_digest = [], hashlib.sha256()
    try:
        with archive.open('rb') as source:
            index = 0
            while True:
                first = source.read(min(1024**2, part_bytes))
                if not first:
                    break
                index += 1
                part = directory / f'{archive.name}.part{index:03d}'
                digest, size = hashlib.sha256(), 0
                with part.open('xb') as output:
                    block = first
                    while block:
                        digest.update(block)
                        total_digest.update(block)
                        output.write(block)
                        size += len(block)
                        if size == part_bytes:
                            break
                        block = source.read(min(1024**2, part_bytes - size))
                parts.append({'name': part.name, 'size': size, 'sha256': digest.hexdigest()})
        if not parts:
            raise ValueError('A release archive cannot be empty')
        expected = total_digest.hexdigest()
        joined = archive.name + '.assembling'
        sources = '+'.join('"' + part['name'] + '"' for part in parts)
        command = (
            '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
            f'if exist "{archive.name}" (echo Tep ZIP da ton tai. Giu nguyen tep cu va dung thu muc moi. & pause & exit /b 1)\r\n'
            f'if exist "{joined}" (echo Tep ghep do da ton tai. Dung thu muc moi. & pause & exit /b 1)\r\n'
            f'copy /b {sources} "{joined}"\r\n'
            'if errorlevel 1 goto failed\r\n'
            'powershell.exe -NoProfile -Command "'
            f"if ((Get-FileHash -LiteralPath '{joined}' -Algorithm SHA256).Hash.ToLowerInvariant() -ne '{expected}') "
            "{ Write-Error 'SHA256 khong khop. Khong dung tep ZIP nay.'; exit 1 }\"\r\n"
            'if errorlevel 1 goto failed\r\n'
            f'move /-y "{joined}" "{archive.name}"\r\n'
            'if errorlevel 1 exit /b 1\r\n'
            'echo Da ghep va kiem tra SHA256 thanh cong. Giai nen toan bo ZIP de dung tool.\r\npause\r\nexit /b 0\r\n'
            ':failed\r\n'
            f'if exist "{joined}" del /q "{joined}"\r\n'
            'echo Ghép loi hoac SHA256 khong khop. Tai lai day du cac phan.\r\npause\r\nexit /b 1\r\n'
        )
        # Keep the launcher ASCII so cmd.exe does not depend on a code page.
        command = command.replace('Ghép', 'Ghep')
        (directory / 'GHEP_GOI.cmd').write_bytes(command.encode('ascii'))
        (directory / (archive.name + '.sha256')).write_text(expected + '  ' + archive.name + '\n', encoding='utf-8')
        (directory / 'DOWNLOAD-PARTS.sha256').write_text(''.join(
            part['sha256'] + '  ' + part['name'] + '\n' for part in parts), encoding='utf-8')
        manifest = {'format': 'voice-studio-full-zip-parts-v1', 'archive': archive.name,
                    'archive_sha256': expected, 'archive_size': archive.stat().st_size, 'parts': parts}
        (directory / 'DOWNLOAD-PARTS.json').write_bytes(_json_bytes(manifest))
        (directory / 'DOC_TAI_VE.txt').write_text(
            'TẢI GÓI VOICE STUDIO ĐẦY ĐỦ\n\n'
            'Tải TẤT CẢ các tệp .part001, .part002… và GHEP_GOI.cmd vào cùng một thư mục mới.\n'
            'Mở GHEP_GOI.cmd để nối thành ZIP và kiểm tra SHA256. Sau đó giải nén toàn bộ ZIP.\n'
            'Giữ nguyên tên các phần; cần đủ mọi phần mới dùng được. Không mở riêng từng phần như một ZIP.\n'
            'Các phần tồn tại vì giới hạn kích thước mỗi tệp phát hành của GitHub.\n'
            'Không cần cài Python để ghép; dùng các công cụ sẵn có trong Windows.\n', encoding='utf-8')
        return directory
    except BaseException:
        # This directory was created by this call and contains only its outputs.
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()
        directory.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--qa-report', type=Path)
    parser.add_argument('--native-root', type=Path, help='Staged Windows CPU/CUDA runtimes, both required')
    parser.add_argument('--native-model', type=Path, help='Prepared data dir containing models/voxcpm-native.ready')
    parser.add_argument('--windows-qa', type=Path, help='Actual Windows CPU PCM report for the same source/runtime/model')
    parser.add_argument('--release-parts', type=Path, help='Optional new directory for release-sized pieces and verified Windows joiner')
    args = parser.parse_args(argv)
    for path in build_full(args.base_archive, args.output, args.qa_report,
                           native_root=args.native_root, native_model=args.native_model,
                           windows_qa=args.windows_qa):
        print(path, flush=True)
    if args.release_parts is not None:
        print(split_release(args.output, args.release_parts), flush=True)


if __name__ == '__main__':
    main()
