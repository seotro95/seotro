"""Build a deterministic, source-only repair for an existing Hmong 1.5 bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from apply_hmong_update import BASE_ASSETS, REQUIRED_PAYLOAD, digest, read_version, safe_path


LAUNCHER = '''@echo off
setlocal
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
for %%I in ("%~dp0.") do set "PATCH_ROOT=%%~fI"
if exist "%PATCH_ROOT%\\runtime\\python.exe" if exist "%PATCH_ROOT%\\voice-studio-hmong\\studio_variant.py" goto found
for %%I in ("%~dp0..") do set "PATCH_ROOT=%%~fI"
if exist "%PATCH_ROOT%\\runtime\\python.exe" if exist "%PATCH_ROOT%\\voice-studio-hmong\\studio_variant.py" goto found
echo LOI: Giai nen ban sua loi vao thu muc Voice Studio Hmong 1.5.0 dang co runtime va voice-studio-hmong.
exit /b 1
:found
"%PATCH_ROOT%\\runtime\\python.exe" "%~dp0hmong-update\\apply_update.py" --root "%PATCH_ROOT%" %*
exit /b %ERRORLEVEL%
'''


def build(source, output, *, base_version='1.5.0', version='1.5.1'):
    source, output = Path(source), Path(output)
    if base_version != '1.5.0' or version != '1.5.1':
        raise ValueError('This repair supports base 1.5.0 and target 1.5.1 only.')
    if read_version(safe_path(source, 'studio_variant.py')) != version:
        raise ValueError('Source Hmong version does not match requested patch version.')
    files = {}
    for name in sorted(REQUIRED_PAYLOAD):
        raw = safe_path(source, name).read_bytes()
        if not raw:
            raise ValueError('Empty update source: ' + name)
        files[name] = raw
    manifest = {
        'format': 1, 'product': 'Voice Studio Hmong', 'base_version': base_version, 'version': version,
        'files': {name: {'sha256': digest(raw), 'bytes': len(raw)} for name, raw in files.items()},
        'base_assets': {name: digest(safe_path(source, name).read_bytes()) for name in BASE_ASSETS},
    }
    entries = {
        'SUA_LOI_MO_TOOL.bat': LAUNCHER.replace('\n', '\r\n').encode('ascii'),
        'hmong-update/apply_update.py': Path(__file__).with_name('apply_hmong_update.py').read_bytes(),
        'hmong-update/manifest.json': (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8'),
        **{'hmong-update/files/' + name: raw for name, raw in files.items()},
    }
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'Voice-Studio-Hmong-{version}-Update.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for name, raw in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, raw)
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + '.sha256').write_text(archive_digest + '  ' + archive.name + '\n', encoding='ascii')
    report = {'archive': archive.name, 'sha256': archive_digest, 'bytes': archive.stat().st_size,
              'base_version': base_version, 'version': version, 'files': manifest['files'],
              'models_included': False, 'runtime_included': False}
    (output / 'patch-build.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-version', default='1.5.0')
    parser.add_argument('--version', default='1.5.1')
    args = parser.parse_args(argv)
    print(json.dumps(build(args.source, args.output, base_version=args.base_version, version=args.version), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
