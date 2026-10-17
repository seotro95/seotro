"""Standalone local voice studio: text, SRT, cloning and audio exports only."""
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

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from narration import MAX_CHARACTERS, PROFILES, plan_segments
from subtitles import parse_srt, export_srt
from system_voices import installed_voices
from hardware import supports_int8, system_info
from performance import speed_report
from nano_resources import resource_policy, resolve_nano_settings
from state_io import write_json_atomic, read_progress
from language_catalog import LANGUAGES, CORE_LANGUAGES, QWEN_LANGUAGES, native_language

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE / '.data'))).resolve()
for folder in ('voices', 'audio', 'jobs', 'models', 'parts'):
    (DATA / folder).mkdir(parents=True, exist_ok=True)

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


app = FastAPI(title='Voice Studio Riêng', version='1.1.0', lifespan=lifespan)
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
    return {
        'version': app.version,
        'mode': 'local',
        'edition': 'standalone-voice',
        'languages': LANGUAGES,
        'ai_voice_languages': list(CORE_LANGUAGES),
        'max_characters': MAX_CHARACTERS,
        'max_audio_minutes': 180,
        'fast_vieneu': supports_int8() and (DATA / 'models' / 'vieneu_fast.ready').exists(),
        'int8_cpu': supports_int8(),
        'models': {name: (DATA / 'models' / f'{name}.ready').exists() for name in ('vieneu', 'qwen', 'qwen_clone')},
        'hardware': 'GPU' if shutil.which('nvidia-smi') else 'CPU',
        'ffmpeg': bool(shutil.which('ffmpeg')),
        'cpu_cores': os.cpu_count() or 1,
        'nano_ready': (DATA / 'models' / 'vieneu_nano.ready').exists(),
        'nano_clone_ready': (DATA / 'models' / 'vieneu_nano_clone.ready').exists(),
        'acceleration': resource_policy(),
        'worker_warm': warm_worker is not None and warm_worker.poll() is None,
    }


@app.get('/api/voices')
def voices():
    entries=PRESETS+installed_voices()+records('voices')
    entries=[{**voice,'engine':voice.get('engine','vieneu' if voice.get('languages',['vi'])[0]=='vi' else 'qwen_clone')} for voice in entries]
    result = []
    for voice in entries:
        cloned = voice.get('category') == 'cloned'
        ready_engines = {
            'vieneu': (DATA / 'models' / 'vieneu.ready').exists(),
            'vieneu_nano': (DATA / 'models' / 'vieneu_nano_clone.ready').exists(),
            'qwen_clone': (DATA / 'models' / 'qwen_clone.ready').exists(),
        } if cloned else {}
        result.append({**voice, 'native_language': native_language(voice),
                       'ready': voice.get('engine') == 'system' or (DATA / 'models' / f"{voice.get('engine', 'vieneu')}.ready").exists(),
                       'ready_engines': ready_engines})
    return {'voices': result}


