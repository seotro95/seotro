"""Apply the small 1.5.1 source repair using the existing portable Python only."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


ALLOWLIST = frozenset({
    'app.py', 'portable_launcher.py', 'runtime_instance.py', 'bundle_check.py',
    'studio_variant.py', 'hmong_launcher.py', 'HMONG-README.md',
    'docs/HMONG-NATIVE.md', 'VALIDATION-HMONG.md',
})
REQUIRED_PAYLOAD = frozenset({
    'app.py', 'portable_launcher.py', 'runtime_instance.py', 'bundle_check.py',
    'studio_variant.py', 'hmong_launcher.py', 'HMONG-README.md',
})
BASE_REQUIRED = (
    'app.py', 'studio_variant.py', 'hmong_launcher.py', 'hmong_assets.py',
    'hmong_acceleration.py', 'hmong_native.py', 'hmong_native_models.py',
    'worker.py', 'state_io.py', 'static/index.html',
    'hmong_native_vendor/manifest.json', 'hmong_native_vendor/vits/models.py',
    'hmong_native_vendor/openvoice/models.py', 'hmong_native_vendor/watermark/models/my_model.py',
)
BASE_ASSETS = (
    'assets/hmong/voices.json', 'assets/hmong/female.wav', 'assets/hmong/male.wav',
    'assets/hmong/source-female.mp3', 'assets/hmong/source-male.mp3',
)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def safe_path(base, relative):
    if (not isinstance(relative, str) or '\\' in relative or ':' in relative
            or relative.startswith('/') or any(p in {'', '.', '..'} for p in relative.split('/'))):
        raise RuntimeError('Unsafe update path: ' + str(relative))
    path = Path(base)
    if path.is_symlink():
        raise RuntimeError('Linked update/install folders are not supported: ' + str(path))
    for part in relative.split('/'):
        path = path / part
        if path.is_symlink():
            raise RuntimeError('Linked update/install files are not supported: ' + str(path))
    return path


def read_version(path):
    try:
        tree = ast.parse(Path(path).read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'APP_VERSION' for t in node.targets):
                for value in ast.walk(node.value):
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        match = re.fullmatch(r'(\d+\.\d+\.\d+)-hmong', value.value)
                        if match:
                            return match.group(1)
    except (OSError, SyntaxError, UnicodeError):
        pass
    raise RuntimeError('Cannot identify the installed Hmong version safely.')


def load_payload(patch):
    manifest_path = safe_path(patch, 'manifest.json')
    try:
        if manifest_path.stat().st_size > 100_000:
            raise ValueError('manifest too large')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        files = manifest['files']
        if (manifest.get('format') != 1 or manifest.get('product') != 'Voice Studio Hmong'
                or manifest.get('base_version') != '1.5.0' or manifest.get('version') != '1.5.1'
                or not isinstance(files, dict) or not REQUIRED_PAYLOAD.issubset(files)
                or not set(files).issubset(ALLOWLIST)
                or set(manifest['base_assets']) != set(BASE_ASSETS)):
            raise ValueError('unsupported update manifest')
        payload = {}
        for name, expected in files.items():
            path = safe_path(Path(patch) / 'files', name)
            raw = path.read_bytes()
            if (type(expected.get('bytes')) is not int or expected['bytes'] != len(raw)
                    or expected.get('sha256') != digest(raw) or not raw):
                raise ValueError('payload checksum/size mismatch: ' + name)
            payload[name] = raw
        if read_version(safe_path(Path(patch) / 'files', 'studio_variant.py')) != manifest['version']:
            raise ValueError('payload version mismatch')
        for expected in manifest['base_assets'].values():
            if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                raise ValueError('invalid base asset checksum')
        return manifest, payload
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise RuntimeError('Update validation failed before writing files: ' + str(exc)) from None


def validate_install(root, manifest):
    root = Path(root).absolute()
    app = safe_path(root, 'voice-studio-hmong')
    for name in ('runtime/python.exe', 'MO_HMONG_NHANH.bat'):
        path = safe_path(root, name)
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError('This is not a complete Windows portable installation: ' + name)
    for name in BASE_REQUIRED:
        path = safe_path(app, name)
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError('The native Hmong base installation is incomplete: ' + name)
    version = read_version(safe_path(app, 'studio_variant.py'))
    if version not in {manifest['base_version'], manifest['version']}:
        raise RuntimeError('Unsupported Hmong base version: ' + version + '. Expected 1.5.0 or 1.5.1.')
    for name, expected in manifest['base_assets'].items():
        path = safe_path(app, name)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise RuntimeError('Default Hmong voice assets do not match the 1.5 base: ' + name)
    return root, app


def atomic_write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.update', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def apply_update(root, patch=None, *, verify_only=False):
    patch = Path(patch) if patch is not None else Path(__file__).resolve().parent
    manifest, payload = load_payload(patch)
    root, app = validate_install(root, manifest)
    changed = []
    for name, raw in payload.items():
        target = safe_path(app, name)
        if target.exists() and not target.is_file():
            raise RuntimeError('An update destination is not a regular file: ' + name)
        if not target.is_file() or target.read_bytes() != raw:
            changed.append(name)
        if name.endswith('.py'):
            module = Path(name)
            cache = safe_path(app, str(module.parent / '__pycache__').replace('\\', '/'))
            if cache.exists() and not cache.is_dir():
                raise RuntimeError('The Python cache path is not a directory: ' + str(cache))
    if verify_only:
        if changed:
            raise RuntimeError('Installed source differs from the repair: ' + ', '.join(changed))
        return {'status': 'verified', 'changed': [], 'backup': None, 'version': manifest['version']}
    if not changed:
        return {'status': 'already-current', 'changed': [], 'backup': None, 'version': manifest['version']}
    # All source, base, destination and payload checks finish before any write.
    backup = safe_path(app, '.data/update-backups/' + uuid.uuid4().hex)
    backup.mkdir(parents=True, exist_ok=False)
    originals = {}
    for name in changed:
        target = safe_path(app, name)
        originals[name] = target.read_bytes() if target.is_file() else None
        if originals[name] is not None:
            saved = safe_path(backup, name)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    applied = []
    try:
        for name in changed:
            atomic_write(safe_path(app, name), payload[name])
            applied.append(name)
    except BaseException as failure:
        rollback_errors = []
        for name in reversed(applied):
            try:
                target = safe_path(app, name)
                if originals[name] is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, originals[name])
            except OSError as exc:
                rollback_errors.append(name + ': ' + str(exc))
        if rollback_errors:
            raise RuntimeError('Repair failed; some files could not be restored. Original source backup: '
                               + str(backup) + '. ' + '; '.join(rollback_errors)) from failure
        raise
    for name in changed:
        if name.endswith('.py'):
            module = Path(name)
            cache = safe_path(app, str(module.parent / '__pycache__').replace('\\', '/'))
            if cache.is_dir():
                for pyc in cache.glob(module.stem + '.*.pyc'):
                    if pyc.is_file() and not pyc.is_symlink():
                        try:
                            pyc.unlink()
                        except OSError:
                            pass  # Fresh source timestamps also invalidate an old cache.
    return {'status': 'updated', 'changed': changed, 'backup': str(backup), 'version': manifest['version']}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Repair Voice Studio Hmong 1.5.0 startup without downloading models.')
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--no-launch', action='store_true')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = apply_update(args.root, verify_only=args.verify_only)
        print('PASS: ' + json.dumps(result, ensure_ascii=False), flush=True)
        if not args.no_launch and not args.verify_only:
            if os.name != 'nt':
                raise RuntimeError('Use --no-launch when checking the Windows update on another OS.')
            return subprocess.call(['cmd.exe', '/d', '/c', 'call', 'MO_HMONG_NHANH.bat'], cwd=args.root)
        return 0
    except (OSError, RuntimeError) as exc:
        print('LOI: ' + str(exc), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
