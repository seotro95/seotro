"""Assemble a Windows CPU candidate on another OS, without claiming Windows QA.

Use the PSF's official Python NuGet runtime, PyPI Windows wheels, checksum-verified
FFmpeg and a model directory already exercised by the operator. The resulting
BUILD.json intentionally records native_windows_validation=false. Native Windows
smoke_portable.py is still required before treating it as a verified release.
"""
import argparse
import base64
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import urllib.request
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
PYTHON_VERSION = '3.12.10'
PYTHON_URL = f'https://api.nuget.org/v3-flatcontainer/python/{PYTHON_VERSION}/python.{PYTHON_VERSION}.nupkg'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_parts(name):
    # ZIP names always use forward slashes; reject Windows path escape syntax too.
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    return path.parts


def download_python(downloads):
    archive = downloads / f'python.{PYTHON_VERSION}.nupkg'
    with urllib.request.urlopen(urllib.request.Request(PYTHON_URL, method='HEAD'), timeout=60) as response:
        expected = response.headers.get('x-ms-meta-sha512')
    if not expected:
        raise RuntimeError('Official NuGet feed did not supply the Python package SHA512.')
    def digest(path):
        with path.open('rb') as stream:
            return base64.b64encode(hashlib.file_digest(stream, 'sha512').digest()).decode()
    if not archive.exists() or digest(archive) != expected:
        temporary = archive.with_suffix('.part')
        urllib.request.urlretrieve(PYTHON_URL, temporary)
        if digest(temporary) != expected:
            temporary.unlink(missing_ok=True)
            raise RuntimeError('PSF Python package SHA512 mismatch.')
        temporary.replace(archive)
    return archive, {'url': PYTHON_URL, 'sha512_base64': expected, 'sha256': sha256(archive)}


def extract_python(archive, runtime):
    runtime.mkdir(parents=True)
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            parts = safe_parts(entry.filename)
            if len(parts) < 2 or parts[0] != 'tools' or entry.is_dir():
                continue
            destination = runtime.joinpath(*parts[1:])
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, destination.open('wb') as target:
                shutil.copyfileobj(source, target)
    if not (runtime / 'python.exe').is_file() or not (runtime / 'LICENSE.txt').is_file():
        raise RuntimeError('PSF runtime is incomplete.')


def verify_wheel(path):
    """Check PyPI's artifact SHA256 and the wheel's per-file RECORD digests."""
    with zipfile.ZipFile(path) as wheel:
        metadata_path = next(n for n in wheel.namelist() if n.endswith('.dist-info/METADATA'))
        from email.parser import Parser
        metadata = Parser().parsestr(wheel.read(metadata_path).decode())
        url = f'https://pypi.org/pypi/{metadata["Name"]}/{metadata["Version"]}/json'
        with urllib.request.urlopen(url, timeout=60) as response:
            release = json.load(response)
        artifact = next((a for a in release['urls'] if a['filename'] == path.name), None)
        if artifact is None or sha256(path) != artifact['digests']['sha256']:
            raise RuntimeError(f'PyPI artifact checksum mismatch: {path.name}')
        record = next(n for n in wheel.namelist() if n.endswith('.dist-info/RECORD'))
        for name, encoded_hash, size in csv.reader(io.StringIO(wheel.read(record).decode())):
            safe_parts(name)
            if not encoded_hash:
                continue  # RECORD and optional signature files are unhashed by specification.
            algorithm, expected = encoded_hash.split('=', 1)
            if algorithm not in {'sha256', 'sha384', 'sha512'}:
                raise ValueError('Unsupported wheel RECORD hash algorithm')
            data = wheel.read(name)
            actual = base64.urlsafe_b64encode(hashlib.new(algorithm, data).digest()).rstrip(b'=').decode()
            if actual != expected or (size and len(data) != int(size)):
                raise RuntimeError(f'Wheel file checksum mismatch: {path.name}: {name}')
    return {'filename': path.name, 'sha256': artifact['digests']['sha256'], 'source': artifact['url']}