@app.post('/api/voices/clone', status_code=201)
async def clone(name: str = Form(min_length=1, max_length=80), language: str = Form('vi'), transcript: str = Form('', max_length=2000), consent: bool = Form(False), file: UploadFile = File(...)):
    ident = uuid.uuid4().hex
    target = DATA / 'voices' / f'{ident}.wav'
    source = DATA / 'voices' / f'{ident}.upload'
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
        # Decode only local audio; prohibit FFmpeg from following network playlists.
        result = await run_in_threadpool(subprocess.run, ['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', str(source), '-t', '31', '-vn', '-ac', '1', '-ar', '24000', '-y', str(target)], capture_output=True, timeout=45, check=False)
        if result.returncode or not target.exists():
            raise HTTPException(422, 'Không đọc được âm thanh. Hãy dùng bản thu WAV/MP3 rõ tiếng.')
        import wave
        with wave.open(str(target)) as audio:
            duration = audio.getnframes() / audio.getframerate()
        if not 3 <= duration <= 30:
            raise HTTPException(422, 'Dùng mẫu dài từ 3 đến 30 giây. Nên thu một người nói, ít tạp âm, không nhạc nền.')
        record = {'id': ident, 'name': name.strip(), 'category': 'cloned', 'languages': [language], 'language': language, 'transcript': transcript.strip(), 'description': f'Mẫu giọng cá nhân · {duration:.1f}s', 'duration': duration, 'consent_at': now(), 'created_at': now()}
        write_json(DATA / 'voices' / f'{ident}.json', record)
        return record
    except (subprocess.TimeoutExpired, FileNotFoundError):
        raise HTTPException(503, 'Cần FFmpeg hoạt động để nhập mẫu âm thanh.') from None
    finally:
        source.unlink(missing_ok=True)
        if not (DATA / 'voices' / f'{ident}.json').exists():
            target.unlink(missing_ok=True)
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
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=MAX_CHARACTERS)
    voice_id: str = Field(min_length=1, max_length=128)
    language: str = 'vi'
    speed: float = Field(default=1, ge=0.7, le=1.4)
    format: str = 'wav'
    input_format: str = Field(default='txt', pattern='^(txt|srt)$')
    skip_timestamps: bool = True
    nano_threads: int = Field(default=0, ge=0, le=8)
    nano_parallel: int = Field(default=0, ge=0, le=8)
    nano_steps: int = Field(default=8, ge=4, le=16)
    clone_engine: str = Field(default='auto', pattern='^(auto|standard|nano)$')
    max_minutes: int = Field(default=180, ge=1, le=180)
    delivery: str = 'natural'
    paragraph_pause: float = Field(default=0.3, ge=0, le=3)
    quality: str = Field(default='auto', pattern='^(auto|standard|fast)$')
    max_cue_tempo: float = Field(default=1.5, ge=1, le=2)
    cue_fit: str = Field(default='strict', pattern='^(strict|gap)$')
    timeline_seconds: float = Field(default=10800, gt=0, le=10800)


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
            elapsed = time.monotonic() - processing_started
            reused = reused_parts or result.get('reused_chunks', 0) > 0
            measured_audio = result.get('synthesized_audio_seconds', result.get('audio_seconds', 0))
            # SRT can compress cues after synthesis and insert timeline silence.
            # Throughput claims use continuous TXT output with no reused chunks.
            reportable = not reused and job.get('input_format', 'txt') == 'txt'
            job.update(status='done', url=f'/api/audio/{ident}', finished_at=now(), wall_processing_seconds=round(elapsed, 3), speed_report=speed_report(measured_audio, elapsed, complete=not result.get('duration_limited', False)) if reportable else None)
    except Exception as exc:
        job.update(status='error', error=str(exc))
    with lock:
        write_json(path, job)


@app.post('/api/speech', status_code=202)
def speech(body: Speech):
    return queue_speech(body)


