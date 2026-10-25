"""Validate the complete Hmong application without third-party dependencies."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PYTHON_FILES = (
    'app.py', 'bundle_check.py', 'caption_markers.py', 'character_cast.py', 'dubbing.py', 'hardware.py', 'hmong_acceleration.py', 'hmong_assets.py',
    'hmong_engine.py', 'hmong_expression.py', 'hmong_f5.py', 'hmong_health.py', 'hmong_launcher.py',
    'hmong_native.py', 'hmong_native_models.py',
    'hmong_reference.py', 'hmong_text.py',
    'language_catalog.py', 'local_vieneu.py', 'longform.py', 'narration.py', 'performance.py', 'reference_quality.py',
    'portable_launcher.py', 'runtime_instance.py', 'prepare_hmong.py', 'prepare_hmong_native.py', 'prepare_models.py',
    'prepare_subtitles.py', 'recognition.py', 'state_io.py', 'studio_variant.py',
    'subtitles.py', 'system_voices.py', 'translation.py', 'video_editor.py',
    'video_export.py', 'video_tasks.py', 'voice_errors.py', 'worker.py', 'writing.py',
)
STATIC_FILES = tuple('static/' + name for name in (
    'index.html', 'style.css', 'app.js', 'workspace.js', 'studio-tools.js',
    'video-editor.js', 'video-preview.js', 'direct-video.js',
))
ASSET_FILES = tuple('assets/hmong/' + name for name in (
    'voices.json', 'female.wav', 'male.wav', 'source-female.mp3', 'source-male.mp3',
))
DOCUMENTATION_FILES = ('docs/HUONG-DAN-HMONG.md', 'docs/HUONG-DAN-HMONG.html')
REQUIRED_FILES = PYTHON_FILES + STATIC_FILES + ASSET_FILES + DOCUMENTATION_FILES + ('hmong_native_vendor/manifest.json',)
NATIVE_VENDOR_REQUIRED = (
    '__init__.py', 'UPSTREAM.json', 'vits/__init__.py', 'vits/models.py',
    'vits/modules.py', 'vits/commons.py', 'vits/attentions.py', 'vits/transforms.py',
    'vits/symbols.py', 'vits/LICENSE', 'vits/TEXT-LICENSE',
    'openvoice/__init__.py', 'openvoice/models.py', 'openvoice/modules.py',
    'openvoice/commons.py', 'openvoice/attentions.py', 'openvoice/transforms.py',
    'openvoice/mel_processing.py', 'openvoice/LICENSE', 'watermark/__init__.py',
    'watermark/models/__init__.py', 'watermark/models/my_model.py', 'watermark/models/hinet.py',
    'watermark/models/invblock.py', 'watermark/models/rrdb_denselayer.py',
    'watermark/models/module_util.py', 'watermark/LICENSE',
)


class BundleError(RuntimeError):
    pass


def _repair_message(detail):
    return (detail + '\nGiải nén TOÀN BỘ ZIP Voice Studio Hmong vào một thư mục có quyền ghi, '
            'rồi mở MO_VOICE_STUDIO_HMONG.bat ở thư mục gốc. '
            'Chép riêng các tệp .py/.bat không đủ để chạy tool. Dữ liệu cá nhân không bị xóa.')


def validate_native_vendor(base):
    """Check vendored code and its licenses without importing model code."""
    root = Path(base) / 'hmong_native_vendor'
    try:
        manifest = root / 'manifest.json'
        if manifest.is_symlink() or manifest.stat().st_size > 100_000:
            raise ValueError('invalid native code manifest')
        records = json.loads(manifest.read_text(encoding='utf-8'))
        if not isinstance(records, dict) or not set(NATIVE_VENDOR_REQUIRED).issubset(records):
            raise ValueError('native code or license missing from manifest')
        for name, expected in records.items():
            if (not isinstance(name, str) or '\\' in name or ':' in name or name.startswith('/')
                    or any(part in {'', '.', '..'} for part in name.split('/'))):
                raise ValueError('invalid native code path')
            path = root / name
            if (not (path.suffix == '.py' or path.name in {'LICENSE', 'TEXT-LICENSE', 'UPSTREAM.json'})
                    or path.is_symlink() or any(parent.is_symlink() for parent in path.parents
                                               if parent != root.parent)):
                raise ValueError('unapproved native code file: ' + name)
            if (not isinstance(expected, str) or len(expected) != 64
                    or any(char not in '0123456789abcdef' for char in expected)):
                raise ValueError('invalid native code checksum')
            if not path.is_file() or not path.stat().st_size or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('native code checksum mismatch: ' + name)
        return len(records)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise BundleError(_repair_message('Mã hoặc giấy phép bộ đọc nhanh không hợp lệ: ' + str(exc))) from None


def validate_bundle(base=None):
    """Check actual UI/modules and immutable voice assets before reporting PASS."""
    base = Path(base) if base is not None else Path(__file__).resolve().parent
    missing = []
    for relative in REQUIRED_FILES:
        try:
            good = (base / relative).is_file() and (base / relative).stat().st_size > 0
        except OSError:
            good = False
        if not good:
            missing.append(relative)
    if missing:
        # Include static/assets even if many source modules were omitted.
        shown = missing[:6] + [name for name in missing[6:] if name.startswith(('static/', 'assets/'))][:6]
        raise BundleError(_repair_message('Bộ tool thiếu hoặc có tệp bắt buộc rỗng: ' + ', '.join(shown)))
    root = base / 'assets' / 'hmong'
    try:
        manifest_path = root / 'voices.json'
        if manifest_path.stat().st_size > 100_000:
            raise ValueError('voice manifest too large')
        records = json.loads(manifest_path.read_text(encoding='utf-8'))
        for gender in ('male', 'female'):
            item = records[gender]
            for key, checksum in (('file', 'sha256'), ('reference_file', 'reference_sha256')):
                relative = item[key]
                if (not isinstance(relative, str) or Path(relative).name != relative
                        or '/' in relative or '\\' in relative):
                    raise ValueError('invalid voice filename')
                path = root / relative
                expected = item[checksum]
                if (not isinstance(expected, str) or len(expected) != 64
                        or any(char not in '0123456789abcdef' for char in expected)):
                    raise ValueError('invalid voice checksum')
                with path.open('rb') as stream:
                    digest = hashlib.sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(block)
                    actual = digest.hexdigest()
                if actual != expected:
                    raise ValueError('voice checksum mismatch: ' + relative)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise BundleError(_repair_message('Tệp giọng mặc định hoặc SHA256 không hợp lệ: ' + str(exc))) from None
    vendor_checksums = validate_native_vendor(base)
    return {'application_files': len(REQUIRED_FILES) + vendor_checksums,
            'voice_checksums': 4, 'native_code_checksums': vendor_checksums}


if __name__ == '__main__':
    try:
        validate_bundle()
        print('PASS: đủ tệp ứng dụng, giao diện và bốn checksum giọng mặc định.')
    except BundleError as exc:
        print('LỖI: ' + str(exc), file=sys.stderr)
        sys.exit(1)
