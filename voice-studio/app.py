from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from studio_variant import IS_HMONG, APP_NAME, APP_VERSION, DEFAULT_LANGUAGE, DEFAULT_DATA_FOLDER
from narration import MAX_CHARACTERS, PROFILES, plan_segments
import writing
from dubbing import inspect_video
from subtitles import parse_srt, export_srt
from system_voices import installed_voices
from hardware import supports_int8, system_info
from performance import speed_report
from state_io import write_json_atomic,read_progress

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE / DEFAULT_DATA_FOLDER))).resolve()
for folder in ('voices', 'audio', 'jobs', 'models', 'parts', 'videos'):
    (DATA / folder).mkdir(parents=True, exist_ok=True)
from language_catalog import LANGUAGES,CORE_LANGUAGES,QWEN_LANGUAGES,SUBTITLE_LANGUAGES,RECOGNITION_CODES,native_language

PRESETS = [
    {'id': 'vi-maianh', 'name': 'Mai Anh', 'engine': 'vieneu', 'speaker': 'Mai Anh', 'languages': ['vi', 'en-US', 'en-GB'], 'description': 'Giọng có sẵn · VieNeu'},
    {'id': 'vi-haidang', 'name': 'Hải Đăng', 'engine': 'vieneu', 'speaker': 'Hải Đăng', 'languages': ['vi', 'en-US', 'en-GB'], 'description': 'Giọng có sẵn · VieNeu'},
    {'id': 'qw-ryan', 'name': 'Ryan', 'engine': 'qwen', 'speaker': 'Ryan', 'languages': list(QWEN_LANGUAGES), 'description': 'Giọng nam · tiếng Anh bản ngữ'},
    {'id': 'qw-aiden', 'name': 'Aiden', 'engine': 'qwen', 'speaker': 'Aiden', 'languages': list(QWEN_LANGUAGES), 'description': 'Giọng nam · tiếng Anh bản ngữ'},
    {'id': 'qw-ono', 'name': 'Ono Anna', 'engine': 'qwen', 'speaker': 'Ono_Anna', 'languages': list(QWEN_LANGUAGES), 'description': 'Giọng nữ · tiếng Nhật bản ngữ'},
    {'id': 'qw-sohee', 'name': 'Sohee', 'engine': 'qwen', 'speaker': 'Sohee', 'languages': list(QWEN_LANGUAGES), 'description': 'Giọng nữ · tiếng Hàn bản ngữ'},
    {'id': 'qw-vivian', 'name': 'Vivian', 'engine': 'qwen', 'speaker': 'Vivian', 'languages': list(QWEN_LANGUAGES), 'description': 'Giọng nữ · tiếng Trung bản ngữ'},
    {'id': 'qw-serena', 'name': 'Serena', 'engine': 'qwen', 'speaker': 'Serena', 'languages': ['en-US', 'en-GB', 'ja', 'ko', 'zh', 'fr', 'de', 'es', 'it', 'pt', 'ru'], 'description': 'Giọng nữ · tiếng Trung bản ngữ'},
    {'id': 'qw-unclefu', 'name': 'Uncle Fu', 'engine': 'qwen', 'speaker': 'Uncle_Fu', 'languages': ['en-US', 'en-GB', 'ja', 'ko', 'zh', 'fr', 'de', 'es', 'it', 'pt', 'ru'], 'description': 'Giọng nam trầm · tiếng Trung bản ngữ'},
    {'id': 'qw-dylan', 'name': 'Dylan', 'engine': 'qwen', 'speaker': 'Dylan', 'languages': ['en-US', 'en-GB', 'ja', 'ko', 'zh', 'fr', 'de', 'es', 'it', 'pt', 'ru'], 'description': 'Giọng nam · tiếng Trung Bắc Kinh'},
    {'id': 'qw-eric', 'name': 'Eric', 'engine': 'qwen', 'speaker': 'Eric', 'languages': ['en-US', 'en-GB', 'ja', 'ko', 'zh', 'fr', 'de', 'es', 'it', 'pt', 'ru'], 'description': 'Giọng nam · tiếng Trung Tứ Xuyên'},
    {'id': 'nano-minhquan', 'name': 'Minh Quân · Siêu nhanh', 'engine': 'vieneu_nano', 'speaker': 'Minh Quân', 'languages': ['vi'], 'description': 'Nano 8 bước · nhanh hơn, giảm độ tự nhiên'},
    {'id': 'nano-aihan', 'name': 'Ái Hân · Siêu nhanh', 'engine': 'vieneu_nano', 'speaker': 'Ái Hân', 'languages': ['vi'], 'description': 'Nano 8 bước · nhanh hơn, giảm độ tự nhiên'},
]
if IS_HMONG:
    from hmong_assets import presets as hmong_presets
    PRESETS = hmong_presets()


def model_ready(engine):
    if engine == 'f5_hmong':
        from hmong_engine import availability
        return availability()['ready']
    return engine == 'system' or (DATA / 'models' / f'{engine}.ready').is_file()


@contextmanager
def studio_lock():
    # Prevent a second server from marking a still-running long job interrupted.
    handle = (DATA / 'server.lock').open('a+b')
    try:
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Voice Studio đã chạy với thư mục dữ liệu này. Hãy dùng cửa sổ đang mở.') from None
        yield
    finally:
        handle.close()


@asynccontextmanager
async def lifespan(application):
    global executor
    with studio_lock():
        shutdown_event.clear()
        for path in (DATA/'video_tasks').glob('*/job.json'):
            task = read_json(path)
            if task.get('status') in {'queued','running'}:
                task.update(status='error',error='Ứng dụng đã tắt trước khi xử lý xong. Hãy chạy lại tác vụ.')
                write_json(path,task)
        executor = ThreadPoolExecutor(max_workers=1)
        for interrupted in records('jobs'):
            if interrupted.get('status') in {'queued', 'running', 'cancelling'}:
                interrupted.update(status='error', error='Ứng dụng đã khởi động lại trước khi hoàn tất. Bạn có thể tiếp tục từ các đoạn đã tạo.')
                write_json(DATA / 'jobs' / f"{interrupted['id']}.json", interrupted)
        try:
            yield
        finally:
            shutdown_event.set()
            await run_in_threadpool(executor.shutdown, wait=True, cancel_futures=True)
            await run_in_threadpool(close_warm_worker)
            for pending in records('jobs'):
                if pending.get('status') == 'queued':
                    pending.update(status='error', error='Ứng dụng đã tắt. Có thể tiếp tục từ Lịch sử.')
                    write_json(DATA / 'jobs' / f"{pending['id']}.json", pending)
            with writing.KEY_LOCK:
                writing.KEYS.clear()


app = FastAPI(title=APP_NAME + ' · Local AI', version=APP_VERSION, lifespan=lifespan)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # Pydantic's default details can echo an invalid API key; return no raw input.
    return JSONResponse({'detail': 'Dữ liệu không hợp lệ. Kiểm tra giới hạn ký tự, thời lượng và các trường đã nhập.'}, status_code=422)