def missing_windows_requirements(wheels):
    # pip --platform selects wheel tags but does not fully replace the host's
    # environment markers. Check the complete Windows dependency graph explicitly.
    from email.parser import Parser
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    environment = default_environment()
    environment.update(sys_platform='win32', platform_system='Windows',
                       platform_machine='AMD64', os_name='nt', python_version='3.12',
                       python_full_version=PYTHON_VERSION, implementation_name='cpython', extra='')
    installed, metadata = {}, []
    for path in wheels:
        with zipfile.ZipFile(path) as wheel:
            name = next(n for n in wheel.namelist() if n.endswith('.dist-info/METADATA'))
            item = Parser().parsestr(wheel.read(name).decode())
        installed[canonicalize_name(item['Name'])] = item['Version']
        metadata.append(item)
    missing = set()
    for item in metadata:
        for text in item.get_all('Requires-Dist', []):
            requirement = Requirement(text)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            version = installed.get(canonicalize_name(requirement.name))
            if version is None:
                extra = '[' + ','.join(sorted(requirement.extras)) + ']' if requirement.extras else ''
                missing.add(requirement.name + extra + str(requirement.specifier))
            elif version not in requirement.specifier:
                raise RuntimeError(f'Windows dependency conflict: {item["Name"]}: {text}, have {version}')
    return sorted(missing)


def install_wheel(path, runtime):
    """Install wheel library/data trees without executing a foreign interpreter."""
    site = runtime / 'Lib' / 'site-packages'
    site.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as wheel:
        for entry in wheel.infolist():
            # Intel ships its separate debug CRT build as optional wheel data;
            # the release app never loads it and Windows debug CRT is not redistributable.
            if entry.filename.endswith('/tcm_debug.dll'):
                continue
            parts = safe_parts(entry.filename)
            if not parts or entry.is_dir():
                continue
            if parts[0].endswith('.data'):
                if len(parts) < 3:
                    continue
                scheme, parts = parts[1], parts[2:]
                if scheme in {'purelib', 'platlib'}:
                    base = site
                elif scheme == 'data':
                    base = runtime
                elif scheme == 'scripts':
                    base = runtime / 'Scripts'
                elif scheme == 'headers':
                    base = runtime / 'Include'
                else:
                    raise ValueError(f'Unsupported wheel data scheme: {scheme}')
            else:
                base = site
            destination = base.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with wheel.open(entry) as source, destination.open('wb') as target:
                shutil.copyfileobj(source, target)


def copy_models(models, destination):
    """Copy only verified model storage, never personal voices/jobs/cache tokens."""
    for engine in ('vieneu_nano', 'vieneu'):
        marker = models / f'{engine}.ready'
        if not marker.is_file():
            raise ValueError(f'Model preparation has not completed: {marker.name}')
    destination.mkdir(parents=True)
    for repo in (models / 'cache' / 'hub').glob('models--*'):
        target = destination / 'cache' / 'hub' / repo.name
        for name in ('snapshots', 'refs'):
            if (repo / name).exists():
                # dereference links: Windows ZIP extraction need not restore Unix symlinks.
                shutil.copytree(repo / name, target / name, symlinks=False)
    for name in ('vieneu_nano.ready', 'vieneu.ready', 'vieneu_fast.ready'):
        if (models / name).is_file():
            shutil.copy2(models / name, destination / name)
    if (models / 'whisper-base').is_dir():
        shutil.copytree(models / 'whisper-base', destination / 'whisper-base', symlinks=False)
    return [{'path': str(p.relative_to(destination)).replace(os.sep, '/'), 'sha256': sha256(p), 'size': p.stat().st_size}
            for p in sorted(destination.rglob('*')) if p.is_file()]


