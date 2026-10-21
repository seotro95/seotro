"""Build a relocatable Windows distribution from an explicit clean source set.

The default archive contains Python, CPU dependencies and FFmpeg. Model weights
are downloaded and exercised in CI but are not redistributed: first start uses
the app's integrity-checking model installer. No developer .data is copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
APP_FILES = (
    'audio_io.py', 'bootstrap.py', 'engine.py', 'jobs.py', 'launch.py',
    'longform.py', 'runtime_lock.py', 'server.py', 'setup_voice.py', 'voices.py', 'version.py',
    'requirements-voice.txt', 'start.bat', 'install_voice.bat', 'start.sh',
    'README.md', 'VALIDATION.md', 'SECURITY-REVIEW.md', 'BAT-DAU.txt',
)
FFMPEG_BASE = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
FFMPEG_ASSET = 'ffmpeg-n8.1-latest-win64-gpl-8.1.zip'


def sha256(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def copy_source(destination, source=SOURCE):
    """Never traverse developer data, environments, attachments or job history."""
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name in APP_FILES:
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or linked required application file: ' + name)
        shutil.copy2(path, destination / name)
    for folder in ('web', 'assets'):
        entries = source / folder
        for path in entries.rglob('*'):
            if path.is_symlink():
                raise ValueError('Linked application asset cannot be packaged: ' + str(path))
        shutil.copytree(entries, destination / folder)


def ffmpeg_relative(entry):
    """Validate upstream ZIP names before dropping its common root folder."""
    name = entry.filename.replace('\\', '/')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or any(':' in part for part in path.parts):
        raise ValueError('Unsafe FFmpeg archive path')
    if stat.S_ISLNK(entry.external_attr >> 16):
        raise ValueError('Linked FFmpeg archive entry')
    parts = path.parts[1:]
    if not parts or entry.is_dir() or parts[-1].lower() == 'ffplay.exe':
        return None
    return Path(*parts)


def download_verified_ffmpeg(target, downloads):
    target, downloads = Path(target), Path(downloads)
    downloads.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(FFMPEG_BASE + 'checksums.sha256', timeout=60) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('FFmpeg checksum manifest is too large')
    matches = [line.split()[0] for line in raw.decode('utf-8').splitlines()
               if len(line.split()) == 2 and line.split()[-1].lstrip('*') == FFMPEG_ASSET]
    if len(matches) != 1 or len(matches[0]) != 64:
        raise ValueError('No unique SHA-256 for the selected FFmpeg build')
    expected = matches[0].lower()
    if any(character not in '0123456789abcdef' for character in expected):
        raise ValueError('Invalid FFmpeg SHA-256')
    archive = downloads / FFMPEG_ASSET
    if not archive.is_file() or sha256(archive) != expected:
        temporary = archive.with_suffix('.part')
        try:
            urllib.request.urlretrieve(FFMPEG_BASE + FFMPEG_ASSET, temporary)
            if sha256(temporary) != expected:
                raise RuntimeError('FFmpeg SHA-256 mismatch; downloaded bytes were not installed')
            temporary.replace(archive)
        finally:
            temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            relative = ffmpeg_relative(entry)
            if relative is None:
                continue
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, destination.open('wb') as output:
                shutil.copyfileobj(source, output)
    if not all((target / 'bin' / name).is_file() for name in ('ffmpeg.exe', 'ffprobe.exe')):
        raise RuntimeError('The verified FFmpeg archive did not contain both required binaries')
    (target / 'UPSTREAM-SHA256.txt').write_text(
        expected + '  ' + FFMPEG_ASSET + '\n' + FFMPEG_BASE + '\n', encoding='utf-8')


def copy_runtime(source, destination):
    source, destination = Path(source), Path(destination)
    if (source / 'pyvenv.cfg').exists():
        raise ValueError('Build with a base Windows Python interpreter, never a developer venv')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(
        '__pycache__', '*.pyc', '*.pdb', 'pip-cache'))
    visual_studio = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Microsoft Visual Studio'
    candidates = [path for path in visual_studio.glob(
        '*/*/VC/Redist/MSVC/*/x64/Microsoft.VC143.CRT/msvcp140.dll')
        if 'onecore' not in str(path).lower()]
    if not candidates:
        raise RuntimeError('App-local MSVC CRT is unavailable; an incomplete runtime is not distributable')
    for library in sorted(candidates)[-1].parent.glob('*.dll'):
        shutil.copy2(library, destination / library.name)


def checked_run(command, *, timeout=1800, environment=None, cwd=None):
    subprocess.run([str(argument) for argument in command], check=True, timeout=timeout,
                   env=environment, cwd=cwd)


def build_environment(root, reports):
    environment = dict(os.environ)
    for name in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'HMOOB_DATA_DIR', 'HMOOB_MODEL_DIR'):
        environment.pop(name, None)
    environment.update({
        'PATH': str(root / 'ffmpeg' / 'bin') + os.pathsep + environment.get('PATH', ''),
        'PYTHONNOUSERSITE': '1', 'PYTHONUTF8': '1', 'PYTHONUNBUFFERED': '1',
        'HMOOB_DATA_DIR': str(reports / 'smoke-data'),
        'HMOOB_MODEL_DIR': str(root / 'hmoob-voicelab' / '.data' / 'models'),
        'MPLCONFIGDIR': str(reports / 'cache' / 'matplotlib'),
        'NUMBA_CACHE_DIR': str(reports / 'cache' / 'numba'),
        'XDG_CACHE_HOME': str(reports / 'cache' / 'xdg'),
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
    })
    return environment


def write_launcher(root):
    content = ('@echo off\r\nsetlocal\r\nset "PYTHONHOME="\r\nset "PYTHONPATH="\r\n'
               'set "PYTHONNOUSERSITE=1"\r\nset "PYTHONUTF8=1"\r\ncd /d "%~dp0"\r\n'
               '"%~dp0runtime\\python.exe" "%~dp0hmoob-voicelab\\bootstrap.py" %*\r\n'
               'if errorlevel 1 (\r\n'
               '  echo Khong mo duoc tool. Xem thong bao phia tren.\r\n'
               '  pause\r\n  exit /b 1\r\n)\r\nexit /b 0\r\n')
    (root / 'MO_HMOOB_VOICELAB.bat').write_bytes(content.encode('ascii'))


def write_notices(root, model_manifest):
    shutil.copy2(SOURCE / 'BAT-DAU.txt', root / 'BAT-DAU.txt')
    (root / 'THIRD-PARTY-NOTICES.txt').write_text(
        'Python: runtime/LICENSE.txt and https://www.python.org/\n'
        'Python packages: runtime/Lib/site-packages/*.dist-info/licenses and METADATA.\n'
        'FFmpeg GPL build: bundled ffmpeg/LICENSE*, documentation, '
        'https://github.com/BtbN/FFmpeg-Builds and corresponding upstream source.\n'
        'MSVC app-local CRT: https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files\n'
        'F5-TTS code: https://github.com/SWivid/F5-TTS (MIT); Hmong integration: '
        'https://github.com/YangNobody12/F5-TTS-Hmong.\n'
        'Model weights are NOT included. First start downloads directly from the model publishers '
        'using setup_voice.py with integrity verification. Review the publishers model terms '
        'for your use; a code license does not establish a weight license.\n'
        'Only the two approved built-in reference recordings are included. No other recordings, '
        'developer history, environments or credentials are copied.\n', encoding='utf-8')
    (root / 'MODEL-SOURCES.json').write_text(json.dumps(model_manifest, indent=2) + '\n', encoding='utf-8')


def archive_package(root, archive):
    root, archive = Path(root), Path(archive)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as bundle:
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise ValueError('Portable tree contains a symlink: ' + str(path))
            if path.is_file():
                bundle.write(path, root.name + '/' + path.relative_to(root).as_posix())
    checksum = sha256(archive)
    Path(str(archive) + '.sha256').write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
    return checksum


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reports', required=True, type=Path)
    args = parser.parse_args(argv)
    if os.name != 'nt' or sys.maxsize <= 2 ** 32 or sys.version_info[:2] != (3, 12):
        raise RuntimeError('Build with native Windows x64 base Python 3.12')
    root, reports = args.output.resolve(), args.reports.resolve()
    if root.exists():
        raise ValueError('Build output must be a new directory; existing files are preserved')
    root.mkdir(parents=True)
    reports.mkdir(parents=True, exist_ok=True)
    copy_source(root / 'hmoob-voicelab')
    download_verified_ffmpeg(root / 'ffmpeg', root.parent / 'downloads')
    copy_runtime(Path(sys.base_prefix), root / 'runtime')
    write_launcher(root)
    app = root / 'hmoob-voicelab'
    environment = build_environment(root, reports)
    checked_run([root / 'runtime' / 'python.exe', app / 'setup_voice.py'],
                environment=environment, cwd=app)
    models = app / '.data' / 'models'
    model_manifest = json.loads((models / 'verified-models.json').read_text(encoding='utf-8'))
    write_notices(root, model_manifest)
    freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (root / 'BUILD-DEPENDENCIES.txt').write_text(freeze, encoding='utf-8')

    # Move the whole directory, rather than copying it, to prove imports and
    # executable lookup survive relocation without leaving an original runtime.
    relocated = root.parent / 'Relocated test with spaces' / root.name
    relocated.parent.mkdir(parents=True, exist_ok=True)
    if relocated.exists():
        raise ValueError('Relocation destination already exists')
    root.rename(relocated)
    try:
        checked_run([relocated / 'runtime' / 'python.exe', SOURCE / 'packaging' / 'smoke_portable.py',
                     relocated, reports], environment=build_environment(relocated, reports),
                    cwd=relocated / 'hmoob-voicelab', timeout=1800)
    finally:
        relocated.rename(root)

    # This directory was created by this build, never copied from developer
    # data. Its weights are used for validation only, not redistributed.
    shutil.rmtree(models)
    if list((app / '.data').iterdir()):
        raise RuntimeError('Unexpected application data in the distribution')
    (app / '.data').rmdir()
    checked_run([root / 'runtime' / 'python.exe', SOURCE / 'packaging' / 'check_first_run.py', root],
                environment=build_environment(root, reports), cwd=app, timeout=180)
    build = {'commit': os.environ.get('GITHUB_SHA'), 'python': sys.version,
             'platform': 'windows-x64', 'models_included': False,
             'first_run_model_download_required': True,
             'validated_offline_voices': ['female', 'male'], 'relocated_runtime_tested': True}
    (root / 'BUILD.json').write_text(json.dumps(build, indent=2) + '\n', encoding='utf-8')
    archive = root.parent / 'Hmoob-VoiceLab-Windows-x64.zip'
    checksum = archive_package(root, archive)
    (reports / 'build.json').write_text(json.dumps({**build, 'archive': str(archive),
        'archive_bytes': archive.stat().st_size, 'archive_sha256': checksum}, indent=2) + '\n', encoding='utf-8')
    print('BUILT: ' + str(archive), flush=True)


if __name__ == '__main__':
    main()