executor = ThreadPoolExecutor(max_workers=1)
lock = threading.RLock()
shutdown_event = threading.Event()
warm_worker = None


def now():
    return datetime.now(UTC).isoformat()


def write_json(path, data):
    write_json_atomic(path,data)


def valid_id(value):
    if len(value) != 32 or any(c not in '0123456789abcdef' for c in value):
        raise HTTPException(404, 'Không tìm thấy mục này.')
    return value


def read_json(path):
    if not path.is_file():
        raise HTTPException(404, 'Không tìm thấy mục này.')
    return json.loads(path.read_text(encoding='utf-8'))


def records(folder):
    result = []
    for path in (DATA / folder).glob('*.json'):
        try:
            result.append(read_json(path))
        except (ValueError, OSError):
            continue
    return result


@app.middleware('http')
async def local_browser_guard(request: Request, call_next):
    origin = request.headers.get('origin')
    host = request.headers.get('host', '').split(':')[0].lower()
    if host not in {'127.0.0.1', 'localhost', 'testserver'} or (origin and origin != str(request.base_url).rstrip('/')):
        return JSONResponse({'detail': 'Ứng dụng chỉ nhận yêu cầu cùng nguồn trên máy cục bộ.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self' blob:; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response


@app.get('/')
def index():
    import re
    from fastapi.responses import HTMLResponse
    html=(BASE/'static'/'index.html').read_text(encoding='utf-8')
    if IS_HMONG:
        html=html.replace('Voice Studio', APP_NAME).replace('3.6.2', APP_VERSION)
    html=re.sub(r'((?:src|href)="/static/[^"?]+)"',lambda m:m[1]+'?v='+app.version+'"',html)
    return HTMLResponse(html,headers={'Cache-Control':'no-store'})


@app.get('/api/config')
def config():
    try:
        import psutil
        available=round(psutil.virtual_memory().available/1024**3,1)
    except ImportError:
        available=0
    return {'available_ram_gb':available,**_config_values()}


def _config_values():
    if IS_HMONG:
        return {'variant':'hmong','app_name':APP_NAME,'default_language':'mww','default_voice_id':'hmong-male','version':app.version,'mode':'local',
                'languages':{'mww':LANGUAGES['mww']},'subtitle_languages':SUBTITLE_LANGUAGES,
                'recognition_languages':{k:v for k,v in SUBTITLE_LANGUAGES.items() if k.split('-')[0] in RECOGNITION_CODES},
                'ai_voice_languages':['mww'],'max_characters':MAX_CHARACTERS,'max_audio_minutes':180,
                'fast_vieneu':False,'int8_cpu':False,'models':{'f5_hmong':model_ready('f5_hmong')},
                'hmong_ready':model_ready('f5_hmong'),'hmong_steps':16,'paragraph_pause':0,'subtitle_ready':False,
                'hmong_reference_note':'Hai MP3 nam/nữ là tệp nguồn bạn gửi. Lời tham chiếu có sẵn trong dự án chưa được xác minh khớp bản thu. Nghe mẫu; nếu cần sửa lời, nhập MP3 gốc vào phần Nhân bản và lưu hồ sơ giọng đã chỉnh. Lời khớp đoạn thu giúp mô hình đọc rõ hơn.',
                'hardware':'unknown','hardware_label':'CỤC BỘ · CHƯA KIỂM TRA CPU/GPU','ffmpeg':bool(shutil.which('ffmpeg')),
                'cpu_cores':os.cpu_count() or 1,'nano_ready':False,'worker_warm':warm_worker is not None and warm_worker.poll() is None}
    return {'variant':'standard','app_name':APP_NAME,'default_language':'vi','subtitle_ready':(DATA/'models'/'whisper-base'/'model.bin').is_file(),'version':app.version,'mode': 'local', 'languages': LANGUAGES,'subtitle_languages':SUBTITLE_LANGUAGES,'ai_voice_languages':list(CORE_LANGUAGES), 'max_characters': MAX_CHARACTERS, 'max_audio_minutes': 180, 'fast_vieneu': supports_int8() and (DATA / 'models' / 'vieneu_fast.ready').exists(), 'int8_cpu': supports_int8(), 'models': {name: (DATA / 'models' / f'{name}.ready').exists() for name in ('vieneu', 'qwen', 'qwen_clone')}, 'hardware': 'GPU' if shutil.which('nvidia-smi') else 'CPU', 'ffmpeg': bool(shutil.which('ffmpeg')), 'cpu_cores': os.cpu_count() or 1, 'nano_ready': (DATA / 'models' / 'vieneu_nano.ready').exists(), 'worker_warm': warm_worker is not None and warm_worker.poll() is None}


@app.get('/api/voices')
def voices():
    entries=PRESETS+(installed_voices() if not IS_HMONG else [])+records('voices')
    entries=[{**voice,'engine':voice.get('engine','vieneu' if voice.get('languages',['vi'])[0]=='vi' else 'qwen_clone')} for voice in entries]
    return {'voices':[{**voice,'native_language':native_language(voice),'ready':model_ready(voice.get('engine','vieneu'))} for voice in entries]}



@app.post('/api/voices/clone', status_code=201)
async def clone(name: str = Form(min_length=1, max_length=80), language: str = Form(DEFAULT_LANGUAGE), transcript: str = Form('', max_length=2000), consent: bool = Form(False), reference_start: float | None = Form(None), reference_end: float | None = Form(None), file: UploadFile = File(...)):
    ident = uuid.uuid4().hex
    target = DATA / 'voices' / f'{ident}.wav'
    source = DATA / 'voices' / f'{ident}.upload'
    decoded = DATA / 'voices' / f'{ident}.decoded.wav'
    try:
        if not consent:
            raise HTTPException(422, 'Cần xác nhận quyền sử dụng mẫu giọng.')
        if language not in CORE_LANGUAGES:raise HTTPException(422,'Nhân bản AI chưa hỗ trợ ngôn ngữ này. Chọn giọng hệ thống Windows đã cài cho ngôn ngữ đó.')
        if not name.strip() or language not in LANGUAGES:
            raise HTTPException(422, 'Tên hoặc ngôn ngữ không hợp lệ.')
        if Path(file.filename or '').suffix.lower() not in {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm'}:
            raise HTTPException(422, 'Chọn tệp MP3, WAV, M4A, FLAC, OGG hoặc WEBM.')
        content = await file.read(20 * 1024 * 1024 + 1)
        if not content or len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, 'Mẫu phải có dữ liệu và không vượt quá 20 MB.')
        source.write_bytes(content)
        selection = None
        if IS_HMONG:
            from hmong_reference import decode_upload, select_reference, crop_reference, ReferenceError
            from hmong_text import normalize_text, HmongTextError
            try:
                transcript = normalize_text(transcript)
                source_duration = await run_in_threadpool(decode_upload, source, decoded)
                selection = select_reference(content, source_duration, transcript, reference_start, reference_end)
                selection['transcript'] = normalize_text(selection['transcript'])
                duration = await run_in_threadpool(crop_reference, decoded, target,
                                                   selection['reference_start'], selection['reference_end'])
                transcript = selection['transcript']
            except (ReferenceError, HmongTextError) as exc:
                raise HTTPException(422, str(exc)) from None
        else:
            # Decode only local audio; prohibit FFmpeg from following network playlists.
            result = await run_in_threadpool(subprocess.run, ['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', str(source), '-t', '31', '-vn', '-ac', '1', '-ar', '24000', '-y', str(target)], capture_output=True, timeout=45, check=False)
            if result.returncode or not target.exists():
                raise HTTPException(422, 'Không đọc được âm thanh. Hãy dùng bản thu WAV/MP3 rõ tiếng.')
            import wave
            with wave.open(str(target)) as audio:
                duration = audio.getnframes() / audio.getframerate()
        if not 3 <= duration <= 30:
            raise HTTPException(422, 'Dùng mẫu dài từ 3 đến 30 giây. Nên thu một người nói, ít tạp âm, không nhạc nền.')
        import numpy as np
        import soundfile as sf
        samples, _ = sf.read(str(target), dtype='float32')
        if not np.all(np.isfinite(samples)) or not np.any(np.abs(samples) > 0.0001):
            raise HTTPException(422, 'Mẫu giọng chỉ có im lặng hoặc âm thanh không hợp lệ. Hãy thu lại lời nói rõ tiếng.')
        record = {'id': ident, 'name': name.strip(), 'category': 'cloned', 'languages': [language], 'language': language, 'transcript': transcript.strip(), 'description': f'Mẫu giọng cá nhân · {duration:.1f}s', 'duration': duration, 'consent_at': now(), 'created_at': now()}
        if IS_HMONG:
            record.update(engine='f5_hmong', **selection)
        write_json(DATA / 'voices' / f'{ident}.json', record)
        return record
    except (subprocess.TimeoutExpired, FileNotFoundError):
        raise HTTPException(503, 'Cần FFmpeg hoạt động để nhập mẫu âm thanh.') from None
    finally:
        source.unlink(missing_ok=True)
        decoded.unlink(missing_ok=True)
        if not (DATA / 'voices' / f'{ident}.json').exists():
            target.unlink(missing_ok=True)
        await file.close()


@app.post('/api/hmong/reference-info')
async def hmong_reference_info(file: UploadFile = File(...)):
    if not IS_HMONG:
        await file.close()
        raise HTTPException(404, 'Chức năng chọn đoạn mẫu chỉ có trong bản Hmong.')
    import tempfile
    from hmong_reference import MAX_UPLOAD_BYTES, validate_upload, decode_upload, describe_reference, ReferenceError
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, 'Mẫu không được vượt quá 20 MB.')
        validate_upload(file.filename, content)
        with tempfile.TemporaryDirectory(prefix='reference-info-', dir=DATA / 'parts') as folder:
            source, decoded = Path(folder) / 'source.upload', Path(folder) / 'decoded.wav'
            source.write_bytes(content)
            duration = await run_in_threadpool(decode_upload, source, decoded)
            return describe_reference(content, duration)
    except ReferenceError as exc:
        raise HTTPException(422, str(exc)) from None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        raise HTTPException(503, 'Cần FFmpeg hoạt động để kiểm tra mẫu âm thanh.') from None
    finally:
        await file.close()


@app.get('/api/voices/{ident}/sample')
def voice_sample(ident: str):
    valid_id(ident)
    path = DATA / 'voices' / f'{ident}.wav'
    if not path.exists():
        raise HTTPException(404, 'Không tìm thấy mẫu giọng.')
    return FileResponse(path, media_type='audio/wav')


@app.delete('/api/voices/{ident}', status_code=204)
def delete_voice(ident: str):
    valid_id(ident)
    with lock:
        if any(j['status'] in {'queued', 'running', 'cancelling'} and j.get('voice_id') == ident for j in records('jobs')):
            raise HTTPException(409, 'Giọng đang được dùng trong hàng đợi. Đợi tác vụ hoàn tất trước khi xóa.')
        for suffix in ('.json', '.wav'):
            (DATA / 'voices' / f'{ident}{suffix}').unlink(missing_ok=True)


class Speech(BaseModel):
    max_cue_tempo: float = Field(default=1.5,ge=1,le=2)
    cue_fit: str = Field(default='strict',pattern='^(strict|gap)$')
    timeline_seconds: float = Field(default=10800,gt=0,le=10800)
    caption_style: dict = Field(default_factory=dict)
    text: str = Field(min_length=1, max_length=MAX_CHARACTERS)
    voice_id: str = Field(min_length=1, max_length=128)
    language: str = DEFAULT_LANGUAGE
    speed: float = Field(default=1, ge=0.7, le=1.4)
    format: str = 'wav'
    input_format: str = Field(default='txt', pattern='^(txt|srt)$')
    skip_timestamps: bool = True
    video_id: str | None = None
    video_offset: float = Field(default=0, ge=0, le=10800)
    video_mix: bool = False
    caption_cues: list[dict] = Field(default_factory=list,max_length=10000)
    export_resolution: str = Field(default='original',pattern='^(original|720p|1080p|2160p)$')
    export_quality: str = Field(default='balanced',pattern='^(best|balanced|fast)$')
    logos: list[dict] = Field(default_factory=list,max_length=20)
    logo: dict[str, int] | None = None
    hmong_steps: int = Field(default=16, ge=4, le=32)
    nano_threads: int = Field(default=2, ge=1, le=8)
    nano_parallel: int = Field(default=1, ge=1, le=4)
    nano_steps: int = Field(default=8, ge=4, le=16)
    max_minutes: int = Field(default=180, ge=1, le=180)
    delivery: str = 'natural'
    paragraph_pause: float = Field(default=0 if IS_HMONG else 0.3, ge=0, le=3)
    quality: str = Field(default='auto', pattern='^(auto|standard|fast)$')


def stop_worker(process, force=False):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        # Kill FFmpeg descendants too; keep chunk checkpoints on disk.
        try:
            stopped = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
            if stopped.returncode and process.poll() is None:
                process.kill()
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:
            pass


def close_warm_worker():
    global warm_worker
    process, warm_worker = warm_worker, None
    if process is not None:
        stop_worker(process, force=True)
        process.wait()
        if process.stdin:
            process.stdin.close()


def execute_worker(path, env, work):
    global warm_worker
    # Keep one model process resident for consecutive jobs; cancellation kills it.
    done = work / 'worker-done.json'
    done.unlink(missing_ok=True)
    if warm_worker is None or warm_worker.poll() is not None:
        close_warm_worker()
        with (DATA / 'worker-startup.log').open('a', encoding='utf-8') as errors:
            warm_worker = subprocess.Popen([sys.executable, str(BASE / 'worker.py'), '--serve'], env=env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors, text=True, encoding='utf-8', **({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}))
    process = warm_worker
    try:
        process.stdin.write(str(path.resolve()) + '\n')
        process.stdin.flush()
        started = time.monotonic()
        while True:
            if (work / 'cancel.flag').exists() or shutdown_event.is_set():
                close_warm_worker()
                return -2
            if done.exists():
                return read_json(done)['code']
            if process.poll() is not None:
                close_warm_worker()
                return 1
            if time.monotonic() - started > 7 * 86400:
                raise TimeoutError('Tác vụ vượt giới hạn xử lý 7 ngày. Có thể tiếp tục từ các đoạn đã tạo.')
            time.sleep(0.1)
    except BaseException:
        close_warm_worker()
        raise


def run_job(ident):
    path = DATA / 'jobs' / f'{ident}.json'
    work = DATA / 'parts' / ident
    work.mkdir(parents=True, exist_ok=True)
    with lock:
        job = read_json(path)
        if job['status'] != 'queued' or (work / 'cancel.flag').exists():
            return
        job['status'] = 'running'
        job['started_at'] = now()
        processing_started = time.monotonic()
        reused_parts = any(work.glob("[0-9]*.wav"))
        write_json(path, job)
    try:
        env = dict(os.environ, VOICE_STUDIO_DATA_DIR=str(DATA), HF_HOME=str(DATA / 'models' / 'cache'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS=os.environ.get('VOICE_STUDIO_THREADS', '4'), PYTHONUTF8='1')
        code = execute_worker(path, env, work)
        if code == -2 or (work / 'cancel.flag').exists():
            job.update(status='cancelled', error='Đã dừng. Bạn có thể tiếp tục từ các đoạn đã tạo.')
        elif code:
            marker = work / 'worker-done.json'
            if marker.exists():
                detail = read_json(marker).get('user_error')
                if detail:
                    raise RuntimeError(detail)
            raise RuntimeError('Không tạo được âm thanh. Kiểm tra nhật ký tác vụ; có thể bấm Tiếp tục để giữ các đoạn đã tạo.')
        else:
            output = DATA / 'audio' / f"{ident}.{job['format']}"
            if not output.exists() or output.stat().st_size < 100:
                raise RuntimeError('Mô hình không tạo ra âm thanh hợp lệ.')
            result = read_json(work / 'result.json')
            job.update(result)
            if job.get('video_id'):
                job['video_url'] = f'/api/dubbed/{ident}'
            elapsed = time.monotonic() - processing_started
            job.update(status='done', url=f'/api/audio/{ident}', finished_at=now(), wall_processing_seconds=round(elapsed, 3), speed_report=None if reused_parts else speed_report(result.get('audio_seconds', 0), elapsed))
    except Exception as exc:
        job.update(status='error', error=str(exc))
    with lock:
        write_json(path, job)


@app.post('/api/speech', status_code=202)
def speech(body: Speech):
    if IS_HMONG and (body.language != 'mww' or body.hmong_steps not in {4,8,16,32}):
        raise HTTPException(422, 'Bản Hmong chỉ đọc Hmong Trắng; chọn F5 4, 8, 16 hoặc 32 bước.')
    if not body.text.strip() or body.language not in LANGUAGES or body.format not in {'wav', 'mp3'} or body.delivery not in PROFILES:
        raise HTTPException(422, 'Kiểm tra nội dung, ngôn ngữ và định dạng xuất.')
    if body.video_id:
        meta = read_json(DATA / 'videos' / f'{valid_id(body.video_id)}.json')
        if body.logo or body.logos:
            from video_tasks import logo_filters
            meta.update(inspect_video(DATA/'videos'/f'{body.video_id}.source'))
            try:
                logo_filters(body.model_dump(),meta)
            except (ValueError,KeyError,TypeError) as exc:
                raise HTTPException(422,str(exc)) from None
        from video_editor import validate_style
        try:validate_style(body.caption_style)
        except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc)) from None
        if body.caption_cues:
            from video_editor import validate_cues
            try:
                validate_cues(body.caption_cues,meta['duration'])
            except (ValueError,TypeError,KeyError) as exc:
                raise HTTPException(422,str(exc)) from None
        if body.video_offset >= meta['duration']:
            raise HTTPException(422, 'Thời điểm bắt đầu phải nhỏ hơn thời lượng video.')
    voice = next((v for v in PRESETS + installed_voices() + records('voices') if v['id'] == body.voice_id), None)
    if not voice or body.language not in voice['languages']:
        raise HTTPException(422, 'Chọn giọng hỗ trợ ngôn ngữ này. Giọng cá nhân chỉ dùng với ngôn ngữ đã đăng ký.')
    engine = voice.get('engine', 'vieneu' if body.language == 'vi' else 'qwen_clone')
    try:
        segment_plan = ({'vieneu_nano':'nano-packed-v1','f5_hmong':'hmong-packed-v1'}.get(engine,'classic-v1')
                        if body.paragraph_pause == 0 else 'classic-v1')
        segments = plan_segments({**body.model_dump(), 'engine': engine, 'segment_plan': segment_plan})
        from narration import validate_voice_text
        for index,segment in enumerate(segments):
            if segment.text:validate_voice_text(segment.text,engine,f'Câu SRT {segment.cue+1}' if body.input_format=='srt' else f'Đoạn {index+1}')
        if body.input_format == 'srt':
            cues = parse_srt(body.text)
            if body.cue_fit=='gap' and cues[-1]['end']>body.timeline_seconds+.001:
                raise ValueError('Phụ đề vượt thời lượng video đã chọn.')
            if cues[-1]['end'] > body.max_minutes*60:
                raise ValueError('SRT vượt giới hạn thời lượng đã chọn.')
            if body.video_id and cues[-1]['end'] + body.video_offset > meta['duration'] + .001:
                raise ValueError('Mốc SRT cộng thời điểm bắt đầu vượt thời lượng video.')
        if not any(segment.text for segment in segments):
            raise ValueError('Nhập nội dung đọc, không chỉ ký hiệu nghỉ.')
        if engine == 'f5_hmong':
            if voice.get('speaker') in {'hmong-male','hmong-female'}:
                from hmong_assets import reference
                _, reference_text = reference(voice['speaker'])
            else:
                reference_text = voice.get('transcript','')
            validate_voice_text(reference_text,engine,'Lời mẫu tham chiếu')
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except OSError:
        raise HTTPException(422, 'Không đọc được mẫu giọng Hmong mặc định. '
                                  'Giải nén lại toàn bộ bản ZIP để khôi phục thư mục assets/hmong rồi tạo lại.') from None
    if not model_ready(engine):
        raise HTTPException(503, f'Mô hình {engine} chưa sẵn sàng. Bấm Tải model cho giọng đang chọn, chờ kiểm tra hoàn tất rồi tạo lại. Cần Internet ở bước tải.')
    if body.quality == 'auto':
        body.quality = ('standard' if engine == 'f5_hmong' else
                        'fast' if engine != 'vieneu' or (supports_int8() and (DATA / 'models' / 'vieneu_fast.ready').exists()) else 'standard')
    if body.quality == 'fast' and engine == 'vieneu':
        if not supports_int8() or not (DATA / 'models' / 'vieneu_fast.ready').exists():
            raise HTTPException(503, 'Chế độ nhanh tiếng Việt cần tải vieneu_fast trên CPU có VNNI. Dùng chế độ Tiêu chuẩn hoặc chạy prepare_models.py vieneu_fast.')
    with lock:
        if sum(j['status'] in {'queued', 'running', 'cancelling'} for j in records('jobs')) >= 4:
            raise HTTPException(429, 'Hàng đợi đã có 4 tác vụ. Hãy đợi trước khi tạo thêm.')
        ident = uuid.uuid4().hex
        job = {**body.model_dump(), 'text': body.text.strip(), 'id': ident, 'voice_name': voice['name'], 'engine': engine, 'speaker': voice.get('speaker'), 'status': 'queued', 'segment_plan': segment_plan, 'total': len(segments), 'completed': 0, 'progress': 0, 'created_at': now()}
        write_json(DATA / 'jobs' / f'{ident}.json', job)
        executor.submit(run_job, ident)
    return job


