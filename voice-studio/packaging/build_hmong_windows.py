"""Build and validate a clean, relocatable Windows Hmong distribution.

The publicly hosted community Hmong weights have no explicit redistribution
license. The builder downloads them for real QA, records their upstream hashes,
and removes them from the archive. The normal launcher fetches them securely on
first use, then supports offline work.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from build_windows import copy_runtime, download_verified_ffmpeg

SOURCE = Path(__file__).resolve().parents[1]
VERSION = '1.5.2'
ARCHIVE_NAME = f'Voice-Studio-Hmong-{VERSION}-Windows-x64.zip'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def copy_source(destination, source=SOURCE):
    """Copy the application without unrelated installers or personal data."""
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for entry in source.iterdir():
        if entry.is_file() and (entry.suffix in {'.py', '.ps1'} or entry.name in {
                'HMONG-README.md', 'VALIDATION-HMONG.md', 'requirements-hmong.txt'}):
            if entry.is_symlink():
                raise ValueError('Linked application files cannot be bundled')
            shutil.copy2(entry, destination / entry.name)
    for relative in ('static', 'assets/hmong'):
        folder = source / relative
        if folder.is_symlink() or any(path.is_symlink() for path in folder.rglob('*')):
            raise ValueError('Linked application assets cannot be bundled')
        shutil.copytree(folder, destination / relative)
    native_guide = source / 'docs/HMONG-NATIVE.md'
    if native_guide.is_symlink() or native_guide.parent.is_symlink():
        raise ValueError('Linked application documentation cannot be bundled')
    (destination / 'docs').mkdir()
    shutil.copy2(native_guide, destination / 'docs/HMONG-NATIVE.md')
    # Only code/license files named in the checksum manifest are approved;
    # never sweep caches, downloaded checkpoints, or experiments into the ZIP.
    spec = importlib.util.spec_from_file_location('hmong_bundle_copy_check', SOURCE / 'bundle_check.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    try:
        checker.validate_native_vendor(source)
    except checker.BundleError as exc:
        raise ValueError(str(exc)) from None
    vendor = source / 'hmong_native_vendor'
    records = json.loads((vendor / 'manifest.json').read_text(encoding='utf-8'))
    for relative in ('manifest.json', *records):
        target = destination / 'hmong_native_vendor' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(vendor / relative, target)
    required = ('app.py', 'worker.py', 'bundle_check.py', 'runtime_instance.py', 'hmong_acceleration.py',
                'hmong_engine.py', 'hmong_expression.py', 'hmong_f5.py',
                'hmong_native.py', 'hmong_native_models.py',
                'hmong_reference.py', 'hmong_text.py', 'hmong_assets.py', 'prepare_hmong.py',
                'prepare_hmong_native.py',
                'hmong_launcher.py', 'studio_variant.py', 'HMONG-README.md', 'requirements-hmong.txt')
    for name in required:
        if not (destination / name).is_file():
            raise ValueError('Required Hmong application file is missing: ' + name)
    # A portable Hmong download must never direct users to the Vietnamese
    # installer, its incompatible environment, or its model downloads.
    shutil.copy2(destination / 'HMONG-README.md', destination / 'README.md')
    shutil.copy2(destination / 'requirements-hmong.txt', destination / 'requirements.txt')


def build_environment(root, *, offline, backend='f5'):
    if backend not in {'f5', 'native'}:
        raise ValueError('Unknown Hmong backend')
    root = Path(root)
    data = root / 'voice-studio-hmong' / '.data'
    environment = dict(os.environ, VOICE_STUDIO_VARIANT='hmong', HMOOB_BACKEND=backend,
                       VOICE_STUDIO_DATA_DIR=str(data), HMOOB_MODEL_DIR=str(data / 'models'),
                       HF_HOME=str(data / 'models' / 'cache'), HF_HUB_DISABLE_XET='1',
                       PYTHONNOUSERSITE='1', PYTHONUTF8='1', PYTHONUNBUFFERED='1',
                       PATH=str(root / 'runtime') + os.pathsep + str(root / 'ffmpeg' / 'bin')
                            + os.pathsep + os.environ.get('PATH', ''))
    for name in ('PYTHONHOME', 'PYTHONPATH'):
        environment.pop(name, None)
    for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE'):
        if offline:
            environment[name] = '1'
        else:
            environment.pop(name, None)
    return environment


def write_launcher(root):
    root = Path(root)
    app = root / 'voice-studio-hmong'
    app.mkdir(parents=True, exist_ok=True)
    tools = root / 'tools'
    tools.mkdir(parents=True, exist_ok=True)
    content = '''@echo off
setlocal
cd /d "%~dp0.."
set "PATH=%CD%\\runtime;%CD%\\ffmpeg\\bin;%PATH%"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "VOICE_STUDIO_VARIANT=hmong"
set "VOICE_STUDIO_DATA_DIR=%CD%\\voice-studio-hmong\\.data"
set "HMOOB_MODEL_DIR=%VOICE_STUDIO_DATA_DIR%\\models"
if not defined HMOOB_BACKEND set "HMOOB_BACKEND=native"
"runtime\\python.exe" "voice-studio-hmong\\hmong_launcher.py" %*
set "VOICE_EXIT=%ERRORLEVEL%"
if not "%VOICE_EXIT%"=="0" pause
exit /b %VOICE_EXIT%
'''
    (tools / 'launch_hmong.bat').write_bytes(content.replace('\n', '\r\n').encode('ascii'))
    primary = '''@echo off
setlocal
set "HMOOB_BACKEND=native"
call "%~dp0tools\\launch_hmong.bat" %*
exit /b %ERRORLEVEL%
'''
    (root / 'MO_VOICE_STUDIO_HMONG.bat').write_bytes(primary.replace('\n', '\r\n').encode('ascii'))
    fallback = '''@echo off
setlocal
set "HMOOB_BACKEND=f5"
call "%~dp0launch_hmong.bat" %*
exit /b %ERRORLEVEL%
'''
    (tools / 'MO_F5_HMONG.bat').write_bytes(fallback.replace('\n', '\r\n').encode('ascii'))
    check = '''@echo off
setlocal
call "%~dp0..\\MO_VOICE_STUDIO_HMONG.bat" --check
set "VOICE_EXIT=%ERRORLEVEL%"
if not "%VOICE_EXIT%"=="0" pause
exit /b %VOICE_EXIT%
'''
    (tools / 'KIEM_TRA_HMONG.bat').write_bytes(check.replace('\n', '\r\n').encode('ascii'))
    install_cuda = '''@echo off
setlocal
if "%~1"=="" goto setup
call "%~dp0..\\MO_VOICE_STUDIO_HMONG.bat" %*
exit /b %ERRORLEVEL%
:setup
call "%~dp0..\\MO_VOICE_STUDIO_HMONG.bat" --install-cuda
exit /b %ERRORLEVEL%
'''
    (tools / 'install_hmong_cuda.bat').write_bytes(install_cuda.replace('\n', '\r\n').encode('ascii'))


def checked_run(command, *, environment, cwd, timeout=2400):
    command = [str(part) for part in command]
    print('RUN:', ' '.join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=environment, check=True, timeout=timeout)


def write_notices(root, model_manifest, qa_report):
    notice = '''VOICE STUDIO HMONG 1.5.2 — WINDOWS X64

Chi tai MOT goi ZIP va giai nen TOAN BO. Mo MO_VOICE_STUDIO_HMONG.bat.
Tep mo chinh chon bo nhanh VITS Hmong + OpenVoice V2, khong vo tinh mo F5.
Cong cu nang cao nam trong tools; tools/MO_F5_HMONG.bat mo F5 16 buoc FP32.
Da kem Python, thu vien CPU, FFmpeg, hai MP3 nguon va cac doan tham chieu.
LAN DAU CAN INTERNET: bo nhanh tai/kiem tra khoang 580 MB, F5 khoang 1,4 GB.
Moi bo co manifest model rieng; khong can tai ca hai neu chi dung mot bo.
Khong can API key. Sau khi chuan bi xong co the dung ngoai tuyen.
tools/KIEM_TRA_HMONG.bat kiem tra tep/thu vien/model, khong tu tai model.
tools/install_hmong_cuda.bat la tuy chon CUDA rieng, khong bat buoc.
Chua kiem chung suy luan CUDA hoac toc do GPU. Goi nay kiem thu CPU.

Du lieu ca nhan o voice-studio-hmong/.data. Sao luu thu muc nay khi cap nhat.
Bo nhanh sinh tieng Hmong bang VITS va chuyen am sac bang OpenVoice V2.
Gan WavMark cho doan du dai; chua chung nhan dau nhan dien sau nen MP3.
Bo nhanh khong su dung so buoc F5 hay INT8 F5.
Bo F5 giu 16 buoc FP32; 4 buoc chi la ban nhap, 8/16/32 de doi chieu.
Hai MP3 nguon nam/nu moi nhat giu nguyen va nhan dien bang SHA256.
Loi cua doan tham chieu do ban cung cap, khop doan mau, duoc dien tu dong.
Tool giu loi ban sua. Tep khac can chon doan 3-8 giay va nhap dung loi.
Nhan ban giu am sac tu mau; khong bao dam giong hoan toan ban thu.
Mac dinh ke chuyen, warm 65%, giu ngu canh cum/cau, tat nhip tu dong.
Cam xuc neutral/warm/joyful/sad/serious/suspense dung xu ly nhip/am luong
cuc bo, khong phai mo hinh dieu khien cam xuc than kinh. Co TXT/SRT,
WAV/MP3 va [emotion=warm], **tu nhan manh**, [pause=0.4].
Chua ho tro nhan dang loi noi Hmong tu dong; nhap TXT/SRT hoac sua thu cong.

Chua xac minh phat am dung ua/thaj/qab/faib/rov/ris, do giong giong,
hoac muc tieu 1 gio voice trong 2 phut (30x). Toc do tuy CPU/GPU.
Hai MP3 nghe thu do bo nhanh tao nam trong reports, co du sau tu.
Thiet lap/checksum va thoi gian do tron quy trinh o NATIVE-VALIDATION.json. Bao cao
loai khoang lang tool chen; do ngan khong chung minh toc do 1 gio.
Bo F5 duoc kiem thu tuong thich rieng bang tao that 16 buoc FP32.

LICENSE / NGUON
Python: runtime/LICENSE.txt, https://www.python.org/
Thu vien Python: runtime/Lib/site-packages/*.dist-info/licenses
FFmpeg GPL: ffmpeg/LICENSE*, docs va UPSTREAM-SHA256.txt
Ma bo nhanh MIT va nguon/revision: voice-studio-hmong/hmong_native_vendor/
VITS Hmong: leejnus/HmongTTS. OpenVoice V2: myshell-ai/OpenVoice.
WavMark: wavmark/wavmark. F5-TTS: SWivid/F5-TTS (MIT),
YangNobody12/F5-TTS-Hmong, Pakorn2112/F5TTS-Hmong, charactr/vocos-mel-24khz.
Weights KHONG kem ZIP; tai truc tiep bang revision/SHA256 co dinh.
Xem MODEL-SOURCES.json va dieu khoan nha phat hanh truoc khi su dung model.
Goi khong kem ho so giong, lich su, credential hoac ban thu rieng khac.
'''
    (root / 'BAT-DAU.txt').write_text(notice, encoding='utf-8')
    (root / 'MODEL-SOURCES.json').write_text(json.dumps(model_manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'NATIVE-VALIDATION.json').write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding='utf-8')


def bundle_reports(root, reports):
    """Keep evidence and generated auditions inside the single user download."""
    root, reports = Path(root), Path(reports)
    approved = ('native-smoke.json', 'f5-smoke.json', 'model-sources.json',
                'Hmong-female-2-preview.mp3', 'Hmong-male-2-preview.mp3')
    destination = root / 'reports'
    destination.mkdir(parents=True, exist_ok=False)
    for name in approved:
        source = reports / name
        if source.is_symlink() or not source.is_file() or not source.stat().st_size:
            raise ValueError('Required release report/audition is missing: ' + name)
        shutil.copy2(source, destination / name)


def archive_package(root, destination):
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as bundle:
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise ValueError('Portable output contains a symlink')
            if path.is_file():
                bundle.write(path, root.name + '/' + path.relative_to(root).as_posix())
    if destination.stat().st_size >= 2 * 1024 ** 3:
        raise RuntimeError('ZIP exceeds the GitHub per-asset limit; do not publish')
    with zipfile.ZipFile(destination) as bundle:
        bad = bundle.testzip()
    if bad:
        raise RuntimeError('ZIP integrity check failed: ' + bad)
    digest = sha256(destination)
    Path(str(destination) + '.sha256').write_text(digest + '  ' + destination.name + '\n', encoding='ascii')
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reports', required=True, type=Path)
    parser.add_argument('--runtime-source', type=Path,
                        help='Reuse the runtime from a checksum-verified previous portable release.')
    parser.add_argument('--ffmpeg-source', type=Path,
                        help='Reuse FFmpeg from a checksum-verified previous portable release.')
    args = parser.parse_args()
    if os.name != 'nt' or sys.maxsize <= 2 ** 32 or sys.version_info[:2] != (3, 12):
        raise RuntimeError('Build with native Windows x64 base Python 3.12')
    root, reports = args.output.resolve(), args.reports.resolve()
    if root.exists():
        raise ValueError('Output must be new; previous files are preserved')
    root.mkdir(parents=True)
    reports.mkdir(parents=True, exist_ok=True)
    app = root / 'voice-studio-hmong'
    copy_source(app)
    if args.ffmpeg_source:
        ffmpeg_source = args.ffmpeg_source.resolve()
        for relative in ('bin/ffmpeg.exe', 'bin/ffprobe.exe', 'UPSTREAM-SHA256.txt'):
            if not (ffmpeg_source / relative).is_file():
                raise ValueError('Verified FFmpeg source is incomplete: ' + relative)
        if any(path.is_symlink() for path in ffmpeg_source.rglob('*')):
            raise ValueError('Verified FFmpeg source cannot contain links')
        shutil.copytree(ffmpeg_source, root / 'ffmpeg')
    else:
        download_verified_ffmpeg(root / 'ffmpeg', root.parent / 'downloads')
    copy_runtime(args.runtime_source.resolve() if args.runtime_source else Path(sys.base_prefix), root / 'runtime')
    write_launcher(root)
    environment = build_environment(root, offline=False)
    checked_run([root / 'runtime/python.exe', app / 'hmong_launcher.py', '--setup-only'],
                environment=environment, cwd=app)
    model_manifest = {'f5_hmong': json.loads(
        (app / '.data/models/verified-models.json').read_text(encoding='utf-8'))}
    checked_run([root / 'runtime/python.exe', app / 'hmong_launcher.py', '--setup-only'],
                environment=build_environment(root, offline=False, backend='native'), cwd=app)
    model_manifest['hmong_native'] = json.loads(
        (app / '.data/models/verified-native-models.json').read_text(encoding='utf-8'))
    (reports / 'model-sources.json').write_text(
        json.dumps(model_manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    relocated = root.parent / 'Relocated Hmong test with spaces' / root.name
    relocated.parent.mkdir(parents=True, exist_ok=True)
    if relocated.exists():
        raise ValueError('Relocation test destination already exists')
    root.rename(relocated)
    try:
        checked_run([relocated / 'runtime/python.exe', SOURCE / 'packaging/smoke_hmong_portable.py',
                     relocated, reports, '--backend', 'f5'],
                    environment=build_environment(relocated, offline=True),
                    cwd=relocated / 'voice-studio-hmong', timeout=1200)
        checked_run([relocated / 'runtime/python.exe', SOURCE / 'packaging/smoke_hmong_portable.py',
                     relocated, reports, '--backend', 'native'],
                    environment=build_environment(relocated, offline=True, backend='native'),
                    cwd=relocated / 'voice-studio-hmong', timeout=2400)
    finally:
        relocated.rename(root)
    qa_report = json.loads((reports / 'native-smoke.json').read_text(encoding='utf-8'))
    compatibility = json.loads((reports / 'f5-smoke.json').read_text(encoding='utf-8'))
    if not qa_report.get('success') or not compatibility.get('success'):
        raise RuntimeError('Both native and F5 Hmong smoke tests must complete')
    qa_report['f5_compatibility'] = compatibility
    qa_report['advanced_f5_launcher'] = compatibility['advanced_f5_launcher']
    if not qa_report['main_launcher']['second_launch_reused'] or not compatibility['advanced_f5_launcher']['second_launch_reused']:
        raise RuntimeError('Both launchers must reuse the running Windows studio')

    # All data here was created by this build. Never perform this operation on a
    # user's installation or copy a developer data directory into the package.
    shutil.rmtree(app / '.data')
    if (app / '.data').exists():
        raise RuntimeError('Build data was not removed')
    for backend in ('f5', 'native'):
        empty_check = subprocess.run([root / 'runtime/python.exe', app / 'hmong_launcher.py', '--check'],
                                    cwd=app, env=build_environment(root, offline=True, backend=backend), timeout=180)
        if empty_check.returncode != 1:
            raise RuntimeError('Offline check must report missing first-run models without downloading: ' + backend)
    if any(path.is_file() for path in (app / '.data').rglob('*')):
        raise RuntimeError('Stripped offline checks unexpectedly created data or model files')
    if (app / '.data').exists():
        shutil.rmtree(app / '.data')
    qa_report['stripped_package_offline_check'] = True
    (reports / 'native-smoke.json').write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding='utf-8')
    write_notices(root, model_manifest, qa_report)
    bundle_reports(root, reports)
    dependencies = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (root / 'BUILD-DEPENDENCIES.txt').write_text(dependencies, encoding='utf-8')
    build = {'version': VERSION, 'variant': 'hmong', 'python': sys.version,
             'commit': os.environ.get('GITHUB_SHA'), 'platform': 'windows-x64',
             'native_windows_validation': True, 'relocated_runtime_tested': True,
             'duplicate_launch_reused': True, 'empty_windows_lock_validated': True,
             'stale_instance_metadata_recovered': True,
             'models_included': False, 'first_run_model_download_required': True,
             'model_download_approx_gb': {'f5_hmong': 1.4, 'hmong_native': .58}, 'api_key_required': False,
             'main_launcher': 'MO_VOICE_STUDIO_HMONG.bat', 'main_engine': 'hmong_native',
             'fast_backend': 'vits_openvoice_v2', 'fast_steps': None,
             'advanced_f5_launcher': 'tools/MO_F5_HMONG.bat', 'advanced_f5_engine': 'f5_hmong',
             'default_steps': None, 'default_precision': 'fp32', 'advanced_f5_steps': 16,
             'single_main_download': True, 'single_root_launcher': True,
             'reports_bundled': True,
             'default_delivery': 'story', 'default_emotion': 'warm',
             'default_emotion_strength': .65, 'default_auto_rhythm': False,
             'default_hmong_phrase_context': True,
             'cuda_installer_included': True, 'cuda_inference_validated': False,
             'pronunciation_evaluated': False, 'target_30x_verified': False,
             'pronunciation_test_words': qa_report['pronunciation_test_words'],
             'expression_plan': 'hmong-expression-v1',
             'expression_backend': 'local_pitch_preserving_postprocessing',
             'reference_text_verified': qa_report['reference_text_verified'],
             'reference_text_source': qa_report['reference_text_source'],
             'validated_presets': ['hmong-female', 'hmong-male'],
             'validation_workflow_run': os.environ.get('GITHUB_RUN_ID')}
    (root / 'BUILD.json').write_text(json.dumps(build, ensure_ascii=False, indent=2), encoding='utf-8')
    destination = root.parent / ARCHIVE_NAME
    digest = archive_package(root, destination)
    result = {**build, 'archive': str(destination), 'archive_bytes': destination.stat().st_size,
              'archive_sha256': digest}
    (reports / 'build.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