def queue_speech(body: Speech, *, benchmark=False):
    if not body.text.strip() or body.language not in LANGUAGES or body.format not in {'wav', 'mp3'} or body.delivery not in PROFILES:
        raise HTTPException(422, 'Kiểm tra nội dung, ngôn ngữ và định dạng xuất.')
    voice = next((v for v in PRESETS + installed_voices() + records('voices') if v['id'] == body.voice_id), None)
    if not voice or body.language not in voice['languages']:
        raise HTTPException(422, 'Chọn giọng hỗ trợ ngôn ngữ này. Giọng cá nhân chỉ dùng với ngôn ngữ đã đăng ký.')
    engine = voice.get('engine', 'vieneu' if body.language == 'vi' else 'qwen_clone')
    cloned = voice.get('category') == 'cloned'
    if body.clone_engine == 'nano':
        if not cloned or body.language != 'vi':
            raise HTTPException(422, 'Nhân bản Nano chỉ dùng với mẫu giọng cá nhân tiếng Việt; giọng đang chọn được giữ nguyên.')
        engine = 'vieneu_nano'
    elif cloned and body.clone_engine == 'standard':
        engine = 'vieneu' if body.language == 'vi' else 'qwen_clone'
    marker = 'vieneu_nano_clone' if cloned and engine == 'vieneu_nano' else engine
    if engine != 'system' and not (DATA / 'models' / f'{marker}.ready').exists():
        if marker == 'vieneu_nano_clone':
            raise HTTPException(503, 'Chưa có mô hình nhân bản Nano. Chạy TAI_GIONG_NHAN_BAN_NHANH.bat rồi kiểm tra lại giọng.')
        raise HTTPException(503, f'Mô hình {engine} chưa sẵn sàng. Chạy lệnh tải mô hình trong hướng dẫn cài đặt.')
    try:
        segment_plan = 'nano-packed-v1' if engine == 'vieneu_nano' and body.paragraph_pause == 0 else 'classic-v1'
        segments = plan_segments({**body.model_dump(), 'engine': engine, 'segment_plan': segment_plan})
        from narration import validate_voice_text
        for index,segment in enumerate(segments):
            if segment.text:validate_voice_text(segment.text,engine,f'Câu SRT {segment.cue+1}' if body.input_format=='srt' else f'Đoạn {index+1}')
        if body.input_format == 'srt':
            cues = parse_srt(body.text)
            if body.cue_fit=='gap' and cues[-1]['end']>body.timeline_seconds+.001:
                raise ValueError('Phụ đề vượt thời lượng đã chọn.')
            if cues[-1]['end'] > body.max_minutes*60:
                raise ValueError('SRT vượt giới hạn thời lượng đã chọn.')
        if not any(segment.text for segment in segments):
            raise ValueError('Nhập nội dung đọc, không chỉ ký hiệu nghỉ.')
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    if body.quality == 'auto':
        body.quality = 'fast' if engine != 'vieneu' or (supports_int8() and (DATA / 'models' / 'vieneu_fast.ready').exists()) else 'standard'
    if body.quality == 'fast' and engine == 'vieneu':
        if not supports_int8() or not (DATA / 'models' / 'vieneu_fast.ready').exists():
            raise HTTPException(503, 'Chế độ nhanh tiếng Việt cần tải vieneu_fast trên CPU có VNNI. Dùng chế độ Tiêu chuẩn hoặc chạy prepare_models.py vieneu_fast.')
    with lock:
        if sum(j['status'] in {'queued', 'running', 'cancelling'} for j in records('jobs')) >= 4:
            raise HTTPException(429, 'Hàng đợi đã có 4 tác vụ. Hãy đợi trước khi tạo thêm.')
        ident = uuid.uuid4().hex
        job = {**body.model_dump(), 'text': body.text.strip(), 'id': ident, 'voice_name': voice['name'], 'engine': engine, 'speaker': voice.get('speaker'), 'status': 'queued', 'segment_plan': segment_plan, 'total': len(segments), 'completed': 0, 'progress': 0, 'created_at': now()}
        if engine == 'vieneu_nano':
            job = resolve_nano_settings(job)
        if benchmark:
            job['benchmark'] = True
        write_json(DATA / 'jobs' / f'{ident}.json', job)
        executor.submit(run_job, ident)
    return job


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    voice_id: str = Field(min_length=1, max_length=128)
    language: str = 'vi'
    clone_engine: str = Field(default='auto', pattern='^(auto|standard|nano)$')
    nano_threads: int = Field(default=0, ge=0, le=8)
    nano_parallel: int = Field(default=0, ge=0, le=8)
    nano_steps: int = Field(default=4, ge=4, le=16)
    quality: str = Field(default='auto', pattern='^(auto|standard|fast)$')


@app.post('/api/benchmark', status_code=202)
def benchmark(body: BenchmarkRequest):
    from benchmark_text import SAMPLE_TEXTS
    if body.language not in SAMPLE_TEXTS:
        raise HTTPException(422, 'Chưa có văn bản đo tốc độ cho ngôn ngữ này.')
    settings = Speech(**body.model_dump(), text=SAMPLE_TEXTS[body.language],
                      input_format='txt', format='wav', speed=1,
                      delivery='natural', paragraph_pause=0, max_minutes=10)
    return queue_speech(settings, benchmark=True)


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


@app.delete('/api/history/{ident}', status_code=204)
def delete_record(ident: str):
    with lock:
        job = get_job(ident)
        if job['status'] in {'queued', 'running', 'cancelling'}:
            raise HTTPException(409, 'Đợi tác vụ hoàn tất trước khi xóa.')
        shutil.rmtree(DATA / 'parts' / ident, ignore_errors=True)
        for path in [DATA / 'audio' / f'{ident}.wav', DATA / 'audio' / f'{ident}.mp3', DATA / 'audio' / f'{ident}.srt', DATA / 'jobs' / f'{ident}.json', DATA / 'jobs' / f'{ident}.log']:
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


@app.get('/api/system-info')
def machine_info():
    return system_info()


@app.get('/api/jobs/{ident}/script.{extension}')
def download_script(ident: str, extension: str):
    from fastapi.responses import Response
    job = get_job(ident)
    if extension not in ('txt', 'srt'):
        raise HTTPException(404, 'Chỉ hỗ trợ TXT và SRT.')
    if extension == 'txt':
        text = '\n'.join(c['text'] for c in parse_srt(job['text'])) if job.get('input_format') == 'srt' else job['text']
    elif job.get('input_format') == 'srt':
        text = export_srt(parse_srt(job['text']))
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


@app.post('/api/voices/refresh')
def refresh_installed_voices():
    clear=getattr(installed_voices,'cache_clear',None)
    if clear:clear()
    return voices()