@app.get('/api/history')
def history():
    return {'items': [job_status(j) for j in sorted(records('jobs'), key=lambda x: x['created_at'], reverse=True)[:100]]}


@app.get('/api/jobs/{ident}')
def get_job(ident: str):
    return job_status(read_json(DATA / 'jobs' / f'{valid_id(ident)}.json'))


@app.get('/api/audio/{ident}')
def audio(ident: str):
    job = get_job(ident)
    if job['status'] != 'done':
        raise HTTPException(404, 'Bản thu chưa sẵn sàng.')
    path = DATA / 'audio' / f"{ident}.{job['format']}"
    if not path.exists():
        raise HTTPException(404, 'Không tìm thấy bản thu.')
    return FileResponse(path, media_type='audio/wav' if job['format'] == 'wav' else 'audio/mpeg', filename=f"voice-studio-{ident[:8]}.{job['format']}", content_disposition_type='inline')


@app.get('/api/jobs/{ident}/export.{extension}')
def export_voice(ident:str,extension:str):
    if extension not in {'wav','mp3','txt','srt'}:raise HTTPException(422,'Chọn WAV, MP3, TXT hoặc SRT.')
    ident=valid_id(ident)
    job=get_job(ident)
    if job['status']!='done':raise HTTPException(409,'Đợi voice hoàn tất trước khi xuất.')
    if extension in {'txt','srt'}:
        from fastapi.responses import Response
        timing=DATA/'audio'/f'{ident}.srt'
        if not timing.is_file():raise HTTPException(404,'Chưa có mốc lời đọc.')
        text=timing.read_text(encoding='utf-8')
        if extension=='txt':text='\n\n'.join(c['text'] for c in parse_srt(text))+'\n'
        return Response(text,media_type='text/plain; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="voice-studio.{extension}"'})
    source=DATA/'audio'/f'{ident}.wav'
    if not source.is_file():source=DATA/'audio'/f"{ident}.{job['format']}"
    if not source.is_file():raise HTTPException(404,'Không tìm thấy bản thu. Tạo lại voice trước khi xuất.')
    target=DATA/'audio'/f'{ident}.{extension}'
    if not target.is_file():
        temporary=DATA/'audio'/f'{ident}-{uuid.uuid4().hex}.{extension}'
        try:
            subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(source),'-vn','-codec:a','libmp3lame' if extension=='mp3' else 'pcm_s16le',*(['-b:a','192k'] if extension=='mp3' else []),'-y',str(temporary)],check=True,timeout=600,capture_output=True)
            temporary.replace(target)
        except (OSError,subprocess.SubprocessError):raise HTTPException(500,'Chưa chuyển được âm thanh. Kiểm tra FFmpeg và dung lượng trống.') from None
        finally:temporary.unlink(missing_ok=True)
    return FileResponse(target,media_type='audio/mpeg' if extension=='mp3' else 'audio/wav',filename=f'voice-studio.{extension}')


