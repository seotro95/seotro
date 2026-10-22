"""Publish a complete Windows ZIP only after native regression and clone checks.

The base runtime/FFmpeg/Whisper assets come from a hash-verified native Windows
release. Application source is the current branch checkout. No developer data,
recordings, credentials or history are copied into the deliverable.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
import zipfile


VERSION = '3.7.0'
BRANCH = 'codex/voice-studio-3-7-download-20261022'
REPOSITORY = 'seotro95/seotro'
BASE_URL = 'https://github.com/seotro95/seotro/releases/download/windows-portable-35/Voice-Studio-Windows-x64.zip'
BASE_SHA256 = '0d5e46f3500dca1c070fce31071c0c18ff04ec0fe50b70672aad20d85a342750'
ASSET_NAME = 'Voice-Studio-3.7.0-Windows-x64-Full.zip'
SOURCE = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, *, env=None, cwd=None, timeout=600, capture=False):
    print('RUN: ' + ' '.join(str(part) for part in command), flush=True)
    result = subprocess.run([str(part) for part in command], cwd=cwd, env=env,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.STDOUT if capture else None,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if capture:
        print(result.stdout, flush=True)
    if result.returncode:
        raise RuntimeError(f'Command exited {result.returncode}: {command[0]}')
    return result.stdout if capture else None


def download_base(archive):
    partial = archive.with_suffix('.partial')
    for attempt in range(3):
        try:
            print(f'Downloading verified Windows base, attempt {attempt + 1}/3...', flush=True)
            request = urllib.request.Request(BASE_URL, headers={'User-Agent': 'Voice-Studio-3.7-Portable-Builder'})
            with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as output:
                shutil.copyfileobj(response, output, 1024 * 1024)
            if digest(partial) != BASE_SHA256:
                raise RuntimeError('Base ZIP SHA256 mismatch; do not use or publish it.')
            partial.replace(archive)
            return
        except (OSError, RuntimeError) as error:
            partial.unlink(missing_ok=True)
            print(f'Base download did not finish: {error}', flush=True)
            if attempt == 2:
                raise


def extract_base(archive, root):
    with zipfile.ZipFile(archive) as bundle:
        file_infos = [info for info in bundle.infolist() if not info.is_dir()]
        roots = {PurePosixPath(info.filename).parts[0] for info in file_infos}
        if len(roots) != 1:
            raise RuntimeError('Unexpected base ZIP root structure.')
        for info in file_infos:
            parts = PurePosixPath(info.filename).parts
            mode = info.external_attr >> 16
            if PurePosixPath(info.filename).is_absolute() or '..' in parts or any(':' in part for part in parts) or stat.S_ISLNK(mode):
                raise RuntimeError('Unsafe base ZIP entry: ' + info.filename)
            target = root.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
    for relative in ('runtime/python.exe', 'runtime/msvcp140.dll', 'runtime/vcruntime140.dll', 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe', 'voice-studio/.data/models/whisper-base/model.bin'):
        if not (root / relative).is_file():
            raise RuntimeError('Required bundled component missing: ' + relative)


def clean_projects(data):
    data.mkdir(parents=True, exist_ok=True)
    for path in data.iterdir():
        if path.name == 'models':
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for name in ('audio', 'parts', 'jobs', 'voices', 'videos', 'video_tasks', 'editor'):
        (data / name).mkdir()


def overlay_source(root):
    source = SOURCE / 'voice-studio'
    target = root / 'voice-studio'
    # Preserve downloaded model storage only, then replace all application code.
    for path in target.iterdir():
        if path.name == '.data':
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    allowed_folders = {'static', 'tests', 'examples', 'packaging'}
    allowed_suffixes = {'.py', '.js', '.css', '.html', '.txt', '.md', '.bat', '.sh', '.ps1', '.srt'}
    for path in source.rglob('*'):
        relative = path.relative_to(source)
        if not path.is_file() or path.suffix not in allowed_suffixes or any(part.startswith('.') or part == '__pycache__' for part in relative.parts):
            continue
        if len(relative.parts) > 1 and relative.parts[0] not in allowed_folders:
            continue
        if relative.name == 'requirements-tested.txt':
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    assert "version='3.7.0'" in (target / 'app.py').read_text(encoding='utf-8')
    assert (target / 'tests/test_nano_cloning_worker.py').is_file()
    clean_projects(target / '.data')


def bundled_env(root, *, offline):
    app = root / 'voice-studio'
    env = dict(os.environ, PATH=str(root / 'runtime') + os.pathsep + str(root / 'ffmpeg/bin') + os.pathsep + os.environ.get('PATH', ''),
               PYTHONUTF8='1', PYTHONNOUSERSITE='1', VOICE_STUDIO_PORTABLE='1',
               VOICE_STUDIO_DATA_DIR=str(app / '.data'), HF_HOME=str(app / '.data/models/cache'), HF_HUB_DISABLE_XET='1',
               HF_HUB_OFFLINE='1' if offline else '0', TRANSFORMERS_OFFLINE='1' if offline else '0')
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    return env


CLONE_SMOKE = r'''import io,json,sys,time,wave
from pathlib import Path
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
app_root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(app_root))
import app as studio
from subtitles import parse_srt
assert Path(sys.executable).parent.name=='runtime'
assert Path(sys.prefix).resolve()==Path(sys.executable).resolve().parent
data=app_root/'.data'
samples,rate=sf.read(data/'models/nano-check.wav',dtype='float32')
assert samples.size and np.isfinite(samples).all() and np.max(np.abs(samples))>.001
while len(samples)/rate<6:samples=np.concatenate((samples,samples))
samples=samples[:rate*15]
reference=io.BytesIO();sf.write(reference,samples,rate,format='WAV',subtype='PCM_16')
def wait(client,job):
 deadline=time.monotonic()+240
 while time.monotonic()<deadline:
  result=client.get('/api/jobs/'+job['id']);assert result.status_code==200
  value=result.json()
  if value['status']=='done':return value
  if value['status'] in {'error','cancelled'}:raise AssertionError(value)
  time.sleep(.2)
 raise AssertionError('Native clone generation timed out')
measurements=[]
with TestClient(studio.app) as client:
 assert client.get('/api/config').json()['version']=='3.7.0'
 for engine in ('vieneu_nano','vieneu'):
  enrolled=client.post('/api/voices/clone',data={'name':'Synthetic QA '+engine,'language':'vi','engine':engine,'consent':'true'},files={'file':('reference.wav',reference.getvalue(),'audio/wav')})
  assert enrolled.status_code==201,enrolled.text
  voice=enrolled.json();assert voice['engine']==engine
  text='Đây là nội dung mới để kiểm tra nhân bản giọng. Chúc bạn một ngày vui vẻ.'
  queued=client.post('/api/speech',json={'text':text,'voice_id':voice['id'],'language':'vi','format':'mp3','delivery':'review','paragraph_pause':.28,'nano_steps':8,'nano_threads':2})
  assert queued.status_code==202,queued.text
  job=wait(client,queued.json())
  assert not job.get('duration_limited') and job['completed']==job['total']
  for extension in ('wav','mp3','txt','srt'):
   response=client.get('/api/jobs/'+job['id']+'/export.'+extension)
   assert response.status_code==200 and len(response.content)>10,(extension,response.status_code,response.text[:200] if response.status_code!=200 else '')
   if extension=='wav':
    rendered,rate=sf.read(io.BytesIO(response.content),dtype='float32');assert len(rendered)>rate*.3 and np.isfinite(rendered).all() and np.max(np.abs(rendered))>.001
   elif extension=='txt':assert response.text.split()==text.split(), (response.text,text)
   elif extension=='srt':assert parse_srt(response.text)
  measurements.append({'engine':engine,'audio_seconds':job['audio_seconds'],'processing_seconds':job.get('wall_processing_seconds'),'exports':['wav','mp3','txt','srt']})
  if engine=='vieneu_nano':
   srt='1\n00:00:01,000 --> 00:00:07,000\nXin chào bạn.\n\n2\n00:00:08,000 --> 00:00:16,000\nHẹn gặp lại.\n'
   queued=client.post('/api/speech',json={'text':srt,'input_format':'srt','voice_id':voice['id'],'language':'vi','format':'wav','delivery':'story','paragraph_pause':0,'nano_steps':8,'nano_threads':2})
   assert queued.status_code==202,queued.text
   timed=wait(client,queued.json());assert abs(timed['audio_seconds']-16)<.002
   exported=client.get('/api/jobs/'+timed['id']+'/export.srt');assert exported.status_code==200
   cues=parse_srt(exported.text);assert [c['start'] for c in cues]==[1,8] and [c['end'] for c in cues]==[7,16]
   measurements.append({'engine':'vieneu_nano','input_format':'srt','timeline_seconds':timed['audio_seconds'],'cue_starts':[1,8],'cue_ends':[7,16]})
Path(sys.argv[2]).write_text(json.dumps({'passed':True,'new_text_clone_checks':measurements},ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: native offline NEW TEXT Nano/Turbo clones; review/story; WAV/MP3/TXT/SRT exports and exact SRT timeline')
'''


PORTABLE_GUIDE = '''VOICE STUDIO 3.7.0 — WINDOWS 10/11 x64 PORTABLE

1. GIẢI NÉN TOÀN BỘ ZIP vào thư mục có quyền ghi, ví dụ D:\\VoiceStudio.
2. Bấm đúp MO_TOOL.bat trong thư mục vừa giải nén.
3. Trình duyệt tự mở khi sẵn sàng. Giữ cửa sổ chạy; Ctrl+C để tắt.

ĐÃ KÈM SẴN: Python và thư viện Windows, FFmpeg/FFprobe, Nano, nhân bản Nano,
Turbo và Whisper nhận dạng phụ đề. Không cần cài Python/FFmpeg, tạo venv,
nhập API key hoặc tải model Việt trong lần mở đầu.

Tạo voice: nhập/dán TXT hoặc SRT -> chọn giọng, kiểu đọc -> Tạo giọng nói.
Nhân bản: mẫu được phép dùng 3–30 giây -> Nano/Turbo -> lưu -> Sử dụng giọng
-> nhập lời mới -> tạo voice. Tải WAV/MP3/TXT/SRT trong Lịch sử.
Kiểu đọc gồm Tự nhiên, Kể chuyện, Review, Tin tức, Quảng cáo, Hướng dẫn,
Thư giãn, Sôi nổi; thay đổi nhịp, tốc độ và khoảng nghỉ.

Dữ liệu cá nhân lưu trong voice-studio/.data; sao lưu trước khi xóa bộ tool.
Gói không kèm bản thu, giọng cá nhân, API key hoặc lịch sử người dùng.
Qwen quốc tế và Ollama/API viết/dịch là tùy chọn, cần tải/kết nối riêng.

Chưa đạt mục tiêu 2 phút/1 giờ voice trên CPU đã đo. Mẫu Linux Nano4 trước
đây đạt 7,39x; ngoại suy 8,1 phút/giờ, chưa chạy đủ một giờ.

Gói chỉ được xuất bản sau khi native Windows regression, Nano/Turbo offline,
nhân bản bằng lời mới và xuất WAV/MP3/TXT/SRT thành công.
Chi tiết: PORTABLE-VERIFICATION.json và voice-studio/VALIDATION.md.

THÔNG BÁO PHẦN MỀM ĐI KÈM
Python: runtime/LICENSE.txt. Thư viện: runtime/Lib/site-packages/*.dist-info.
FFmpeg GPL: ffmpeg/LICENSE* và tài liệu đi kèm.
Model: thẻ/license trong voice-studio/.data/models/cache/hub.
MSVC: https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files
'''


LAUNCHER = '''@echo off
setlocal
cd /d "%~dp0"
set "PATH=%~dp0runtime;%~dp0ffmpeg\\bin;%PATH%"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "VOICE_STUDIO_DATA_DIR=%~dp0voice-studio\\.data"
set "HF_HOME=%VOICE_STUDIO_DATA_DIR%\\models\\cache"
set "VOICE_STUDIO_PORTABLE=1"
if not exist "runtime\\python.exe" goto incomplete
if not exist "ffmpeg\\bin\\ffmpeg.exe" goto incomplete
if not exist "ffmpeg\\bin\\ffprobe.exe" goto incomplete
if not exist "voice-studio\\.data\\models\\vieneu_nano_clone.ready" goto incomplete
echo Voice Studio 3.7.0 - dang mo tool...
"runtime\\python.exe" "voice-studio\\portable_launcher.py"
set "VOICE_START_EXIT=%ERRORLEVEL%"
pause
exit /b %VOICE_START_EXIT%
:incomplete
echo Giai nen TOAN BO ZIP roi mo lai MO_TOOL.bat.
pause
exit /b 1
'''


def write_portable_docs(root):
    for name in ('MO_TOOL.bat', 'MO_VOICE_STUDIO.bat'):
        (root / name).write_text(LAUNCHER, encoding='ascii', newline='\r\n')
    (root / 'THEM_GIONG_QUOC_TE.bat').write_text('@echo off\nsetlocal\ncd /d "%~dp0voice-studio"\ncall THEM_GIONG_QUOC_TE.bat\nexit /b\n', encoding='ascii', newline='\r\n')
    (root / 'DOC_TRUOC_KHI_DUNG.txt').write_text(PORTABLE_GUIDE, encoding='utf-8-sig')
    (root / 'READ-ME-FIRST.txt').write_text(PORTABLE_GUIDE, encoding='utf-8-sig')
    (root / 'voice-studio/HUONG_DAN_NHANH.txt').write_text(PORTABLE_GUIDE, encoding='utf-8-sig')
    readme = root / 'voice-studio/README.md'
    note = ('> **Bản Portable đầy đủ:** gói này đã kèm Python, FFmpeg, Nano, nhân bản Nano, Turbo và Whisper. '
            'Giải nén toàn bộ rồi mở `../MO_TOOL.bat`; không chạy các bước cài từ mã nguồn bên dưới. '
            'Các hướng dẫn cài Python/FFmpeg chỉ áp dụng gói mã nguồn. Xem `../DOC_TRUOC_KHI_DUNG.txt`.\n\n')
    readme.write_text(note + readme.read_text(encoding='utf-8'), encoding='utf-8')


def create_archive(root, output):
    files = [path for path in sorted(root.rglob('*')) if path.is_file()]
    hashes = {path.relative_to(root).as_posix(): digest(path) for path in files}
    (root / 'FILES-SHA256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as bundle:
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise RuntimeError('Unmaterialized link in portable package: ' + str(path))
            if path.is_file():
                bundle.write(path, 'Voice-Studio-3.7.0/' + path.relative_to(root).as_posix())
    if output.stat().st_size >= 2 * 1024 ** 3:
        raise RuntimeError('ZIP exceeds the 2GB GitHub release asset limit; do not publish.')
    with zipfile.ZipFile(output) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError('Final ZIP CRC verification failed; do not publish.')
        names = bundle.namelist()
        required = ('MO_TOOL.bat', 'runtime/python.exe', 'runtime/msvcp140.dll', 'ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin/ffprobe.exe',
                    'voice-studio/.data/models/vieneu_nano.ready', 'voice-studio/.data/models/vieneu_nano_clone.ready',
                    'voice-studio/.data/models/vieneu.ready', 'voice-studio/.data/models/whisper-base/model.bin')
        for relative in required:
            assert 'Voice-Studio-3.7.0/' + relative in names, relative
    checksum = digest(output)
    output.with_suffix(output.suffix + '.sha256').write_text(checksum + '  ' + output.name + '\n', encoding='ascii')
    return checksum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', required=True, type=Path)
    args = parser.parse_args()
    if os.name != 'nt' or sys.maxsize <= 2 ** 32:
        raise RuntimeError('Build and validate on native Windows x64 only.')
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or os.environ.get('GITHUB_REF') != 'refs/heads/' + BRANCH:
        raise RuntimeError('Publish only the dedicated source branch in the intended repository.')
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    root = work / 'Voice-Studio-3.7.0'
    root.mkdir()
    base_archive = work / 'verified-windows-base.zip'
    download_base(base_archive)
    extract_base(base_archive, root)
    provenance = root / 'provenance'
    provenance.mkdir(exist_ok=True)
    for name in ('BUILD.json', 'BUILD-DEPENDENCIES.txt'):
        if (root / name).is_file():
            shutil.copy2(root / name, provenance / ('BASE-' + name))
    overlay_source(root)
    app = root / 'voice-studio'
    runtime = root / 'runtime/python.exe'
    online = bundled_env(root, offline=False)
    offline = bundled_env(root, offline=True)
    run([runtime, '-m', 'pip', 'check'], env=offline, cwd=app)
    regression_log = run([runtime, app / 'packaging/ci_checks.py'], env=offline, cwd=app, capture=True, timeout=300)
    (provenance / 'WINDOWS-REGRESSION.txt').write_text(regression_log, encoding='utf-8')
    run([runtime, app / 'prepare_models.py', 'vieneu_nano_clone'], env=online, cwd=app, timeout=1800)
    # Keep upstream cards/licenses while obtaining any lazily loaded clone graphs.
    cards = "from huggingface_hub import hf_hub_download; " + "; ".join(
        f"hf_hub_download({repo!r},'README.md')" for repo in ('pnnbao-ump/VieNeu-TTS-v3-Nano', 'pnnbao-ump/VieNeu-TTS-v3-Turbo', 'OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX'))
    run([runtime, '-c', cards], env=online, cwd=app, timeout=300)
    sys.path.insert(0, str(SOURCE / 'voice-studio/packaging'))
    from build_windows import materialize_model_cache
    materialize_model_cache(app / '.data/models/cache/hub')
    run([runtime, app / 'packaging/smoke_portable.py', app], env=offline, cwd=app, timeout=900)
    clone_script = work / 'native_clone_smoke.py'
    clone_script.write_text(CLONE_SMOKE, encoding='utf-8')
    clone_report = provenance / 'WINDOWS-CLONE-CHECKS.json'
    run([runtime, clone_script, app, clone_report], env=offline, cwd=app, timeout=900)
    # Both subprocesses have exited, releasing Windows locks before cleanup.
    clean_projects(app / '.data')
    for pattern in ('*check.wav', '*check.mp3'):
        for path in (app / '.data/models').glob(pattern):
            path.unlink()
    for directory_name in ('__pycache__', '.pytest_cache'):
        for path in list(root.rglob(directory_name)):
            shutil.rmtree(path)
    for pattern in ('*.pyc', '*.pyo'):
        for path in root.rglob(pattern):
            path.unlink()
    # QA output must never be mistaken for user projects in the shipped app.
    assert not any(path.is_file() for path in (app / '.data').rglob('*') if (app / '.data/models') not in path.parents)
    write_portable_docs(root)
    verified_at = datetime.now(timezone.utc).isoformat()
    report = {'version': VERSION, 'source_commit': os.environ['GITHUB_SHA'], 'branch': BRANCH,
              'native_windows_x64': True, 'verified_at_utc': verified_at,
              'github_run_id': os.environ['GITHUB_RUN_ID'], 'base_archive_sha256': BASE_SHA256,
              'native_regression_passed': True, 'relocated_offline_smoke_passed': True,
              'new_text_clone_checks': json.loads(clone_report.read_text(encoding='utf-8')),
              'models_bundled': ['vieneu_nano', 'vieneu_nano_clone', 'vieneu', 'whisper-base'],
              'runtime_and_ffmpeg_bundled': True, 'qwen_international_bundled': False,
              'personal_data_included': False, 'target_2min_per_hour_achieved': False}
    (root / 'PORTABLE-VERIFICATION.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'BUILD.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    validation = app / 'VALIDATION.md'
    with validation.open('a', encoding='utf-8') as stream:
        stream.write('\n\n## Kiểm tra gói Portable trên Windows thật\n\n'
                     f'Commit `{os.environ["GITHUB_SHA"]}`; GitHub Actions `{os.environ["GITHUB_RUN_ID"]}`; {verified_at}. '
                     'Đã qua hồi quy Windows, runtime sau khi chuyển thư mục, Nano/Turbo offline, nhân bản bằng lời mới, '
                     'Review/Kể chuyện và xuất WAV/MP3/TXT/SRT. Các mục chưa kiểm chứng Windows ở phần lịch sử bên trên '
                     'được cập nhật bởi kết quả bản dựng này. Xem `../PORTABLE-VERIFICATION.json`.\n')
    output = work / ASSET_NAME
    checksum = create_archive(root, output)
    tag = f'voice-studio-3.7.0-full-{os.environ["GITHUB_RUN_ID"]}-a{os.environ.get("GITHUB_RUN_ATTEMPT", "1")}'
    notes = work / 'release-notes.txt'
    notes.write_text('Voice Studio 3.7.0 Windows 10/11 x64 đầy đủ.\n\n'
                     'Tải ZIP, giải nén toàn bộ và bấm MO_TOOL.bat. Đã kèm Python, thư viện, FFmpeg/FFprobe, '
                     'giọng Việt Nano/Turbo, nhân bản Nano/Turbo và Whisper; không cần tự cài hoặc tải model Việt lần đầu.\n\n'
                     'Đã kiểm tra trên Windows thật: hồi quy, runtime đã chuyển thư mục, tạo voice/nhân bản bằng lời mới offline '
                     'và xuất WAV/MP3/TXT/SRT. Qwen quốc tế và AI viết/dịch là tùy chọn tải/kết nối riêng.\n\n'
                     'Chưa đạt mục tiêu 2 phút cho một giờ voice trên CPU đã đo; tốc độ phụ thuộc máy và thiết lập.\n\n'
                     f'Source commit: {os.environ["GITHUB_SHA"]}\nSHA256: {checksum}\n', encoding='utf-8')
    run(['gh', 'release', 'create', tag, output, output.with_suffix(output.suffix + '.sha256'), '--repo', REPOSITORY,
         '--target', os.environ['GITHUB_SHA'], '--title', 'Voice Studio 3.7.0 - Windows x64 đầy đủ', '--notes-file', notes, '--latest=false'], timeout=900)
    raw = run(['gh', 'api', f'repos/{REPOSITORY}/releases/tags/{tag}'], capture=True)
    release = json.loads(raw)
    asset = next(item for item in release['assets'] if item['name'] == ASSET_NAME)
    assert asset['state'] == 'uploaded' and asset['size'] == output.stat().st_size
    assert not asset.get('digest') or asset['digest'] == 'sha256:' + checksum
    delivery = {'tag': tag, 'release_url': release['html_url'], 'download_url': asset['browser_download_url'],
                'bytes': asset['size'], 'sha256': checksum, 'source_commit': os.environ['GITHUB_SHA']}
    (work / 'published-download.json').write_text(json.dumps(delivery, indent=2), encoding='utf-8')
    print(json.dumps(delivery, indent=2), flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write(f'## Voice Studio 3.7.0 đầy đủ\n\n[Tải ZIP]({delivery["download_url"]})\n\n'
                          f'Size: {asset["size"]:,} bytes. SHA256: `{checksum}`. Native Windows checks passed.\n')


if __name__ == '__main__':
    main()
