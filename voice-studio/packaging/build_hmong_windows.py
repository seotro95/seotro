"""Build and validate a clean, relocatable Windows Hmong distribution.

The publicly hosted community Hmong weights have no explicit redistribution
license. The builder downloads them for real QA, records their upstream hashes,
and removes them from the archive. The normal launcher fetches them securely on
first use, then supports offline work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from build_windows import copy_runtime, download_verified_ffmpeg

SOURCE = Path(__file__).resolve().parents[1]
VERSION = '1.4.0'
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
    required = ('app.py', 'worker.py', 'bundle_check.py', 'hmong_acceleration.py',
                'hmong_engine.py', 'hmong_expression.py', 'hmong_f5.py',
                'hmong_reference.py', 'hmong_text.py', 'hmong_assets.py', 'prepare_hmong.py',
                'hmong_launcher.py', 'studio_variant.py', 'HMONG-README.md', 'requirements-hmong.txt')
    for name in required:
        if not (destination / name).is_file():
            raise ValueError('Required Hmong application file is missing: ' + name)
    # A portable Hmong download must never direct users to the Vietnamese
    # installer, its incompatible environment, or its model downloads.
    shutil.copy2(destination / 'HMONG-README.md', destination / 'README.md')
    shutil.copy2(destination / 'requirements-hmong.txt', destination / 'requirements.txt')


def build_environment(root, *, offline):
    root = Path(root)
    data = root / 'voice-studio-hmong' / '.data'
    environment = dict(os.environ, VOICE_STUDIO_VARIANT='hmong',
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
    content = '''@echo off
setlocal
cd /d "%~dp0"
set "PATH=%~dp0runtime;%~dp0ffmpeg\\bin;%PATH%"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "VOICE_STUDIO_VARIANT=hmong"
set "VOICE_STUDIO_DATA_DIR=%~dp0voice-studio-hmong\\.data"
set "HMOOB_MODEL_DIR=%VOICE_STUDIO_DATA_DIR%\\models"
"runtime\\python.exe" "voice-studio-hmong\\hmong_launcher.py" %*
set "VOICE_EXIT=%ERRORLEVEL%"
if not "%VOICE_EXIT%"=="0" pause
exit /b %VOICE_EXIT%
'''
    (root / 'MO_VOICE_STUDIO_HMONG.bat').write_bytes(content.replace('\n', '\r\n').encode('ascii'))
    check = '''@echo off
setlocal
cd /d "%~dp0"
call MO_VOICE_STUDIO_HMONG.bat --check
set "VOICE_EXIT=%ERRORLEVEL%"
pause
exit /b %VOICE_EXIT%
'''
    (root / 'KIEM_TRA_HMONG.bat').write_bytes(check.replace('\n', '\r\n').encode('ascii'))
    for folder, target in ((root, '%~dp0MO_VOICE_STUDIO_HMONG.bat'),
                           (app, '%~dp0..\\MO_VOICE_STUDIO_HMONG.bat')):
        start = '@echo off\nsetlocal\ncall "' + target + '" %*\nexit /b %ERRORLEVEL%\n'
        install = ('@echo off\nsetlocal\nif "%~1"=="" goto setup\ncall "' + target
                   + '" %*\nexit /b %ERRORLEVEL%\n:setup\ncall "' + target
                   + '" --setup-only\nexit /b %ERRORLEVEL%\n')
        for name in ('start.bat', 'start_hmong.bat'):
            (folder / name).write_bytes(start.replace('\n', '\r\n').encode('ascii'))
        for name in ('install.bat', 'install_hmong.bat'):
            (folder / name).write_bytes(install.replace('\n', '\r\n').encode('ascii'))
        install_cuda = install.replace('--setup-only', '--install-cuda')
        (folder / 'install_hmong_cuda.bat').write_bytes(install_cuda.replace('\n', '\r\n').encode('ascii'))


def checked_run(command, *, environment, cwd, timeout=2400):
    command = [str(part) for part in command]
    print('RUN:', ' '.join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=environment, check=True, timeout=timeout)


def write_notices(root, model_manifest, qa_report):
    notice = '''VOICE STUDIO HMONG 1.4.0 — WINDOWS X64

Giai nen TOAN BO ZIP, mo MO_VOICE_STUDIO_HMONG.bat.
Da kem Python, thu vien CPU, FFmpeg, hai MP3 goc va doan Hmong co loi tham chieu.
LAN DAU CAN INTERNET: tool tu tai va kiem tra khoang 1,4 GB model tu nguon
chinh thuc. Khong can API key. Sau khi chuan bi xong co the dung ngoai tuyen.
KIEM_TRA_HMONG.bat kiem tra tep va thu vien da cai, khong tu tai model.
start.bat/start_hmong.bat o ca thu muc goc va thu muc ung dung deu mo Hmong.
install.bat/install_hmong.bat chuan bi Hmong bang Python da dong goi.
Khong can cai lai Python hoac tao moi truong tieng Viet.
Goi mac dinh dung CPU. Neu co GPU NVIDIA/driver phu hop, co the chu dong
chay install_hmong_cuda.bat de tai them bo CUDA rieng bang Internet.
Bo cai CUDA duoc kem theo; chua kiem chung suy luan CUDA hoac toc do GPU.

Du lieu ca nhan o voice-studio-hmong/.data. Sao luu thu muc nay khi cap nhat.
Mac dinh tu nhien 16 buoc, FP32 de giu chat luong mo hinh goc.
4 buoc chi la ban nhap nhanh, co the giam do ro va tu nhien.
Co the chon 8/16/32 buoc FP32 de so sanh chat luong.
Chi ban nhap 4 buoc thu INT8 tren CPU, du phong FP32 neu khong tuong thich.
Hai MP3 nam/nu moi nhat duoc nhan dien bang SHA256, giu nguyen de nghe thu.
Loi Hmong cua ca hai doan mau do ban cung cap va xac nhan khop ban thu.
Tool tu chon doan tham chieu theo manifest va dien dung loi ban da gui.
Tool giu loi ban sua, khong ghi de bang loi dien san.
Voi tep khac, chon doan 3-8 giay va nhap loi Hmong khop doan mau.
Mac dinh ke chuyen, cam xuc warm, cuong do 65%; tat tu them khoang nghi.
Giu ngu canh cum/cau khi nhan tu; hieu ung nhan ap dung len ca cum.
Co the bat lai nhip tu dong hoac chen [pause=...] khi can.
Co the chon neutral/warm/joyful/sad/serious/suspense va cuong do 0..1.
Trong TXT co the dung [emotion=warm], **tu nhan manh** va [pause=0.4].
Cam xuc la dieu chinh toc do giu cao do, gain, envelope va khoang nghi
tren may; khong phai mo hinh da huan luyen cam xuc hay thay doi thanh dieu.
Chua co nhan dang loi noi Hmong: nhap TXT/SRT hoac sua phu de thu cong.
Mo hinh Hmong cong dong can nguoi nghe danh gia phat am va do giong giong.
Khong bao dam 1 gio voice trong 2 phut; toc do tuy CPU/GPU va chat luong.
Chua xac minh muc tieu 30x hoac phat am dung cac tu ua/thaj/qab/faib/rov/ris.
Hai MP3 nghe thu do tool tao co du sau tu nay de ban nghe doi chieu.
Bao cao toc do tinh do dai cac doan loi doc, loai khoang lang tool chen.

LICENSE / NGUON
Python: runtime/LICENSE.txt, https://www.python.org/
Thu vien Python: runtime/Lib/site-packages/*.dist-info/licenses
FFmpeg GPL: ffmpeg/LICENSE*, docs va UPSTREAM-SHA256.txt
F5-TTS code (MIT): https://github.com/SWivid/F5-TTS
Hmong integration: https://github.com/YangNobody12/F5-TTS-Hmong
Weights KHONG DUOC PHAN PHOI LAI trong goi nay. Tool tai truc tiep tu
Pakorn2112/F5TTS-Hmong va charactr/vocos-mel-24khz, voi revision/checksum
co dinh. Xem dieu khoan cua nha phat hanh mo hinh cho muc dich su dung.
Hai MP3 goc va doan tham chieu da duoc phep su dung trong du an. Goi khong kem
ho so giong, lich su, credential hoac ban thu khac cua nguoi dung.
'''
    (root / 'BAT-DAU.txt').write_text(notice, encoding='utf-8')
    (root / 'MODEL-SOURCES.json').write_text(json.dumps(model_manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'NATIVE-VALIDATION.json').write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding='utf-8')


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
    download_verified_ffmpeg(root / 'ffmpeg', root.parent / 'downloads')
    copy_runtime(Path(sys.base_prefix), root / 'runtime')
    write_launcher(root)
    environment = build_environment(root, offline=False)
    checked_run([root / 'runtime/python.exe', app / 'hmong_launcher.py', '--setup-only'],
                environment=environment, cwd=app)
    model_manifest = json.loads((app / '.data/models/verified-models.json').read_text(encoding='utf-8'))

    relocated = root.parent / 'Relocated Hmong test with spaces' / root.name
    relocated.parent.mkdir(parents=True, exist_ok=True)
    if relocated.exists():
        raise ValueError('Relocation test destination already exists')
    root.rename(relocated)
    try:
        checked_run([relocated / 'runtime/python.exe', SOURCE / 'packaging/smoke_hmong_portable.py',
                     relocated, reports], environment=build_environment(relocated, offline=True),
                    cwd=relocated / 'voice-studio-hmong', timeout=2400)
    finally:
        relocated.rename(root)
    qa_report = json.loads((reports / 'native-smoke.json').read_text(encoding='utf-8'))
    if not qa_report.get('success'):
        raise RuntimeError('Native Hmong smoke did not complete')

    # All data here was created by this build. Never perform this operation on a
    # user's installation or copy a developer data directory into the package.
    shutil.rmtree(app / '.data')
    if (app / '.data').exists():
        raise RuntimeError('Build data was not removed')
    empty_check = subprocess.run([root / 'runtime/python.exe', app / 'hmong_launcher.py', '--check'],
                                cwd=app, env=build_environment(root, offline=True), timeout=180)
    if empty_check.returncode != 1 or (app / '.data/models/verified-models.json').exists():
        raise RuntimeError('Offline check must report missing first-run models without downloading')
    qa_report['stripped_package_offline_check'] = True
    (reports / 'native-smoke.json').write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding='utf-8')
    write_notices(root, model_manifest, qa_report)
    dependencies = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (root / 'BUILD-DEPENDENCIES.txt').write_text(dependencies, encoding='utf-8')
    build = {'version': VERSION, 'variant': 'hmong', 'python': sys.version,
             'commit': os.environ.get('GITHUB_SHA'), 'platform': 'windows-x64',
             'native_windows_validation': True, 'relocated_runtime_tested': True,
             'models_included': False, 'first_run_model_download_required': True,
             'model_download_approx_gb': 1.4, 'api_key_required': False,
             'default_steps': 16, 'default_precision': 'fp32', 'draft_steps': 4,
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