class TranslationCheck(BaseModel):
    provider:str='ollama'
    model:str=Field(default='',max_length=100)


@app.get('/api/translation/models')
async def available_translation_models(provider:str='ollama'):
    return {'provider':provider,'models':await writing.translation_models(provider)}


@app.post('/api/translation/check')
async def check_translation(body:TranslationCheck):
    return await writing.check_translation_model(body.provider,body.model)


@app.delete('/api/history/{ident}', status_code=204)
def delete_record(ident: str):
    with lock:
        job = get_job(ident)
        if job['status'] in {'queued', 'running', 'cancelling'}:
            raise HTTPException(409, 'Đợi tác vụ hoàn tất trước khi xóa.')
        shutil.rmtree(DATA / 'parts' / ident, ignore_errors=True)
        for path in [DATA / 'audio' / f'{ident}.wav', DATA / 'audio' / f'{ident}.mp3', DATA / 'audio' / f'{ident}.mp4', DATA / 'audio' / f'{ident}.srt', DATA / 'jobs' / f'{ident}.json', DATA / 'jobs' / f'{ident}.log']:
            path.unlink(missing_ok=True)


def job_status(job):
    if job.get('status') in {'running', 'cancelling', 'cancelled', 'error'}:
        path = DATA / 'parts' / job['id'] / 'progress.json'
        if path.exists():
            try:
                job.update(json.loads(path.read_text(encoding='utf-8')))
            except (OSError, ValueError):
                pass
    return job


