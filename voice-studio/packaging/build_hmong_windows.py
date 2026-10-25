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
import re
import shutil
import subprocess
import sys
import zipfile

from build_windows import copy_runtime, download_verified_ffmpeg
from fresh_hmong_portable import wave_evidence_bytes

SOURCE = Path(__file__).resolve().parents[1]
VERSION = '1.6.1'
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
    (destination / 'docs').mkdir()
    for relative in ('docs/HMONG-NATIVE.md', 'docs/HUONG-DAN-HMONG.md', 'docs/HUONG-DAN-HMONG.html'):
        guide = source / relative
        if guide.is_symlink() or guide.parent.is_symlink():
            raise ValueError('Linked application documentation cannot be bundled')
        if not guide.is_file() or not guide.stat().st_size:
            raise ValueError('Required Hmong documentation is missing: ' + relative)
        shutil.copy2(guide, destination / relative)
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
    required = ('app.py', 'worker.py', 'bundle_check.py', 'runtime_instance.py', 'character_cast.py',
                'longform.py', 'reference_quality.py', 'hmong_acceleration.py',
                'hmong_engine.py', 'hmong_expression.py', 'hmong_f5.py', 'hmong_health.py',
                'hmong_native.py', 'hmong_native_models.py',
                'hmong_reference.py', 'hmong_text.py', 'hmong_assets.py', 'prepare_hmong.py',
                'prepare_hmong_native.py',
                'hmong_launcher.py', 'voice_errors.py', 'studio_variant.py', 'HMONG-README.md', 'requirements-hmong.txt')
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
    notice = '''VOICE STUDIO HMONG 1.6.1 — WINDOWS X64

Chi tai MOT goi ZIP va giai nen TOAN BO. Mo MO_VOICE_STUDIO_HMONG.bat.
HUONG DAN DAY DU: mo HUONG-DAN-HMONG.html cung thu muc bang trinh duyet.
Khi tool da mo, bam Huong dan hoac truy cap /help/hmong trong giao dien.
Tep mo chinh chon bo nhanh VITS Hmong + OpenVoice V2, khong vo tinh mo F5.
Cong cu nang cao nam trong tools; tools/MO_F5_HMONG.bat mo F5 16 buoc FP32.
Da kem Python, thu vien CPU, FFmpeg, hai MP3 nguon va cac doan tham chieu.
LAN DAU CAN INTERNET: bo nhanh tai/kiem tra khoang 580 MB, F5 khoang 1,4 GB.
Moi bo co manifest model rieng; khong can tai ca hai neu chi dung mot bo.
Khong can API key. Sau khi chuan bi xong co the dung ngoai tuyen.
tools/KIEM_TRA_HMONG.bat kiem tra tep/thu vien/model va phep tinh that, khong tai model.
Chan doan tao voice that: MO_VOICE_STUDIO_HMONG.bat --test-voice
Ket qua: voice-studio-hmong/.data/diagnostics/speech-check.json va hai WAV nam/nu.
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
TXT Hmong toi da 1.000.000 ky tu, tren 20.000 ky tu tu chia chuong/phan.
Xuat ZIP cac phan WAV/MP3, TXT/SRT va manifest; can du thoi gian/dung luong.
SRT gan giong Hmong theo nhan vat tung cue; ten nhan vat khong doc thanh loi.
Bo nhanh giu toi da 16 mau tham chieu gan dung trong RAM de doi giong.
Chua ho tro nhan dang loi noi Hmong tu dong; nhap TXT/SRT hoac sua thu cong.

Giu nguyen bo phat am Hmong ban da xac nhan; khong huan luyen model moi.
Do giong giong khong bao dam 100%; muc tieu 1 gio voice trong 2 phut (30x)
chua dat. Toc do tuy CPU/GPU. Khong co cai thien am hoc duoc tuyen bo.
Hai MP3 nghe thu va first-run-male.wav/first-run-female.wav nam trong reports.
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
    shutil.copy2(root / 'voice-studio-hmong/docs/HUONG-DAN-HMONG.html', root / 'HUONG-DAN-HMONG.html')
    (root / 'MODEL-SOURCES.json').write_text(json.dumps(model_manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'NATIVE-VALIDATION.json').write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding='utf-8')


def bundle_reports(root, reports):
    """Keep evidence and generated auditions inside the single user download."""
    root, reports = Path(root), Path(reports)
    approved = ('fresh-start.json', 'native-smoke.json', 'f5-smoke.json', 'browser-smoke.json', 'model-sources.json',
                'first-run-male.wav', 'first-run-female.wav',
                'Hmong-female-2-preview.mp3', 'Hmong-male-2-preview.mp3')
    destination = root / 'reports'
    destination.mkdir(parents=True, exist_ok=False)
    for name in approved:
        source = reports / name
        if source.is_symlink() or not source.is_file() or not source.stat().st_size:
            raise ValueError('Required release report/audition is missing: ' + name)
        shutil.copy2(source, destination / name)


def expected_reference_fingerprints():
    spec = importlib.util.spec_from_file_location('hmong_browser_reference_check', SOURCE / 'hmong_assets.py')
    assets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assets)
    return {ident: assets.reference_fingerprint(ident) for ident in ('hmong-male', 'hmong-female')}


def validate_browser_report(report):
    """Require browser clicks, matching saved preset identity and real speech."""
    required_flags = ('success', 'native_windows_validation', 'real_ui_synthesis',
                      'cloned_filter_library_selection', 'cross_panel_selection',
                      'hyphenated_text_preserved')
    if any(report.get(key) is not True for key in required_flags):
        raise ValueError('Real Windows browser selection, library and cross-panel QA must all pass')
    if report.get('platform') != 'win32' or report.get('engine') != 'hmong_native':
        raise ValueError('Browser QA must exercise native speech on real Windows')
    runtime = report.get('runtime', {})
    if runtime.get('version') != VERSION + '-hmong' or runtime.get('backend') != 'hmong_native':
        raise ValueError('Browser QA used a different runtime version or engine')
    browser = report.get('browser', {})
    if not browser.get('channel') or not browser.get('version') or browser.get('responses_mocked') is not False:
        raise ValueError('Browser QA must identify the real browser')
    script_hash = hashlib.sha256((SOURCE / 'packaging/browser_hmong_portable.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    if report.get('script_sha256') != script_hash:
        raise ValueError('Browser QA does not match the reviewed browser script')
    expected = expected_reference_fingerprints()
    if report.get('expected_reference_fingerprints') != expected:
        raise ValueError('Browser QA preset reference identities differ from the supplied recordings')
    voices, cases = report.get('voices', {}), report.get('cases', [])
    if set(voices) != set(expected) or len(cases) < 4:
        raise ValueError('Browser QA must render both presets and the library/workspace cases')
    for item in [*voices.values(), *cases]:
        ident = item.get('voice_id')
        if (ident not in expected or item.get('post_voice_id') != ident or item.get('speaker') != ident
                or item.get('hmong_reference_fingerprint') != expected[ident]
                or item.get('engine') != 'hmong_native' or not item.get('job_id')
                or item.get('status') != 'done' or item.get('real_ui_post') is not True
                or item.get('audio_playback_checked') is not True or item.get('download_verified') is not True
                or item.get('original_text_preserved') is not True
                or item.get('audio_bytes', 0) <= 1000 or item.get('audio_seconds', 0) <= 1 / 3
                or item.get('peak_amplitude', 0) <= .001 or item.get('sample_rate') != 24000
                or item.get('sample_width') != 2
                or not re.fullmatch(r'[a-f0-9]{64}', item.get('sha256', ''))):
            raise ValueError('Browser UI selection must match the saved speaker, reference and generated audio')
        playback = item.get('playback', {})
        if (playback.get('ready_state', 0) < 2 or playback.get('media_error') is not None
                or playback.get('current_time', 0) <= .05 or playback.get('duration', 0) <= 1 / 3):
            raise ValueError('Browser must successfully decode and play the actual generated speech')
    if len({case['job_id'] for case in cases}) < 4:
        raise ValueError('Browser QA must complete four separate UI speech requests')
    expected_cases = {'main_male_button': 'hmong-male', 'main_female_button': 'hmong-female',
                      'library_preset_after_cloned_filter': 'hmong-male',
                      'main_female_to_workspace_speech': 'hmong-female'}
    if {case.get('case'): case.get('voice_id') for case in cases} != expected_cases:
        raise ValueError('Browser QA must cover both explicit buttons, the library filter and workspace speech')
    if not any('Nyob-zoo' in case.get('text', '') for case in cases):
        raise ValueError('Browser QA must complete the original hyphenated Hmong text')
    features = report.get('features_1_6', {})
    longform, cast = features.get('longform', {}), features.get('character_cast', {})
    if (any(longform.get(key) is not True for key in ('success', 'million_character_editor',
            'real_archive', 'chapter_selection', 'audio_playback_checked', 'download_verified'))
            or longform.get('million_character_synthesis_performed') is not False
            or longform.get('completed_chapters') != 2
            or not longform.get('archive_job_id')
            or not re.fullmatch(r'[a-f0-9]{64}', longform.get('archive_sha256', ''))):
        raise ValueError('Browser QA must accept a million-character draft and play/download the real chapter archive')
    if (any(cast.get(key) is not True for key in ('success', 'real_ui_post',
            'reference_identities_verified', 'character_names_not_spoken', 'download_verified'))
            or cast.get('status') != 'done' or cast.get('voice_ids') != ['hmong-male', 'hmong-female']
            or cast.get('cue_count') != 2 or not cast.get('job_id')
            or cast.get('audio_bytes', 0) <= 1000 or cast.get('audio_seconds', 0) <= 1 / 3
            or cast.get('sample_rate') != 24000 or cast.get('peak_amplitude', 0) <= .001
            or not re.fullmatch(r'[a-f0-9]{64}', cast.get('sha256', ''))):
        raise ValueError('Browser QA must route two characters to the correct real Hmong voices and download speech')
    return report


def validate_native_feature_report(report):
    """Separate full-size planning from the bounded real synthesis sample."""
    longform, cast = report.get('longform', {}), report.get('character_cast', {})
    if (report.get('platform') != 'win32' or report.get('native_windows_validation') is not True
            or report.get('reference_cache_limit') != 16
            or report.get('reference_quality_advisories') is not True):
        raise ValueError('Native Windows QA must check the bounded cache and reference quality advisories')
    if (any(longform.get(key) is not True for key in ('success', 'oversize_rejected',
            'plan_preserved_all_segments', 'real_synthesis', 'short_sample_plan_injected',
            'archive_contents_verified', 'chapter_routes_verified'))
            or longform.get('accepted_characters') != 1_000_000
            or longform.get('million_character_synthesis_performed') is not False
            or longform.get('planned_chapters', 0) <= 1 or longform.get('completed_chapters') != 2
            or not 0 < longform.get('sample_characters', 0) < 1000
            or not re.fullmatch(r'[a-f0-9]{64}', longform.get('archive_sha256', ''))):
        raise ValueError('Native Windows QA must check million-character planning and real bounded chapter exports')
    if (any(cast.get(key) is not True for key in ('success', 'real_synthesis',
            'reference_identities_verified', 'original_srt_preserved'))
            or cast.get('voice_ids') != ['hmong-male', 'hmong-female']
            or cast.get('cue_characters') != ['narrator', 'guest'] or cast.get('audio_seconds', 0) <= 1):
        raise ValueError('Native Windows QA must synthesize both character references in a timed script')
    return report


def validate_fresh_start_report(report):
    """Prepared/offline smoke results cannot substitute for a user's first run."""
    flags = ('success', 'native_windows_validation', 'actual_cmd_batch', 'initial_data_absent',
             'missing_models_rejected_offline', 'models_prepared_from_empty_data')
    if (any(report.get(key) is not True for key in flags)
            or report.get('platform') != 'win32' or report.get('version') != VERSION
            or report.get('prepared_models_reused') is not False
            or report.get('external_model_cache_used') is not False):
        raise ValueError('Fresh Windows QA must prepare native models from empty data without prepared model reuse')
    script_hash = hashlib.sha256((SOURCE / 'packaging/fresh_hmong_portable.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    if report.get('script_sha256') != script_hash:
        raise ValueError('Fresh Windows QA does not match the reviewed first-run script')
    expected_steps = [('--check', True, 1), ('--probe-runtime', True, 0),
                      ('--setup-only', False, 0), ('--check', True, 0), ('--test-voice', True, 0)]
    steps = report.get('steps', [])
    if [(step.get('argument'), step.get('offline'), step.get('exit_code')) for step in steps] != expected_steps:
        raise ValueError('Fresh Windows QA must reject missing models, probe, prepare, check and synthesize in order')
    recovery = {'requested_device': 'cuda', 'requested_precision': 'int8',
                'effective_device': 'cpu', 'effective_precision': 'fp32',
                'fallback_notice': True, 'int8_notice': True, 'real_synthesis': True}
    if (report.get('legacy_environment_recovery') != recovery
            or steps[-1].get('environment_overrides') != {'HMOOB_DEVICE': 'cuda', 'HMOOB_PRECISION': 'int8'}
            or 'Đang dùng bộ CPU để tạo giọng' not in steps[-1].get('output', '')
            or 'Đã bỏ tùy chọn INT8 của F5 cũ' not in steps[-1].get('output', '')):
        raise ValueError('Fresh Windows QA must recover inherited CUDA/INT8 settings and actually synthesize on CPU FP32')
    runtime, speech = report.get('runtime_health', {}), report.get('speech_check', {})
    required_runtime_checks = {'cpu-conv1d-numpy', 'wav-soxr-scipy-librosa',
                               'import:hmong_native_vendor.vits.models',
                               'import:hmong_native_vendor.openvoice.models',
                               'import:hmong_native_vendor.watermark.models.my_model'}
    if (runtime.get('ok') is not True or runtime.get('inference_tested') is not False
            or runtime.get('kind') != 'runtime' or runtime.get('backend') != 'native'
            or not runtime.get('checks') or any(check.get('ok') is not True for check in runtime['checks'])
            or not required_runtime_checks.issubset({check.get('name') for check in runtime['checks']})
            or speech.get('ok') is not True or speech.get('inference_tested') is not True
            or speech.get('kind') != 'speech' or speech.get('backend') != 'native'
            or speech.get('device') != 'cpu'
            or speech.get('configuration', {}).get('precision') != 'fp32'):
        raise ValueError('Fresh Windows QA must execute runtime math and real speech diagnostics')
    expected = expected_reference_fingerprints()
    voices, measured = speech.get('voices', []), report.get('independently_verified_voices', [])
    for collection in (voices, measured):
        if {item.get('id') for item in collection} != set(expected) or len(collection) != 2:
            raise ValueError('Fresh Windows QA must synthesize and independently measure both default voices')
        for item in collection:
            if (item.get('reference_fingerprint') != expected[item['id']]
                    or item.get('sample_rate') != 24000 or item.get('channels') != 1
                    or item.get('frames', 0) < 8000 or item.get('duration_seconds', 0) < 1 / 3
                    or item.get('peak', 0) <= .001 or item.get('rms', 0) <= .00001
                    or not re.fullmatch(r'[a-f0-9]{64}', item.get('output_sha256', ''))):
                raise ValueError('Fresh Windows speech must match the selected reference and contain real non-silent audio')
    if ({item['id']: item['output_sha256'] for item in voices}
            != {item['id']: item['output_sha256'] for item in measured}):
        raise ValueError('Fresh Windows diagnostic WAV hashes do not match the independent measurements')
    for key in ('runtime_python_sha256', 'model_manifest_sha256'):
        if not re.fullmatch(r'[a-f0-9]{64}', report.get(key, '')):
            raise ValueError('Fresh Windows QA lacks runtime or prepared-model identity')
    return report


def validate_release_archive(archive):
    """Publication gate reads evidence from the single ZIP being uploaded."""
    prefix = f'Voice-Studio-Hmong-{VERSION}/'
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip():
            raise ValueError('Release archive CRC check failed')
        names = bundle.namelist()
        if any(not name.startswith(prefix) or '/.data/' in name for name in names):
            raise ValueError('Release archive has an unexpected root or contains QA/personal data')
        for module in ('character_cast.py', 'longform.py', 'reference_quality.py', 'hmong_health.py', 'voice_errors.py'):
            if not bundle.read(prefix + 'voice-studio-hmong/' + module):
                raise ValueError('Release archive lacks a required 1.6 runtime module: ' + module)
        application_batches = {name[len(prefix):] for name in names
                               if name.lower().endswith('.bat')
                               and name[len(prefix):].split('/')[0].lower() not in {'runtime', 'ffmpeg'}}
        expected_batches = {'MO_VOICE_STUDIO_HMONG.bat', 'tools/launch_hmong.bat',
                            'tools/MO_F5_HMONG.bat', 'tools/KIEM_TRA_HMONG.bat',
                            'tools/install_hmong_cuda.bat'}
        if application_batches != expected_batches:
            raise ValueError('Release archive must contain one root BAT and all five entrypoints')
        def read_json(relative):
            return json.loads(bundle.read(prefix + relative))
        build = read_json('BUILD.json')
        fresh = validate_fresh_start_report(read_json('reports/fresh-start.json'))
        for voice in fresh['independently_verified_voices']:
            name = 'first-run-' + voice['id'].removeprefix('hmong-') + '.wav'
            measured = wave_evidence_bytes(bundle.read(prefix + 'reports/' + name), name)
            if (measured['output_sha256'] != voice['output_sha256']
                    or measured['frames'] != voice['frames']):
                raise ValueError('The bundled first-run diagnostic speech differs from the tested WAV')
        if (build.get('fresh_windows_first_run_validation') is not True
                or build.get('runtime_python_sha256') != fresh['runtime_python_sha256']
                or hashlib.sha256(bundle.read(prefix + 'runtime/python.exe')).hexdigest() != fresh['runtime_python_sha256']):
            raise ValueError('Release archive lacks the exact runtime tested from empty Windows data')
        sources = build.get('application_sha256', {})
        for required in ('hmong_launcher.py', 'hmong_health.py', 'voice_errors.py', 'prepare_hmong.py',
                         'hmong_native.py', 'docs/HUONG-DAN-HMONG.md', 'docs/HUONG-DAN-HMONG.html'):
            if required not in sources:
                raise ValueError('Release archive lacks a required source checksum: ' + required)
        for relative, expected in sources.items():
            if ('..' in relative.split('/') or relative.startswith('/') or '\\' in relative
                    or not re.fullmatch(r'[a-f0-9]{64}', expected)):
                raise ValueError('Invalid release source checksum entry')
            raw = bundle.read(prefix + 'voice-studio-hmong/' + relative)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Release application checksum mismatch: ' + relative)
            source = SOURCE / {'README.md': 'HMONG-README.md',
                               'requirements.txt': 'requirements-hmong.txt'}.get(relative, relative)
            if source.is_file() and hashlib.sha256(raw.replace(b'\r\n', b'\n')).digest() != hashlib.sha256(source.read_bytes().replace(b'\r\n', b'\n')).digest():
                raise ValueError('Release application differs from the reviewed source: ' + relative)
        app_prefix = prefix + 'voice-studio-hmong/'
        if any(name.startswith(app_prefix) and not name.endswith('/')
               and name[len(app_prefix):] not in sources for name in names):
            raise ValueError('Release application contains files outside the approved source manifest')
        guide = bundle.read(prefix + 'voice-studio-hmong/docs/HUONG-DAN-HMONG.html')
        if bundle.read(prefix + 'HUONG-DAN-HMONG.html') != guide:
            raise ValueError('The root full guide differs from the in-app full guide')
        browser = validate_browser_report(read_json('reports/browser-smoke.json'))
        native, f5 = read_json('reports/native-smoke.json'), read_json('reports/f5-smoke.json')
        validate_native_feature_report(native)
        longform = browser['features_1_6']['longform']
        if (longform['archive_job_id'] != native['longform'].get('job_id')
                or longform['archive_sha256'] != native['longform']['archive_sha256']):
            raise ValueError('Browser and native QA must verify the same real chapter archive')
        if (build.get('version') != VERSION or build.get('windows_browser_validation') is not True
                or not native.get('success') or not f5.get('success')
                or native['main_launcher'].get('browser_ui') != browser
                or not native['main_launcher'].get('active_job_preserved')
                or not native['main_launcher'].get('second_launch_reused')
                or not f5['advanced_f5_launcher'].get('second_launch_reused')):
            raise ValueError('Release archive lacks required native, F5, browser or duplicate-launch evidence')
        for name in ('Hmong-female-2-preview.mp3', 'Hmong-male-2-preview.mp3'):
            if len(bundle.read(prefix + 'reports/' + name)) <= 1000:
                raise ValueError('Release archive lacks a generated male/female MP3 audition')
    return browser


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
    parser.add_argument('--output', type=Path)
    parser.add_argument('--reports', type=Path)
    parser.add_argument('--validate-archive', type=Path,
                        help='Check the ZIP and mandatory Windows browser evidence before publication.')
    parser.add_argument('--runtime-source', type=Path,
                        help='Reuse the runtime from a checksum-verified previous portable release.')
    parser.add_argument('--ffmpeg-source', type=Path,
                        help='Reuse FFmpeg from a checksum-verified previous portable release.')
    args = parser.parse_args()
    if args.validate_archive:
        validate_release_archive(args.validate_archive)
        print('PASS: single ZIP, empty-data Windows first-run preparation/runtime/speech, browser, native/F5 and duplicate-launch evidence.')
        return
    if args.output is None or args.reports is None:
        parser.error('--output and --reports are required when building')
    if os.name != 'nt' or sys.maxsize <= 2 ** 32 or sys.version_info[:2] != (3, 12):
        raise RuntimeError('Build with native Windows x64 base Python 3.12')
    root, reports = args.output.resolve(), args.reports.resolve()
    browser_python = Path(os.environ.get('HMOOB_BROWSER_PYTHON', '')).resolve()
    if not browser_python.is_file() or root in browser_python.parents:
        raise RuntimeError('Provide HMOOB_BROWSER_PYTHON from a separate browser QA environment outside the package')
    if root.exists():
        raise ValueError('Output must be new; previous files are preserved')
    root.mkdir(parents=True)
    reports.mkdir(parents=True, exist_ok=True)
    app = root / 'voice-studio-hmong'
    copy_source(app)
    application_sha256 = {path.relative_to(app).as_posix(): sha256(path)
                          for path in sorted(app.rglob('*')) if path.is_file()}
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
    # This gate runs before either backend's existing prepared/offline smoke.
    # It must exercise an unprepared user download, not restore models from QA.
    checked_run([root / 'runtime/python.exe', SOURCE / 'packaging/fresh_hmong_portable.py', root, reports],
                environment=build_environment(root, offline=False, backend='native'), cwd=app, timeout=3600)
    fresh_report = validate_fresh_start_report(json.loads((reports / 'fresh-start.json').read_text(encoding='utf-8')))
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
    browser_report = validate_browser_report(json.loads((reports / 'browser-smoke.json').read_text(encoding='utf-8')))
    if not qa_report.get('success') or not compatibility.get('success'):
        raise RuntimeError('Both native and F5 Hmong smoke tests must complete')
    validate_native_feature_report(qa_report)
    qa_report['f5_compatibility'] = compatibility
    qa_report['advanced_f5_launcher'] = compatibility['advanced_f5_launcher']
    if qa_report['main_launcher'].get('browser_ui') != browser_report:
        raise RuntimeError('Windows launcher and browser evidence differ')
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
    if any(path.is_file() for path in (app / '.data/models').rglob('*')):
        raise RuntimeError('Stripped offline checks unexpectedly created model files')
    if (app / '.data').exists():
        shutil.rmtree(app / '.data')
    qa_report['stripped_package_offline_check'] = True
    qa_report['fresh_windows_first_run'] = fresh_report
    (reports / 'native-smoke.json').write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding='utf-8')
    write_notices(root, model_manifest, qa_report)
    bundle_reports(root, reports)
    dependencies = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
    (root / 'BUILD-DEPENDENCIES.txt').write_text(dependencies, encoding='utf-8')
    build = {'version': VERSION, 'variant': 'hmong', 'python': sys.version,
             'commit': os.environ.get('GITHUB_SHA'), 'platform': 'windows-x64',
             'native_windows_validation': True, 'relocated_runtime_tested': True,
             'fresh_windows_first_run_validation': True,
             'fresh_windows_first_run_script_sha256': fresh_report['script_sha256'],
             'runtime_python_sha256': fresh_report['runtime_python_sha256'],
             'application_sha256': application_sha256,
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
             'windows_browser_validation': True, 'real_ui_synthesis': True,
             'max_script_characters': 1_000_000, 'native_reference_cache_limit': 16,
             'character_cast_validation': True, 'longform_chapter_archive_validation': True,
             'million_character_synthesis_validated': False,
             'browser_validated_presets': sorted(browser_report['voices']),
             'browser_qa_script': 'voice-studio/packaging/browser_hmong_portable.py',
             'browser_qa_script_sha256': browser_report['script_sha256'],
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
    for cache in app.rglob('__pycache__'):
        shutil.rmtree(cache)
    destination = root.parent / ARCHIVE_NAME
    digest = archive_package(root, destination)
    validate_release_archive(destination)
    result = {**build, 'archive': str(destination), 'archive_bytes': destination.stat().st_size,
              'archive_sha256': digest}
    (reports / 'build.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
