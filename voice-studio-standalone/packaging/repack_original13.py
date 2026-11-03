"""Patch the verified 1.3.0 ZIP while preserving its runtime and bundled models."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import subprocess
import sys
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
BASE_SHA256 = 'c81dc5d8fecb31cca708e417f1100ea061c037b6c3caaa7ec8b8dbb14652787d'
BASE_BYTES = 2022409929
VERSION = '1.3.1'
NAME = 'Voice-Studio-Rieng-1.3.1-TXT-SRT-Windows-x64.zip'
PATCHES = ['app/app.py', 'app/worker.py', 'app/narration.py',
           'app/timeline_audio.py', 'app/export_duration.py',
           'app/static/app.js', 'app/static/index.html']


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, cwd, env, timeout=1200):
    print('RUN:', ' '.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, env=env, timeout=timeout, check=True)


def protected(path):
    return (path.startswith(('runtime/', 'tools/', 'MODEL-LICENSES/', 'app/.data/models/'))
            or path in {'MO_TOOL.bat', 'KIEM_TRA.bat', 'portable_launcher.py'})


def unpack(base, destination):
    before = {}
    root_names = set()
    with zipfile.ZipFile(base) as bundle:
        for item in bundle.infolist():
            name = item.filename.replace('\\', '/')
            parts = PurePosixPath(name).parts
            if not parts or '..' in parts or name.startswith('/') or PureWindowsPath(name).drive:
                raise ValueError('Invalid base archive path')
            root_names.add(parts[0])
            target = destination.joinpath(*parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(item) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
            relative = '/'.join(parts[1:])
            if protected(relative):
                before[relative] = (item.CRC, item.file_size)
    if len(root_names) != 1:
        raise ValueError('Expected one root folder in the original portable ZIP')
    return destination/next(iter(root_names)), before


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-zip', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    if os.name != 'nt':
        raise RuntimeError('Validate the actual portable bundle on native Windows.')
    if args.base_zip.stat().st_size != BASE_BYTES or sha256(args.base_zip) != BASE_SHA256:
        raise ValueError('Original 1.3.0 ZIP size/SHA-256 mismatch')
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    root, before = unpack(args.base_zip, work/'unpacked')
    # Force relocation and a nontrivial path, as in the original portable proof.
    relocated = root.with_name('Voice Studio Rieng 1.3.1 test with spaces')
    root.rename(relocated)
    root = relocated
    for relative in PATCHES:
        source, target = SOURCE/relative, root/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert sha256(source) == sha256(target)
    shutil.rmtree(root/'app/__pycache__', ignore_errors=True)
    info_path = root/'BUILD.json'
    info = json.loads(info_path.read_text(encoding='utf-8')) if info_path.is_file() else {}
    info.update(version=VERSION, source_commit=os.environ['GITHUB_SHA'],
                original_version='1.3.0', original_archive_sha256=BASE_SHA256,
                reused_runtime_and_models=True, qwen_bundled=False,
                native_windows_offline_validation=False)
    info_path.write_text(json.dumps(info, indent=2), encoding='utf-8')
    env = dict(os.environ, PYTHONHOME=str(root/'runtime'), PYTHONNOUSERSITE='1',
               PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
               VOICE_STUDIO_DATA_DIR=str(work/'unit-data'),
               HF_HOME=str(root/'app/.data/models/cache'),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               VOICE_STUDIO_PORTABLE='1',
               PATH=str(root/'tools/ffmpeg/bin')+os.pathsep+str(root/'runtime')+os.pathsep+os.environ['PATH'])
    env.pop('PYTHONPATH', None)
    python = root/'runtime/python.exe'
    run([python, '-m', 'pytest', '-q', '-ra', SOURCE/'app/tests'],
        SOURCE/'app', env)
    run(['node', '--check', SOURCE/'app/static/app.js'], SOURCE, env)
    env['VOICE_STUDIO_DATA_DIR'] = str(root/'app/.data')
    run([python, SOURCE/'packaging/smoke_portable.py', root], root, env, timeout=1800)
    country = {}
    for path in (root/'app/.data/jobs').glob('*.json'):
        job = json.loads(path.read_text(encoding='utf-8'))
        if job.get('engine') == 'piper' and job.get('timeline_seconds') == 20:
            if not job.get('duration_verified') or not job.get('sync_ok'):
                raise ValueError('Country voice did not complete actual duration verification')
            if job['duration_report']['sample_frames'] != 480000:
                raise ValueError('Country voice is not exactly 20 seconds')
            country.setdefault(job['voice_id'], []).append(job['format'])
    if len(country) != 16 or any(sorted(formats) != ['mp3', 'wav'] for formats in country.values()):
        raise ValueError('Expected actual TXT/WAV and SRT/MP3 checks for all 16 original Piper voices')
    # The original cleanup excludes models, exactly as in its release builder.
    for path in (root/'app/.data').iterdir():
        if path.name == 'models':
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for name in ('voices', 'audio', 'jobs', 'parts'):
        (root/'app/.data'/name).mkdir()
    shutil.rmtree(root/'app/__pycache__', ignore_errors=True)
    info['native_windows_offline_validation'] = True
    info['verified_piper_voice_count'] = len(country)
    info_path.write_text(json.dumps(info, indent=2), encoding='utf-8')
    (root/'CAP_NHAT_TXT_SRT_1.3.1.txt').write_text(
        'VOICE STUDIO RIENG 1.3.1 - BAN SUA TXT/SRT TREN GOI GOC 1.3.0\n\n'
        'Giai nen toan bo ZIP vao thu muc moi, nhan dup MO_TOOL.bat.\n'
        'Giu nguyen Python, FFmpeg, Nano/Turbo, nhan ban Viet va 16 giong Piper.\n'
        'SRT: bat Tu can loi doc theo moc thoi gian; de trong thoi luong de lay moc cuoi.\n'
        'TXT: nhap cung thoi luong dich, vi du 10:00; so khong co dau : duoc tinh bang giay.\n'
        'Da nhap thoi luong thi can bat Tu can, tool se khong am tham bo qua thoi luong.\n'
        'WAV/MP3 duoc do lai tren file thuc te truoc khi bao hoan tat.\n'
        'Cau qua dai se bao loi, khong cat mat loi de ep khop.\n'
        'Ban nay chi cap nhat ma, khong them model Qwen hay thu vien giong moi.\n',
        encoding='utf-8-sig')
    proof = {'version': VERSION, 'base_bytes': BASE_BYTES, 'base_sha256': BASE_SHA256,
             'source_commit': os.environ['GITHUB_SHA'],
             'native_windows_offline_validation': True,
             'piper_country_formats': country, 'protected_file_count': len(before),
             'runtime_and_models_unchanged': False}
    # Check original CRC+size entries against the final ZIP, including every
    # runtime binary and model. The original download has already passed SHA-256.
    root_name = 'Voice-Studio-Rieng-Portable'
    archive = work/NAME
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                output.write(path, root_name+'/'+relative)
    with zipfile.ZipFile(archive) as result:
        after = {'/'.join(PurePosixPath(entry.filename).parts[1:]): (entry.CRC, entry.file_size)
                 for entry in result.infolist()
                 if protected('/'.join(PurePosixPath(entry.filename).parts[1:]))}
        if before != after:
            changed = sorted(key for key in set(before)|set(after) if before.get(key) != after.get(key))
            raise ValueError('Original runtime/model files changed: '+', '.join(changed[:30]))
        if result.testzip() is not None:
            raise ValueError('Final ZIP failed CRC verification')
    if archive.stat().st_size > BASE_BYTES + 20*1024**2:
        raise ValueError('Unexpected package growth: code-only update must stay close to the original 2.02 GB')
    proof['runtime_and_models_unchanged'] = True
    proof['zip_bytes'] = archive.stat().st_size
    proof['zip_sha256'] = sha256(archive)
    (work/'QA.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
    Path(str(archive)+'.sha256').write_text(proof['zip_sha256']+'  '+archive.name+'\n', encoding='ascii')
    print('VERIFIED ORIGINAL MODELS AND RUNTIME:', len(before), 'files', flush=True)
    print('VERIFIED PACKAGE:', archive, archive.stat().st_size, proof['zip_sha256'], flush=True)


if __name__ == '__main__':
    main()
