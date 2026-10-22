"""Native Windows portable build. Never package a developer's data or keys."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
FFMPEG_BASE = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
FFMPEG_ASSET = 'ffmpeg-n8.1-latest-win64-gpl-8.1.zip'


def download_verified_ffmpeg(target, downloads):
    downloads.mkdir(parents=True, exist_ok=True)
    manifest = urllib.request.urlopen(FFMPEG_BASE+'checksums.sha256', timeout=60).read().decode()
    expected = next(line.split()[0] for line in manifest.splitlines() if line.split()[-1] == FFMPEG_ASSET)
    archive = downloads/FFMPEG_ASSET
    if not archive.exists() or hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest() != expected:
        urllib.request.urlretrieve(FFMPEG_BASE+FFMPEG_ASSET, archive)
    actual = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    if actual != expected:
        raise RuntimeError('FFmpeg SHA256 mismatch. Stop without using the archive.')
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            # Drop upstream root directory, retain binaries, licenses and docs.
            parts = Path(entry.filename).parts[1:]
            if not parts or entry.is_dir() or parts[-1].lower() == 'ffplay.exe':
                continue
            if '..' in parts or Path(*parts).is_absolute():
                raise ValueError('Unsafe FFmpeg archive path')
            destination = target.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, destination.open('wb') as output:
                shutil.copyfileobj(source, output)
    (target/'UPSTREAM-SHA256.txt').write_text(expected+'  '+FFMPEG_ASSET+'\n'+FFMPEG_BASE, encoding='utf-8')


def materialize_model_cache(hub):
    # HF normally links snapshots to blobs. ZIP would duplicate both, and some
    # Windows extractors cannot restore symlinks. Keep real snapshot files only.
    for repo in hub.glob('models--*'):
        snapshots = repo/'snapshots'
        if not snapshots.exists():
            continue
        for link in snapshots.rglob('*'):
            if link.is_symlink():
                if not link.is_file():
                    raise ValueError('Unexpected model-cache directory symlink')
                temporary = link.with_name(link.name+'.portable')
                shutil.copyfile(link.resolve(strict=True), temporary)
                link.unlink()
                temporary.replace(link)
        shutil.rmtree(repo/'blobs', ignore_errors=True)


def copy_runtime(source, destination):
    if (source/'pyvenv.cfg').exists():
        raise ValueError('Build with base Windows Python, not a venv.')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pdb', 'pip-cache'))
    # Include app-local MSVC libraries so no admin redistributable install is needed.
    roots = [Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'Microsoft Visual Studio']
    candidates = [p for root in roots if root.exists() for p in root.glob('*/*/VC/Redist/MSVC/*/x64/Microsoft.VC143.CRT/msvcp140.dll') if 'onecore' not in str(p).lower()]
    if not candidates:
        raise RuntimeError('Cannot locate redistributable MSVC CRT; do not publish an incomplete runtime.')
    for file in sorted(candidates)[-1].parent.glob('*.dll'):
        shutil.copy2(file, destination/file.name)


def copy_source(destination):
    destination.mkdir(parents=True)
    for entry in SOURCE.iterdir():
        if entry.is_file() and entry.suffix in ('.py', '.ps1', '.txt', '.md', '.bat'):
            shutil.copy2(entry, destination/entry.name)
    shutil.copytree(SOURCE/'static', destination/'static')


def verify_offline(root):
    runtime = root/'runtime/python.exe'
    app = root/'voice-studio'
    env = dict(os.environ, PATH=str(root/'ffmpeg/bin')+os.pathsep+os.environ['PATH'], PYTHONNOUSERSITE='1', PYTHONUTF8='1', VOICE_STUDIO_DATA_DIR=str(app/'.data'), HF_HOME=str(app/'.data/models/cache'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', VOICE_STUDIO_PORTABLE='1')
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    subprocess.run([str(runtime), str(SOURCE/'packaging/smoke_portable.py'), str(app)], check=True, env=env, cwd=app, timeout=600)


def run_preparation(command, **kwargs):
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',**kwargs)
    print(result.stdout,flush=True)
    if result.returncode:
        raise RuntimeError(f'Model preparation exited {result.returncode}: '+result.stdout[-3500:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if os.name != 'nt' or sys.maxsize <= 2**32:
        raise RuntimeError('Build on native 64-bit Windows.')
    root = args.output.resolve()
    if root.exists():
        raise ValueError('Output must be a new directory to protect previous builds.')
    root.mkdir(parents=True)
    copy_source(root/'voice-studio')
    download_verified_ffmpeg(root/'ffmpeg', root.parent/'downloads')
    os.environ['PATH'] = str(root/'ffmpeg/bin')+os.pathsep+os.environ['PATH']
    data = root/'voice-studio/.data'
    env = dict(os.environ, VOICE_STUDIO_DATA_DIR=str(data), HF_HOME=str(data/'models/cache'), HF_HUB_DISABLE_XET='1')
    for engine in ('vieneu_nano_clone', 'vieneu'):
        run_preparation([sys.executable, str(SOURCE/'prepare_models.py'), engine], env=env, timeout=1800)
    run_preparation([sys.executable,str(SOURCE/'prepare_subtitles.py')],env=env,timeout=1800)
    # Retain model cards/licenses alongside redistributed weights.
    from huggingface_hub import hf_hub_download
    for repo in ('pnnbao-ump/VieNeu-TTS-v3-Nano', 'pnnbao-ump/VieNeu-TTS-v3-Turbo', 'OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX'):
        hf_hub_download(repo, 'README.md', cache_dir=str(data/'models/cache/hub'))
    materialize_model_cache(data/'models/cache/hub')
    # New build directory contains only calibration clips and downloaded models.
    # Copying the installed base interpreter keeps site-packages relocatable.
    copy_runtime(Path(sys.base_prefix), root/'runtime')
    for name in ('MO_VOICE_STUDIO.bat', 'THEM_GIONG_QUOC_TE.bat'):
        shutil.copy2(SOURCE/'packaging'/name, root/name)
    notices = '''Voice Studio Windows x64 Portable\n\nExtract ALL files to a writable folder, then double-click MO_VOICE_STUDIO.bat.\nNo Python, FFmpeg, venv installation, model download or API key is needed for bundled Vietnamese voices.\nNano, Turbo and Whisper base subtitle recognition are included. International Qwen models are optional: THEM_GIONG_QUOC_TE.bat needs Internet and several GB.\nYour projects are saved in voice-studio/.data. Back up that folder before deleting this portable folder.\nOllama writing/translation is optional and requires a separate Ollama installation/model.\n\nTHIRD-PARTY NOTICES\nPython: runtime/LICENSE.txt; https://www.python.org/\nPython packages: licenses in runtime/Lib/site-packages/*.dist-info\nFFmpeg GPL build: ffmpeg/LICENSE*, docs and https://github.com/BtbN/FFmpeg-Builds\nMSVC app-local redistributable: https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files\nModels: license/model cards in voice-studio/.data/models/cache/hub.\nNo personal recordings, keys, history or developer environment files are packaged.\n'''
    (root/'READ-ME-FIRST.txt').write_text(notices, encoding='utf-8')
    from importlib.metadata import distribution
    license_path = next(f for f in distribution('vieneu').files if str(f).endswith('dist-info/licenses/LICENSE'))
    shutil.copy2(distribution('vieneu').locate_file(license_path), root/'MODEL-APACHE-2.0-LICENSE.txt')
    freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (root/'BUILD-DEPENDENCIES.txt').write_text(freeze, encoding='utf-8')
    (root/'BUILD.json').write_text(json.dumps({'commit': os.environ.get('GITHUB_SHA'), 'python': sys.version, 'engines': ['vieneu_nano','vieneu_nano_clone','vieneu'], 'windows_x64': True}, indent=2), encoding='utf-8')
    try:
        verify_offline(root)
    except Exception as exc:
        print('::error title=Portable offline validation failed::'+str(exc).replace('%','%25').replace('\n','%0A'), flush=True)
        raise
    archive = shutil.make_archive(str(root.parent/'Voice-Studio-Windows-x64'), 'zip', root.parent, root.name)
    size = Path(archive).stat().st_size
    if size >= 2*1024**3:
        raise RuntimeError('Archive exceeds the GitHub single-asset limit; do not publish.')
    checksum = hashlib.file_digest(open(archive, 'rb'), 'sha256').hexdigest()
    Path(str(archive)+'.sha256').write_text(checksum+'  '+Path(archive).name+'\n')
    print(f'BUILT AND VERIFIED: {archive} ({size/1024**2:.0f} MiB)', flush=True)


if __name__ == '__main__':
    try:main()
    except Exception as exc:
        message=(type(exc).__name__+': '+str(exc)).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print('::error title=Windows portable build failed::'+message,flush=True)
        raise