@app.get('/api/jobs/{ident}/alignment')
def voice_alignment(ident:str):
    ident=valid_id(ident)
    read_json(DATA/'jobs'/f'{ident}.json')
    path=DATA/'parts'/ident/'alignment.json'
    return read_json(path) if path.is_file() else {'cues':[],'sync_ok':False,'pending':True}


@app.get('/api/jobs/{ident}/timing')
def voice_timing(ident:str):
    ident=valid_id(ident)
    job=read_json(DATA/'jobs'/f'{ident}.json')
    if job['status']!='done':raise HTTPException(409,'Voice chưa hoàn tất.')
    path=DATA/'audio'/f'{ident}.srt'
    if not path.is_file():raise HTTPException(404,'Chưa có mốc lời đọc.')
    return {'cues':parse_srt(path.read_text(encoding='utf-8'))}


@app.post('/api/jobs/{ident}/cancel', status_code=202)
def cancel_job(ident: str):
    with lock:
        job = get_job(ident)
        if job['status'] not in {'queued', 'running', 'cancelling'}:
            raise HTTPException(409, 'Tác vụ không đang chạy.')
        work = DATA / 'parts' / ident
        work.mkdir(parents=True, exist_ok=True)
        (work / 'cancel.flag').touch()
        job['status'] = 'cancelled' if job['status'] == 'queued' else 'cancelling'
        write_json(DATA / 'jobs' / f'{ident}.json', job)
        return job


