"""Build a code-only 1.11.1 update for an existing Windows installation.

No runtimes, models, recordings or installation data are read or bundled.
The archive is an overlay of application source, not a standalone Windows tool.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import zipfile


VERSION = '1.11.1'
BASE_SOURCE_COMMIT = '888d1dbbb7153177dbaa31a213efd8ffc428b012'
ROOT_NAME = 'Voice-Studio-1.11.1-Speed-Update'
SOURCE_ROOT = Path(__file__).resolve().parents[1]
QA_NAME = 'INTERNATIONAL-PACKING-QA.json'
MANIFEST_NAME = 'UPDATE_MANIFEST.sha256'
_EXCLUDED_PARTS = frozenset({'.data', 'voice-library', 'models', 'tests',
                            '__pycache__', '.pytest_cache', '.cache',
                            'runtime', 'runtime-international', 'runtime-native'})
_STATIC_SUFFIXES = frozenset({'.html', '.js', '.css'})

GUIDE = '''CẬP NHẬT MÃ VOICE STUDIO 1.11.1

Đây là bản cập nhật mã cho tool Windows 1.10/1.11 đã cài sẵn.
Gói này không chứa Python runtime, model, thư viện GPU hoặc mẫu giọng;
không thể chạy độc lập khi chưa có bộ tool cũ.

1. Đóng tool và cửa sổ MO_TOOL.bat. Chờ mọi tác vụ tạo tiếng dừng hẳn.
2. Sao lưu toàn bộ thư mục tool cũ trước khi cập nhật.
3. Giải nén ZIP này vào một thư mục tạm riêng.
4. Trong thư mục vừa giải nén, chép thư mục app vào thư mục tool cũ,
   cùng cấp với MO_TOOL.bat. Chấp nhận thay thế các tệp mã cùng tên.
   Không chép app vào bên trong app cũ, không xóa app cũ để thay toàn bộ.
5. Giữ nguyên runtime, runtime-international, runtime-native, app\\.data
   và app\\voice-library. Lịch sử, model và các mẫu giọng cũ nằm ở đó.
   Gói cập nhật không chứa các thư mục dữ liệu này.
6. Mở lại MO_TOOL.bat và kiểm tra phiên bản 1.11.1 trên giao diện.

Giữ nguyên BUILD_INFO.json và MANIFEST.sha256 của bộ cài cũ: hai tệp đó
mô tả bộ cài gốc. UPDATE_INFO.json và UPDATE_MANIFEST.sha256 trong gói
này mô tả riêng bản cập nhật; không dùng chúng để ghi đè manifest cũ.

Để ghép các câu ngắn khi đọc giọng quốc tế, chọn chế độ Nhanh,
khoảng nghỉ đoạn 0 giây (paragraph_pause=0), và 1 tiến trình.
Giữ đúng giọng và ngôn ngữ đã chọn; nghe mẫu trước khi đọc bản dài.
Giảm số bước có thể ảnh hưởng phát âm. Không có cam kết nhanh ngang Turbo.
Bản cập nhật mã này chưa được chạy thử trên Windows hoặc GPU trong phiên này.

Công cụ đo tùy chọn: chép thêm thư mục tools vào thư mục tool cũ để có
tools\\benchmark_international_packing.py. Chạy công cụ bằng Python trong
runtime-international đã cài, với model và mẫu WAV trên máy; không tải model.
Dùng --help để xem tham số. Kết quả ghi rõ thời gian và độ dài tiếng thực;
không dùng khoảng im lặng của SRT để tính tốc độ.
Nếu có INTERNATIONAL-PACKING-QA.json, đó là báo cáo mẫu ngắn đi kèm;
không chứng minh chất lượng/tốc độ của mọi giọng hoặc GTX 1060.
'''


def _read_source(path, boundary):
    path, boundary = Path(path), Path(boundary).resolve()
    if path.is_symlink() or not path.resolve().is_relative_to(boundary):
        raise ValueError('Source symlinks and paths outside the source tree are not allowed')
    if not path.is_file():
        raise ValueError('A required update source file is missing: ' + path.name)
    return path.read_bytes()


def _source_version(source):
    try:
        tree = ast.parse(source.decode('utf-8'))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError('app.py must be valid UTF-8 Python source') from exc
    versions = []
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'app' for target in node.targets)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == 'FastAPI'):
            versions.extend(keyword.value.value for keyword in node.value.keywords
                            if keyword.arg == 'version' and isinstance(keyword.value, ast.Constant))
    if versions != [VERSION]:
        raise ValueError('app.py must declare FastAPI version ' + VERSION)
    return VERSION


def _collect_source(root):
    app = root / 'app'
    if app.is_symlink() or not app.is_dir():
        raise ValueError('The application source directory must be a real directory')
    contents = {}
    for path in sorted(app.iterdir()):
        if (path.name.startswith('.') or path.name.startswith('test_')
                or path.suffix not in {'.py', '.ps1'}):
            continue
        contents['app/' + path.name] = _read_source(path, root)
    if 'app/app.py' not in contents:
        raise ValueError('app.py is required for the update')
    _source_version(contents['app/app.py'])
    static = app / 'static'
    if static.is_symlink() or not static.is_dir():
        raise ValueError('The static source directory must be a real directory')
    for directory, directories, files in os.walk(static, followlinks=False):
        base = Path(directory)
        for name in directories:
            if (base / name).is_symlink():
                raise ValueError('Source symlink directories are not allowed')
        directories[:] = sorted(name for name in directories
                                if not name.startswith('.') and name not in _EXCLUDED_PARTS)
        for name in sorted(files):
            path = base / name
            if path.is_symlink():
                raise ValueError('Source symlinks are not allowed')
            if name.startswith('.') or path.suffix.lower() not in _STATIC_SUFFIXES:
                continue
            contents[path.relative_to(root).as_posix()] = _read_source(path, root)
    for required in ('app/static/index.html', 'app/static/app.js', 'app/static/style.css'):
        if required not in contents:
            raise ValueError('A required static asset is missing: ' + required)
    benchmark = root / 'packaging/benchmark_international_packing.py'
    contents['tools/benchmark_international_packing.py'] = _read_source(benchmark, root)
    return contents


def _qa_report(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('The QA report must be a regular JSON file')
    payload = path.read_bytes()
    try:
        report = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('The QA report must be valid JSON') from exc
    if (not isinstance(report, dict)
            or report.get('format') != 'international-packing-real-speech-v1'
            or report.get('private_reference_audio_included') is not False
            or not isinstance(report.get('results'), list) or not report['results']):
        raise ValueError('The QA report must be a completed international packing report without reference audio')
    return payload


def build_update(output, qa_report=None, *, source_root=None):
    root = Path(source_root or SOURCE_ROOT)
    if root.is_symlink():
        raise ValueError('The source root must not be a symlink')
    root = root.resolve()
    output = Path(output)
    checksum = Path(str(output) + '.sha256')
    if output.suffix.lower() != '.zip':
        raise ValueError('--output must name a ZIP file')
    if output.exists() or checksum.exists():
        raise FileExistsError('Choose a new output ZIP path; existing files are preserved')
    contents = _collect_source(root)
    if qa_report is not None:
        contents[QA_NAME] = _qa_report(qa_report)
    metadata = {
        'version': VERSION, 'package_type': 'code-only-update',
        'base_source_commit': BASE_SOURCE_COMMIT,
        'existing_installation_required': True,
        'supported_existing_versions': ['1.10', '1.11'],
        'native_runtimes_bundled': False, 'model_weights_bundled': False,
        'private_voice_data_bundled': False, 'standalone_windows_runtime': False,
        'native_windows_qa_run_in_this_session': False,
        'gpu_qa_run_in_this_session': False, 'turbo_speed_parity_verified': False,
        'real_speech_qa_included': qa_report is not None,
        'qa_report': QA_NAME if qa_report is not None else None,
        'existing_build_info_and_manifest_replaced': False,
    }
    contents['UPDATE_INFO.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    contents['DOC_CAP_NHAT.txt'] = GUIDE.encode('utf-8')
    contents[MANIFEST_NAME] = ''.join(
        hashlib.sha256(payload).hexdigest() + '  ' + name + '\n'
        for name, payload in sorted(contents.items())).encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, payload in sorted(contents.items()):
            info = zipfile.ZipInfo(ROOT_NAME + '/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload, compresslevel=6)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    with checksum.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(digest + '  ' + output.name + '\n')
    return output, checksum


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New ZIP file path')
    parser.add_argument('--qa-report', type=Path, help='Optional completed real-speech packing JSON report')
    args = parser.parse_args(argv)
    for path in build_update(args.output, args.qa_report):
        print(path)


if __name__ == '__main__':
    main()
