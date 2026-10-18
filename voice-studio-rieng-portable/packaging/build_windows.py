"""Build the standalone 1.3 Windows bundle; publish only after native validation.

A checksum-pinned, previously tested portable release can supply the runtime and
models. Only its runtime, FFmpeg and model storage are reused; application source,
recordings, keys and project history are never copied from another installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import urllib.request
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
BASE_SHA256 = '5998b2f9e5198cf8ef4ab82a4796539bed0754f2b5eeaeb4da72d4fec27d1501'
FFMPEG_BASE = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
FFMPEG_ASSET = 'ffmpeg-n8.1-latest-win64-gpl-8.1.zip'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_zip_path(entry):
    path = PurePosixPath(entry.filename)
    if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename:
        raise ValueError('Unsafe archive path: '+entry.filename)
    if (entry.external_attr >> 16) & 0o170000 == 0o120000:
        raise ValueError('Archive symlinks are not accepted: '+entry.filename)
    return path.parts


def extract_member(bundle, entry, target):
    if entry.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    if target.exists():
        raise ValueError('Refusing to overwrite archive destination: '+str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    with bundle.open(entry) as source, target.open('wb') as output:
        shutil.copyfileobj(source, output)


def extract_verified_base(archive, root, expected=BASE_SHA256):
    if len(expected) != 64 or any(char not in '0123456789abcdef' for char in expected.lower()):
        raise ValueError('A complete upstream base SHA256 is required')
    actual = sha256(archive)
    if actual != expected.lower():
        raise ValueError('Base archive SHA256 mismatch; no contents have been used')
    with zipfile.ZipFile(archive) as bundle:
        candidates = [safe_zip_path(item)[:-2] for item in bundle.infolist()
                      if item.filename.endswith('/runtime/python.exe')]
        if len(candidates) != 1:
            raise ValueError('Expected one runtime/python.exe in the verified base')
        prefix = candidates[0]
        for entry in bundle.infolist():
            parts = safe_zip_path(entry)
            if parts[:len(prefix)] != prefix:
                continue
            relative = parts[len(prefix):]
            destination = None
            if relative and relative[0] in {'runtime', 'ffmpeg'}:
                destination = root.joinpath(*relative)
            elif relative[:3] == ('voice-studio', '.data', 'models'):
                model = relative[3:]
                # Exclude Whisper/video models and prior calibration recordings.
                repos = {'models--pnnbao-ump--VieNeu-TTS-v3-Nano', 'models--pnnbao-ump--VieNeu-TTS-v3-Turbo',
                         'models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX'}
                if model and ((len(model) >= 3 and model[:2] == ('cache', 'hub') and model[2] in repos)
                              or (len(model) == 1 and model[0] in {'vieneu_nano.ready', 'vieneu.ready'})):
                    destination = (root/'app/.data/models').joinpath(*model)
            elif len(relative) == 1 and relative[0] in {'MODEL-APACHE-2.0-LICENSE.txt', 'BUILD-DEPENDENCIES.txt'}:
                destination = root/('BASE-'+relative[0])
            if destination is not None:
                extract_member(bundle, entry, destination)
    if not (root/'runtime/python.exe').is_file() or not (root/'app/.data/models/vieneu_nano.ready').is_file():
        raise ValueError('Verified base does not contain prepared Nano and Windows Python')
    if not (root/'ffmpeg/UPSTREAM-SHA256.txt').is_file():
        raise ValueError('Verified base is missing the FFmpeg upstream checksum record')
    (root/'BASE-ARCHIVE-SHA256.txt').write_text(actual+'  '+Path(archive).name+'\n', encoding='utf-8')


def download_verified_ffmpeg(target, downloads):
    downloads.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(FFMPEG_BASE+'checksums.sha256', timeout=60) as response:
        manifest = response.read(1024*1024).decode('utf-8')
    sys.path.insert(0, str(SOURCE))
    from bootstrap import checksum_for_asset
    expected = checksum_for_asset(manifest, FFMPEG_ASSET)
    archive = downloads/FFMPEG_ASSET
    if not archive.exists() or sha256(archive) != expected:
        with urllib.request.urlopen(FFMPEG_BASE+FFMPEG_ASSET, timeout=60) as source, archive.open('wb') as output:
            shutil.copyfileobj(source, output)
    if sha256(archive) != expected:
        raise RuntimeError('FFmpeg SHA256 mismatch; stop without using this archive')
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            parts = safe_zip_path(entry)[1:]
            if not parts or parts[-1].lower() == 'ffplay.exe':
                continue
            extract_member(bundle, entry, target.joinpath(*parts))
    (target/'UPSTREAM-SHA256.txt').write_text(expected+'  '+FFMPEG_ASSET+'\n'+FFMPEG_BASE, encoding='utf-8')


def runtime_environment(root, *, offline):
    env = dict(os.environ)
    for name in ('PYTHONHOME', 'PYTHONPATH', 'TRANSFORMERS_CACHE'):
        env.pop(name, None)
    data = root/'app/.data'
    env.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', VOICE_STUDIO_DATA_DIR=str(data),
               HF_HOME=str(data/'models/cache'), HF_HUB_CACHE=str(data/'models/cache/hub'),
               HUGGINGFACE_HUB_CACHE=str(data/'models/cache/hub'), HF_HUB_DISABLE_XET='1',
               HF_HUB_DISABLE_TELEMETRY='1', GRADIO_ANALYTICS_ENABLED='False', DO_NOT_TRACK='1',
               HF_HUB_OFFLINE='1' if offline else '0', TRANSFORMERS_OFFLINE='1' if offline else '0')
    env['PATH'] = str(root/'ffmpeg/bin')+os.pathsep+str(root/'runtime')+os.pathsep+env.get('PATH', '')
    return env


def copy_source(root):
    app = root/'app'
    app.mkdir(parents=True, exist_ok=True)
    for file in (SOURCE/'app').iterdir():
        if file.is_file() and file.suffix in {'.py', '.ps1'}:
            shutil.copy2(file, app/file.name)
    shutil.copytree(SOURCE/'app/static', app/'static')
    for name in ('HUONG_DAN_CAN_MOC.txt', 'requirements-runtime.txt'):
        shutil.copy2(SOURCE/name, root/name)
    guide=root/'HUONG_DAN_CAN_MOC.txt'
    guide.write_text(guide.read_text(encoding='utf-8').replace('Chạy CAI_DAT.bat rồi MO_TOOL.bat theo DOC_TRUOC.md.', 'Bản Portable: mở MO_TOOL.bat; không cần cài Python hay tải model.'), encoding='utf-8')
    shutil.copy2(SOURCE/'packaging/MO_TOOL.bat', root/'MO_TOOL.bat')


def copy_runtime(destination):
    source = Path(sys.base_prefix)
    if Path(sys.prefix).resolve() != source.resolve() or (source/'pyvenv.cfg').exists():
        raise ValueError('Fresh builds require base Windows Python, not a virtualenv')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pdb', 'pip-cache'))
    vs_root = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'Microsoft Visual Studio'
    candidates = [p for p in vs_root.glob('*/*/VC/Redist/MSVC/*/x64/Microsoft.VC143.CRT/msvcp140.dll')
                  if 'onecore' not in str(p).lower()]
    if not candidates:
        raise RuntimeError('App-local MSVC CRT was not found; do not distribute an incomplete runtime')
    for file in sorted(candidates)[-1].parent.glob('*.dll'):
        shutil.copy2(file, destination/file.name)


def materialize_models(hub):
    for repo in hub.glob('models--*'):
        for link in (repo/'snapshots').rglob('*'):
            if link.is_symlink():
                if not link.is_file():
                    raise ValueError('Unexpected directory symlink in model cache')
                temporary = link.with_name(link.name+'.portable')
                shutil.copyfile(link.resolve(strict=True), temporary)
                link.unlink()
                temporary.replace(link)
        shutil.rmtree(repo/'blobs', ignore_errors=True)


def prepare_models(root, include_turbo):
    env = runtime_environment(root, offline=False)
    engines = ['vieneu_nano']+(['vieneu'] if include_turbo else [])
    for engine in engines:
        subprocess.run([sys.executable, str(root/'app/prepare_models.py'), engine], env=env, cwd=root/'app', check=True, timeout=2400)
    # Model cards are redistributed alongside weights, with explicit license text.
    from huggingface_hub import hf_hub_download
    repos = ['pnnbao-ump/VieNeu-TTS-v3-Nano', 'OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX']
    if include_turbo:
        repos.append('pnnbao-ump/VieNeu-TTS-v3-Turbo')
    for repo in repos:
        hf_hub_download(repo, 'README.md', cache_dir=str(root/'app/.data/models/cache/hub'))
    materialize_models(root/'app/.data/models/cache/hub')
    from importlib.metadata import distribution
    dist = distribution('vieneu')
    license_file = next(file for file in dist.files if str(file).endswith('dist-info/licenses/LICENSE'))
    shutil.copy2(dist.locate_file(license_file), root/'MODEL-APACHE-2.0-LICENSE.txt')


def clean_data(root):
    data = root/'app/.data'
    data.mkdir(parents=True, exist_ok=True)
    for file in data.iterdir():
        if file.name == 'models':
            continue
        if file.is_dir():
            shutil.rmtree(file)
        else:
            file.unlink()
    for file in (data/'models').glob('*.wav'):
        file.unlink()  # model-preparation calibration speech, never user recordings
    for folder in ('audio', 'parts', 'jobs', 'voices'):
        (data/folder).mkdir(exist_ok=True)


def verify_relocated(root):
    # Move the complete bundle. No original Python prefix or build paths may be
    # required, including when Windows paths contain spaces and Vietnamese text.
    relocated = root.with_name(root.name+' - Kiem tra co dau é')
    if relocated.exists():
        raise ValueError('Relocation test destination already exists')
    root.rename(relocated)
    try:
        subprocess.run([str(relocated/'runtime/python.exe'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                        str(SOURCE/'app/tests'), str(SOURCE/'tests'), str(SOURCE/'packaging/test_build_windows.py')],
                       env=runtime_environment(relocated, offline=True), cwd=SOURCE, check=True, timeout=600)
        subprocess.run([str(relocated/'runtime/python.exe'), '-s', '-X', 'utf8',
                        str(SOURCE/'packaging/smoke_portable.py'), str(relocated)],
                       env=runtime_environment(relocated, offline=True), cwd=relocated, check=True, timeout=1200)
    finally:
        relocated.rename(root)
    clean_data(root)


def write_notices(root):
    (root/'DOC_TRUOC_PORTABLE.txt').write_text('''VOICE STUDIO RIENG 1.3.0 - WINDOWS 10/11 X64 PORTABLE

Giai nen TOAN BO ZIP vao thu muc moi, vi du D:\\VoiceStudio.
Mo MO_TOOL.bat. Khong can cai Python, FFmpeg hay tai lai giong Nano da kem theo.
Giu cua so tool mo trong khi tao voice. Du lieu cua ban nam trong app/.data.
Ban nay giu nguyen moc SRT, tu can nhip tung cau va them khoang lang.
Chon WAV de dung video; cau bi ep qua nhanh van can nghe kiem tra.
TXT khong co moc thoi gian khong the xac dinh thoi luong video.
Qwen quoc te khong duoc dong goi. Giong Windows phu thuoc may dang su dung.
Khong ghi de app/.data khi cap nhat; sao luu du lieu truoc khi thay goi.

THIRD-PARTY NOTICES
Python: runtime/LICENSE.txt; https://www.python.org/psf/license/
Packages: runtime/Lib/site-packages/*.dist-info (metadata and license files).
FFmpeg GPL: ffmpeg/LICENSE*, upstream docs and UPSTREAM-SHA256.txt;
https://github.com/BtbN/FFmpeg-Builds
MSVC app-local runtime: Microsoft Visual Studio redistributable license;
https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files
Vietnamese models: model cards/licenses in app/.data/models/cache/hub and
MODEL-APACHE-2.0-LICENSE.txt or BASE-MODEL-APACHE-2.0-LICENSE.txt.
Source, binary and weight redistribution remain subject to those licenses.
No personal recordings, uploaded subtitles, API keys or history are included.
''', encoding='utf-8')


def check_bundle_hygiene(root):
    forbidden = {'.env', '.netrc', '.git-credentials', 'token', 'stored_tokens', 'pyvenv.cfg', '.agent_harnesses.json'}
    for file in root.rglob('*'):
        if file.is_symlink():
            raise ValueError('Portable ZIP must not contain symlinks: '+str(file))
        relative = file.relative_to(root)
        if file.name in forbidden or any(part in {'.git', '.aws', '.codex', '.agents'} for part in relative.parts):
            raise ValueError('Unexpected credential/developer file in bundle: '+str(relative))
    data = root/'app/.data'
    assert not any(file.is_file() for file in data.rglob('*') if data/'models' not in file.parents), 'QA data or user projects remain'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-archive', type=Path)
    parser.add_argument('--base-sha256', default=BASE_SHA256)
    parser.add_argument('--include-turbo', action='store_true', help='Fresh builds: also download Turbo; verified bases retain bundled Turbo')
    args = parser.parse_args()
    if os.name != 'nt' or sys.maxsize <= 2**32:
        raise RuntimeError('Run this builder and its offline inference checks on native Windows x64')
    root = args.output.resolve()
    if root.exists():
        raise ValueError('Output must be a new directory; previous builds are protected')
    root.mkdir(parents=True)
    if args.base_archive:
        extract_verified_base(args.base_archive, root, args.base_sha256)
    else:
        download_verified_ffmpeg(root/'ffmpeg', root.parent/'downloads')
    copy_source(root)
    if not args.base_archive:
        prepare_models(root, args.include_turbo)
        copy_runtime(root/'runtime')
    if not all((root/'ffmpeg/bin'/name).is_file() for name in ('ffmpeg.exe', 'ffprobe.exe')):
        raise ValueError('Both FFmpeg and FFprobe are required')
    clean_data(root)
    write_notices(root)
    verify_relocated(root)
    check_bundle_hygiene(root)
    metadata = {'product': 'Voice Studio Rieng', 'version': '1.3.0', 'package_type': 'windows-x64-portable',
                'source_commit': os.environ.get('GITHUB_SHA'), 'max_characters': 1000000,
                'bundled_runtime': True, 'bundled_model_weights': True, 'native_windows_offline_smoke': 'passed',
                'verified_base_sha256': args.base_sha256 if args.base_archive else None}
    (root/'BUILD_INFO.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    manifest = [sha256(file)+'  '+file.relative_to(root).as_posix() for file in sorted(root.rglob('*')) if file.is_file()]
    (root/'MANIFEST.sha256').write_text('\n'.join(manifest)+'\n', encoding='utf-8')
    archive = Path(shutil.make_archive(str(root)+'-Windows-x64', 'zip', root.parent, root.name))
    with zipfile.ZipFile(archive) as bundle:
        corrupt = bundle.testzip()
        if corrupt is not None:
            raise ValueError('ZIP CRC validation failed: '+corrupt)
    if archive.stat().st_size >= 2*1024**3:
        raise RuntimeError('ZIP exceeds the GitHub single-release-asset size limit; do not publish')
    Path(str(archive)+'.sha256').write_text(sha256(archive)+'  '+archive.name+'\n', encoding='utf-8')
    print('BUILT AND VERIFIED: '+str(archive), flush=True)


if __name__ == '__main__':
    main()