@app.post('/api/jobs/{ident}/resume', status_code=202)
def resume_job(ident: str):
    with lock:
        job = get_job(ident)
        if job['status'] not in {'cancelled', 'error'}:
            raise HTTPException(409, 'Chỉ tiếp tục tác vụ đã dừng hoặc có lỗi.')
        if sum(j['status'] in {'queued', 'running', 'cancelling'} for j in records('jobs')) >= 4:
            raise HTTPException(429, 'Hàng đợi đã đầy.')
        if not job.get('speaker') and not (DATA / 'voices' / f"{job['voice_id']}.json").exists():
            raise HTTPException(409, 'Mẫu giọng đã bị xóa; không thể tiếp tục tác vụ này.')
        (DATA / 'parts' / ident / 'cancel.flag').unlink(missing_ok=True)
        job.update(status='queued')
        job.pop('error', None)
        write_json(DATA / 'jobs' / f'{ident}.json', job)
        executor.submit(run_job, ident)
        return job


@app.get('/api/writing/connections')
async def writing_connections():
    providers = {provider: bool(writing.get_key(provider)) for provider in writing.ENV_KEYS}
    try:
        local = await writing.local_status()
    except HTTPException as error:
        local = {'connected': False, 'models': [], 'requires_key': False, 'message': error.detail}
    providers['ollama'] = local['connected']
    return {'providers': providers, 'local': local, 'defaults': writing.DEFAULT_MODELS}


@app.post('/api/writing/connect')
async def connect_writing(body: writing.Connection):
    return await writing.verify_connection(body)


@app.delete('/api/writing/connections/{provider}', status_code=204)
def disconnect_writing(provider: str):
    if provider not in writing.ENV_KEYS:
        raise HTTPException(422, 'Nhà cung cấp không hợp lệ.')
    with writing.KEY_LOCK:
        writing.KEYS.pop(provider, None)
    if any(os.environ.get(key) for key in writing.ENV_KEYS[provider]):
        raise HTTPException(409, 'Khóa từ biến môi trường vẫn được cấu hình. Xóa biến môi trường rồi khởi động lại để ngắt hoàn toàn.')


@app.post('/api/writing/generate')
async def write_script(body: writing.WritingRequest):
    if body.language not in LANGUAGES:
        raise HTTPException(422, 'Ngôn ngữ chưa được hỗ trợ.')
    return await writing.generate(body)


@app.get('/api/system-info')
def machine_info():
    return system_info()


@app.post('/api/videos', status_code=201)
async def upload_video(file: UploadFile = File(...)):
    folder = DATA / 'videos'
    folder.mkdir(exist_ok=True)
    ident = uuid.uuid4().hex
    source = folder / (ident + '.source')
    saved = False
    try:
        count = 0
        with source.open('wb') as target:
            while chunk := await file.read(1024 * 1024):
                count += len(chunk)
                if count > 2 * 1024**3:
                    raise HTTPException(413, 'Video tối đa 2 GB.')
                await run_in_threadpool(target.write, chunk)
        info = await run_in_threadpool(inspect_video, source)
        record = {**info, 'id': ident, 'name': Path(file.filename or 'video').name[:200], 'size': count}
        write_json(folder / (ident + '.json'), record)
        saved = True
        return record
    except (ValueError, subprocess.CalledProcessError):
        raise HTTPException(422, 'Video hỏng, codec chưa hỗ trợ hoặc dài quá 3 giờ. Dùng video H.264/MP4 hợp lệ.') from None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise HTTPException(503, 'Không kiểm tra được video. Cần FFmpeg và FFprobe hoạt động.') from None
    finally:
        await file.close()
        if not saved:
            source.unlink(missing_ok=True)


@app.delete('/api/videos/{ident}', status_code=204)
def delete_video(ident: str):
    ident = valid_id(ident)
    with lock:
        active_tasks = [read_json(p) for p in (DATA/'video_tasks').glob('*/job.json')]
        if any(j.get('video_id') == ident and j.get('status') in {'queued','running'} for j in active_tasks):
            raise HTTPException(409,'Dừng tác vụ video trước khi xóa nguồn.')
        if any(j.get('video_id') == ident for j in records('jobs')):
            raise HTTPException(409, 'Xóa các tác vụ dùng video này trong Lịch sử trước khi xóa video gốc.')
        (DATA/'editor'/f'{ident}.json').unlink(missing_ok=True)
        shutil.rmtree(DATA/'asr_cache'/ident,ignore_errors=True)
        for suffix in ('.source', '.json', '.jpg'):
            (DATA / 'videos' / (ident + suffix)).unlink(missing_ok=True)


@app.get('/api/dubbed/{ident}')
def dubbed_video(ident: str):
    job = get_job(ident)
    path = DATA / 'audio' / (ident + '.mp4')
    if job['status'] != 'done' or not job.get('video_id') or not path.exists():
        raise HTTPException(404, 'Video lồng tiếng chưa sẵn sàng.')
    return FileResponse(path, media_type='video/mp4', filename=f'voice-studio-{ident[:8]}.mp4')


@app.get('/api/videos')
def list_videos():
    return {'items': records('videos')}


@app.get('/api/jobs/{ident}/script.{extension}')
def download_script(ident: str, extension: str):
    from fastapi.responses import Response
    job = get_job(ident)
    if extension not in ('txt', 'srt'):
        raise HTTPException(404, 'Chỉ hỗ trợ TXT và SRT.')
    if extension == 'txt':
        text = '\n'.join(c['text'] for c in parse_srt(job['text'])) if job.get('input_format') == 'srt' else job['text']
    elif job.get('input_format') == 'srt':
        text = export_srt(parse_srt(job['text']), job.get('video_offset', 0) if job.get('video_id') else 0)
    else:
        path = DATA / 'audio' / (ident + '.srt')
        if job['status'] != 'done' or not path.exists():
            raise HTTPException(409, 'SRT từ TXT cần tạo giọng hoàn tất để lấy mốc thời gian thật.')
        text = path.read_text(encoding='utf-8')
    return Response(text, media_type='text/plain; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="voice-studio-{ident[:8]}.{extension}"'})


class ScriptConversion(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARACTERS)
    input_format: str = Field(pattern='^(txt|srt)$')
    output_format: str = Field(pattern='^(txt|srt)$')


@app.post('/api/scripts/convert')
def convert_script(body: ScriptConversion):
    try:
        cues = parse_srt(body.text) if body.input_format == 'srt' else None
        if body.output_format == 'srt' and cues is None:
            raise ValueError('Tạo voice hoàn tất rồi xuất SRT để có mốc thời gian thật.')
        text = (export_srt(cues) if body.output_format == 'srt' else '\n'.join(c['text'] for c in cues)) if cues else body.text
        return {'text': text}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

# Video tools share the speech queue so CPU-heavy models never compete.
class EditorCue(BaseModel):
    start: float = Field(ge=0,le=10800)
    end: float = Field(gt=0,le=10800)
    text: str = Field(min_length=1,max_length=4000)