def scan_pe_imports(root):
    """Static named-import closure; this does not replace native loader testing."""
    if not shutil.which('objdump'):
        return {'native_windows_execution': False, 'pe_import_scan': 'not run: objdump unavailable'}
    files = [p for p in root.rglob('*') if p.suffix.lower() in {'.dll', '.pyd', '.exe'}]
    available = {p.name.lower() for p in files}
    # Desktop Windows 10/11 provides these system components. API/ext-ms DLL
    # contracts are resolved by the OS, not bundled from another machine.
    system = set('avrt.dll cfgmgr32.dll d2d1.dll dnsapi.dll dwrite.dll msimg32.dll ncrypt.dll secur32.dll usp10.dll advapi32.dll avicap32.dll bcrypt.dll bcryptprimitives.dll cabinet.dll combase.dll crypt32.dll d3d11.dll d3dcompiler_47.dll dbghelp.dll dxgi.dll gdi32.dll imagehlp.dll iphlpapi.dll kernel32.dll msi.dll msvcrt.dll netapi32.dll ntdll.dll ole32.dll oleaut32.dll pdh.dll powrprof.dll propsys.dll psapi.dll rpcrt4.dll setupapi.dll shell32.dll shlwapi.dll user32.dll userenv.dll version.dll winmm.dll wintrust.dll ws2_32.dll'.split())
    missing = {}
    for path in files:
        result = subprocess.run(['objdump', '-p', str(path)], capture_output=True, text=True, check=False)
        for name in re.findall(r'DLL Name:\s*(\S+)', result.stdout):
            name = name.lower()
            if name not in available and name not in system and not name.startswith(('api-ms-', 'ext-ms-')):
                missing.setdefault(name, []).append(str(path.relative_to(root)).replace(os.sep, '/'))
    if missing:
        raise RuntimeError('Unresolved non-system Windows DLL imports: ' + json.dumps(missing))
    return {'native_windows_execution': False, 'pe_files_scanned': len(files),
            'unresolved_non_windows_system_imports': missing,
            'omitted_optional_release_incompatible_files': ['tcmlib:tcm_debug.dll'],
            'target_os': 'Windows 10/11 desktop x64'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--downloads', type=Path, required=True)
    parser.add_argument('--skip-wheel-download', action='store_true')
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists():
        raise ValueError('Output must be a new directory; previous builds are preserved.')
    args.downloads.mkdir(parents=True, exist_ok=True)
    wheels = args.downloads / 'wheels'
    wheels.mkdir(exist_ok=True)
    if not args.skip_wheel_download:
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--platform', 'win_amd64', '--python-version', '312', '--implementation', 'cp', '--abi', 'cp312', '--only-binary=:all:', '--dest', str(wheels), '-r', str(SOURCE / 'requirements.txt'), 'msvc-runtime==14.44.35112', 'tbb==2023.2.0'], check=True)
    wheel_paths = sorted(wheels.glob('*.whl'))
    for _ in range(8):
        missing = missing_windows_requirements(wheel_paths)
        if not missing:
            break
        if args.skip_wheel_download:
            raise RuntimeError('Missing Windows-specific dependencies: ' + ', '.join(missing))
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--platform', 'win_amd64', '--python-version', '312', '--implementation', 'cp', '--abi', 'cp312', '--only-binary=:all:', '--dest', str(wheels), *missing], check=True)
        wheel_paths = sorted(wheels.glob('*.whl'))
    else:
        raise RuntimeError('Windows dependency graph did not converge.')
    if not wheel_paths:
        raise RuntimeError('No Windows dependency wheels found.')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(verify_wheel, wheel_paths))
    print(f'Checked PyPI SHA256 and RECORD digests for {len(records)} wheels.', flush=True)
    archive, python_provenance = download_python(args.downloads)
    root.mkdir(parents=True)
    extract_python(archive, root / 'runtime')
    for wheel in wheel_paths:
        install_wheel(wheel, root / 'runtime')
    # msvc-runtime's wheel data tree installs the unmodified Microsoft CRT and
    # its redistribution notice app-locally. Keep vcruntime paired with that CRT,
    # rather than depending on a developer's preinstalled system redistributable.
    runtime = root / 'runtime'
    for name in ('vcruntime140.dll', 'vcruntime140_1.dll'):
        shutil.copy2(runtime / 'Scripts' / name, runtime / name)
    for file in (runtime / 'Library' / 'bin').glob('*.dll'):
        shutil.copy2(file, runtime / file.name)
    crt_names = ('msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
    if not all((runtime / name).is_file() for name in crt_names):
        raise RuntimeError('Verified msvc-runtime wheel did not include required CRT DLLs.')
    from build_windows import copy_source, download_verified_ffmpeg
    copy_source(root / 'voice-studio')
    download_verified_ffmpeg(root / 'ffmpeg', args.downloads)
    model_records = copy_models(args.models, root / 'voice-studio' / '.data' / 'models')
    for name in ('MO_VOICE_STUDIO.bat', 'THEM_GIONG_QUOC_TE.bat'):
        shutil.copy2(SOURCE / 'packaging' / name, root / name)
    shutil.copy2(SOURCE / 'packaging' / 'check_cross_bundle.py', root / 'voice-studio' / 'check_bundle.py')
    # The native release smoke script clears QA data at completion; do not expose
    # it as a user-facing check on the user's personal data directory.
    (root / 'KIEM_TRA_TOOL.bat').write_text('@echo off\nsetlocal\ncd /d "%~dp0"\nset "PATH=%~dp0runtime;%~dp0ffmpeg\\bin;%PATH%"\nset "PYTHONHOME="\nset "PYTHONPATH="\nset "PYTHONNOUSERSITE=1"\nset "PYTHONUTF8=1"\n"runtime\\python.exe" "voice-studio\\check_bundle.py"\npause\n', encoding='utf-8')
    (root / 'PE-DEPENDENCIES.json').write_text(json.dumps(scan_pe_imports(root), indent=2), encoding='utf-8')
    manifest = {
        'kind': 'cross-assembled Windows x64 CPU candidate',
        'native_windows_validation': False,
        'python_version': PYTHON_VERSION,
        'python_provenance': python_provenance,
        'wheels': records,
        'msvc_provenance': {'source_wheel': next(p.name for p in wheel_paths if p.name.startswith('msvc_runtime-')), 'dll_sha256': {name: sha256(runtime / name) for name in crt_names}},
        'models': model_records,
        'instructions': 'Extract all files, run MO_VOICE_STUDIO.bat. Native Windows execution remains unverified. No API key or model downloads are needed for bundled Vietnamese CPU voices.',
    }
    (root / 'BUILD.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'READ-ME-FIRST.txt').write_text('''VOICE STUDIO — WINDOWS X64 CPU

Giai nen TOAN BO ZIP vao thu muc co quyen ghi, sau do mo MO_VOICE_STUDIO.bat.
Da kem Python 3.12, FFmpeg, Nano/Turbo va Whisper neu model da chuan bi.
Khong can API key hay tai model cho cac giong Viet di kem.
Du lieu ca nhan luu trong voice-studio/.data. Sao luu thu muc nay khi cap nhat.
THEM_GIONG_QUOC_TE.bat la tuy chon can Internet va dung luong bo sung.

Goi nay duoc lap rap tren Linux tu runtime/wheels Windows va model da chay
kiem tra tren Linux. CHUA CHAY KIEM THU TREN WINDOWS THAT. BUILD.json ghi ro
nguon, checksum va trang thai native_windows_validation=false.
Khong bao dam muc tieu 1 gio voice trong 2 phut; toc do tuy CPU va model.
Chay KIEM_TRA_TOOL.bat de tu kiem tra inference offline tren may Windows,
khong xoa giọng/lich su ca nhan.

LICENSE / NGUON:
Python: runtime/LICENSE.txt, official PSF NuGet distribution.
Python dependencies and Microsoft runtime DLL: runtime/Lib/site-packages/*.dist-info/licenses.
FFmpeg GPL: ffmpeg/LICENSE*, ffmpeg/doc and ffmpeg/UPSTREAM-SHA256.txt.
Model cards/licenses: voice-studio/.data/models/cache/hub/**/snapshots/**.
''', encoding='utf-8')
    source_manifest = {str(p.relative_to(root)).replace(os.sep, '/'): sha256(p) for p in sorted((root / 'voice-studio').rglob('*')) if p.is_file() and '.data' not in p.relative_to(root).parts}
    (root / 'SOURCE-SHA256.json').write_text(json.dumps(source_manifest, indent=2), encoding='utf-8')
    print(f'Assembled candidate: {root}. Native Windows validation: NOT RUN.', flush=True)
    if args.archive:
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        archive_path = shutil.make_archive(str(args.archive.with_suffix('')), 'zip', root.parent, root.name)
        Path(archive_path + '.sha256').write_text(sha256(archive_path) + '  ' + Path(archive_path).name + '\n')
        with zipfile.ZipFile(archive_path) as bundle:
            bad = bundle.testzip()
        if bad:
            raise RuntimeError(f'ZIP integrity failure: {bad}')
        print(f'ZIP verified: {archive_path}', flush=True)


if __name__ == '__main__':
    main()