class EditorProject(BaseModel):
    language:str=Field(default='',max_length=16)
    caption_style: dict = Field(default_factory=dict)
    cues: list[EditorCue] = Field(default_factory=list,max_length=10000)


class VideoTask(BaseModel):
    voice_job_id: str | None = None
    caption_style: dict = Field(default_factory=dict)
    export_resolution: str = Field(default='original',pattern='^(original|720p|1080p|2160p)$')
    export_quality: str = Field(default='balanced',pattern='^(best|balanced|fast)$')
    logos: list[dict] = Field(default_factory=list,max_length=20)
    video_id: str | None = None
    action: str = Field(pattern='^(subtitles|logo|render|export|preview|translate_text|prepare_voice)$')
    preview_start: float = Field(default=0,ge=0,le=10800)
    preview_seconds: float = Field(default=10,ge=1,le=15)
    preview_voice_id: str | None = None
    engine: str = Field(default='qwen',pattern='^(qwen|qwen_clone|vieneu|vieneu_nano|f5_hmong)$')
    text: str = Field(default='',max_length=200000)
    input_format: str = Field(default='txt',pattern='^(txt|srt)$')
    provider: str = Field(default='ollama',pattern='^(ollama|openai|gemini)$')
    cues: list[EditorCue] = Field(default_factory=list,max_length=10000)
    accurate: bool = True
    source_language: str = Field(default='',max_length=16)
    target_language: str = Field(default='', max_length=16)
    model: str = Field(default='qwen3:4b', max_length=100)
    srt: str = Field(default='', max_length=200000)
    logo: dict[str, int] | None = None


def video_task_work(ident):
    return DATA / 'video_tasks' / valid_id(ident)


def run_video_task(ident):
    work = video_task_work(ident)
    path = work/'job.json'
    job = read_json(path)
    process = None
    try:
        if (work/'cancel.flag').exists():
            job['status'] = 'cancelled'
            return
        # Keep TTS warm for cloud translation and export when memory permits.
        available=0
        try:
            import psutil
            available=psutil.virtual_memory().available/1024**3
        except ImportError:
            pass
        asr=job['action']=='subtitles' and not job.get('srt')
        if job['action']=='prepare_voice' or (job.get('target_language') and job.get('provider','ollama')=='ollama') or available<(4 if asr else 2):
            close_warm_worker()
        job['status'] = 'running'
        write_json(path,job)
        worker_env=dict(os.environ)
        if job.get('target_language') and job.get('provider','ollama')!='ollama':
            provider=job['provider'];key=writing.get_key(provider)
            if not key:raise ValueError('Chưa kết nối API key cho dịch vụ dịch đã chọn.')
            worker_env[writing.ENV_KEYS[provider][0]]=key
        with (work/'worker.log').open('wb') as log:
            process = subprocess.Popen([sys.executable,str(BASE/'video_tasks.py'),str(path)],stdout=log,stderr=log,env=worker_env,
                **({'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}))
            while process.poll() is None:
                if shutdown_event.is_set() or (work/'cancel.flag').exists():
                    stop_worker(process, force=True)
                    job['status']='cancelled'
                    return
                time.sleep(.15)
        if process.returncode:
            raise ValueError((work/'error.txt').read_text(encoding='utf-8') if (work/'error.txt').exists() else 'Không xử lý được video. Kiểm tra model phụ đề và FFmpeg.')
        job['status']='done'
    except Exception as exc:
        job.update(status='error',error=str(exc))
    finally:
        if process and process.poll() is None:
            stop_worker(process,force=True)
        if job.get('target_language') and job.get('provider','ollama')=='ollama':
            try:
                import httpx
                httpx.post('http://127.0.0.1:11434/api/generate',json={'model':job.get('model') or writing.DEFAULT_MODELS['ollama'],'keep_alive':0},timeout=2,trust_env=False)
            except Exception:
                pass
        write_json(path,job)


@app.post('/api/video-tasks',status_code=202)
def create_video_task(body:VideoTask):
    if body.action not in {'translate_text','prepare_voice'} and not body.video_id:raise HTTPException(422,'Chọn video trước.')
    meta = read_json(DATA/'videos'/f'{valid_id(body.video_id)}.json') if body.action not in {'translate_text','prepare_voice'} else {'duration':10800}
    try:
        if body.source_language and body.source_language!='auto' and body.source_language not in LANGUAGES and body.source_language.split('-')[0] not in RECOGNITION_CODES:
            raise ValueError('Ngôn ngữ gốc chưa được hỗ trợ.')
        if body.action=='subtitles' and not body.srt and (IS_HMONG or body.source_language=='mww'):
            raise ValueError('Chưa có nhận dạng lời nói Hmong trong bản này. Nhập TXT/SRT hoặc sửa lời Hmong thủ công để tạo giọng.')
        if body.action=='translate_text':
            if not body.text.strip() or body.target_language not in LANGUAGES:raise ValueError('Nhập văn bản và chọn ngôn ngữ dịch.')
            if body.input_format=='srt':parse_srt(body.text)
        if body.action=='subtitles' and not body.srt and not (DATA/'models'/'whisper-base'/'model.bin').is_file():
            raise HTTPException(503,'Model nhận dạng chưa sẵn sàng. Dùng bản Portable có sẵn Whisper hoặc chạy download_subtitle_model.bat.')
        if body.target_language and body.provider!='ollama' and not writing.get_key(body.provider):
            raise HTTPException(503,'Chưa kết nối API key. Mở phần kết nối dịch và chọn OpenAI hoặc Gemini.')
        from video_editor import validate_style
        validate_style(body.caption_style)
        if body.voice_job_id:
            if body.action not in {'render','export','preview'}:raise ValueError('Voice đã tạo chỉ dùng khi xuất video.')
            voice=read_json(DATA/'jobs'/f'{valid_id(body.voice_job_id)}.json')
            if voice['status']!='done' or voice['format']!='wav' or voice.get('duration_limited'):raise ValueError('Voice chưa hoàn tất hoặc đã chạm giới hạn.')
            if voice.get('audio_seconds',0)>meta['duration']+.05:raise ValueError('Voice dài hơn video. Sửa lời hoặc mốc câu trước khi xuất.')
        if body.action=='preview':
            if body.preview_start>=meta['duration']:raise ValueError('Mốc xem thử cần nằm trong video.')
            if body.preview_voice_id:
                voice=read_json(DATA/'jobs'/f'{valid_id(body.preview_voice_id)}.json')
                if voice['status']!='done' or voice['format']!='wav':raise ValueError('Voice xem thử chưa hoàn tất.')
        if body.action=='render' or (body.action=='preview' and body.cues):
            from video_editor import validate_cues
            validate_cues([c.model_dump() for c in body.cues],meta['duration'])
        if body.action in {'translate_text','prepare_voice'} and (body.logo or body.logos):raise ValueError('Tác vụ này không dùng vùng logo.')
        if body.logo or body.logos or body.action=='logo':
            from video_tasks import logo_filters
            meta.update(inspect_video(DATA/'videos'/f'{body.video_id}.source'))
            if not logo_filters(body.model_dump(),meta):
                raise ValueError('Chọn vùng logo trước.')
        if body.srt:
            cues=parse_srt(body.srt)
            if cues[-1]['end']>meta['duration']:
                raise ValueError('SRT dài hơn video.')
        if body.target_language and body.target_language not in LANGUAGES:
            raise ValueError('Ngôn ngữ dịch không hợp lệ.')
    except (ValueError,KeyError,TypeError) as exc:
        raise HTTPException(422,str(exc)) from None
    ident=uuid.uuid4().hex
    work=video_task_work(ident)
    work.mkdir(parents=True)
    job={**body.model_dump(),'id':ident,'status':'queued'}
    write_json(work/'job.json',job)
    executor.submit(run_video_task,ident)
    return {'id':ident,'status':'queued'}


@app.get('/api/video-tasks/{ident}')
def video_task_status(ident:str):
    work=video_task_work(ident)
    job=read_json(work/'job.json')
    state={'progress':0,'phase':'Đang chờ',**read_progress(work/'progress.json')}
    if job['status']=='done':state.update(progress=100,phase='Hoàn tất')
    result={'video_id':job['video_id'],'id':ident,'status':job['status'],'error':job.get('error'),**state}
    if job['status']=='done':
        if job['action']=='prepare_voice':
            result['prepared_engine']=job['engine']
        elif job['action']=='translate_text':
            result['text']=(work/'translated.txt').read_text(encoding='utf-8')
            result['input_format']=job.get('input_format','txt')
            result['target_language']=job['target_language']
        elif job['action']=='subtitles':
            result['srt']=(work/'output.srt').read_text(encoding='utf-8')
            result['cues']=parse_srt(result['srt'])
            if (work/'result.json').exists():result.update(read_json(work/'result.json'))
        else:
            result['video_url']=f'/api/video-tasks/{ident}/output.mp4'
            if (work/'result.json').exists():
                result.update(read_json(work/'result.json'))
    if job['status']=='error' and (work/'original.srt').exists():
        result['original_srt']=(work/'original.srt').read_text(encoding='utf-8')
        result['original_cues']=parse_srt(result['original_srt'])
        result['original_language']=read_json(work/'recognition.json').get('language','') if (work/'recognition.json').exists() else job.get('source_language','')
    return result


@app.post('/api/video-tasks/{ident}/cancel')
def stop_video_task(ident:str):
    work=video_task_work(ident)
    read_json(work/'job.json')
    (work/'cancel.flag').touch()
    return {'status':'cancelling'}


@app.get('/api/video-tasks/{ident}/{filename}')
def video_task_download(ident:str,filename:str):
    if filename not in {'output.mp4','output.srt','output.txt','original.srt'}:
        raise HTTPException(404,'Không tìm thấy tệp.')
    work=video_task_work(ident)
    if not (work/filename).is_file():
        raise HTTPException(404,'Tệp chưa sẵn sàng.')
    return FileResponse(work/filename,filename=filename)


@app.get('/api/videos/{ident}/frame')
def video_frame(ident:str,at:float=Query(default=0,ge=0,le=10800)):
    from fastapi.responses import Response
    import tempfile
    ident=valid_id(ident)
    meta=read_json(DATA/'videos'/f'{ident}.json')
    source=DATA/'videos'/f'{ident}.source'
    with tempfile.TemporaryDirectory(dir=DATA/'parts') as folder:
        output=Path(folder)/'frame.jpg'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',str(min(at,max(0,meta['duration']-.1))),'-protocol_whitelist','file,pipe','-i',str(source),'-frames:v','1','-y',str(output)],check=True,timeout=30)
        return Response(output.read_bytes(),media_type='image/jpeg')


@app.get('/api/videos/{ident}/source')
def editor_source(ident:str):
    ident=valid_id(ident)
    meta=read_json(DATA/'videos'/f'{ident}.json')
    return FileResponse(DATA/'videos'/f'{ident}.source',media_type='video/mp4' if meta['codec']!='vp9' else 'video/webm')


@app.get('/api/videos/{ident}/editor')
def get_editor(ident:str):
    ident=valid_id(ident)
    read_json(DATA/'videos'/f'{ident}.json')
    path=DATA/'editor'/f'{ident}.json'
    return read_json(path) if path.exists() else {'cues':[]}


@app.put('/api/videos/{ident}/editor')
def save_editor(ident:str,body:EditorProject):
    from video_editor import validate_cues
    ident=valid_id(ident)
    meta=read_json(DATA/'videos'/f'{ident}.json')
    try:
        from video_editor import validate_style
        if body.language and body.language!='auto' and body.language not in LANGUAGES and body.language.split('-')[0] not in RECOGNITION_CODES:raise ValueError('Ngôn ngữ phụ đề không hợp lệ.')
        style=validate_style(body.caption_style)
        cues=validate_cues([c.model_dump() for c in body.cues],meta['duration']) if body.cues else []
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None
    folder=DATA/'editor';folder.mkdir(exist_ok=True)
    with lock:
        write_json(folder/f'{ident}.json',{'cues':cues,'caption_style':style,'language':body.language})
    return {'cues':cues,'caption_style':style,'language':body.language}


@app.get('/api/videos/{ident}/editor/export.{extension}')
def export_editor(ident:str,extension:str):
    from fastapi.responses import Response
    from video_editor import validate_cues
    if extension not in {'txt','srt','timed-txt'}:
        raise HTTPException(404,'Chỉ hỗ trợ TXT và SRT.')
    ident=valid_id(ident)
    meta=read_json(DATA/'videos'/f'{ident}.json')
    project=read_json(DATA/'editor'/f'{ident}.json')
    try:
        cues=validate_cues(project['cues'],meta['duration'])
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None
    text=export_srt(cues) if extension=='srt' else '\n'.join(c['text'] for c in cues)
    if extension=='timed-txt':
        from subtitles import minute_timestamp
        text='\n\n'.join(f"{minute_timestamp(c['start'])} --> {minute_timestamp(c['end'])}\n{c['text']}" for c in cues)
        extension='timed.txt'
    return Response(text,media_type='text/plain; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="subtitles-{ident[:8]}.{extension}"'})


@app.post('/api/voices/refresh')
def refresh_installed_voices():
    clear=getattr(installed_voices,'cache_clear',None)
    if clear:clear()
    return voices()


@app.get('/api/hmong/presets/{ident}/sample')
def hmong_preset_sample(ident: str):
    if not IS_HMONG:
        raise HTTPException(404)
    from hmong_assets import source
    try:path=source(ident)
    except (ValueError,OSError):raise HTTPException(404,'Không tìm thấy mẫu Hmong.') from None
    return FileResponse(path,media_type='audio/mpeg')
