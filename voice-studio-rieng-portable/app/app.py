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
from functools import lru_cache

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from narration import MAX_CHARACTERS, PROFILES, plan_segments
from subtitles import parse_srt, export_srt
from system_voices import installed_voices
from hardware import supports_int8, system_info, rendering_presets, rendering_limits, bounded_settings, choose_execution_model
from delivery import get_profile, profile_catalog, supported_preset_voices
from performance import speed_report
from state_io import write_json_atomic, read_progress
from language_catalog import LANGUAGES, CORE_LANGUAGES, QWEN_LANGUAGES, native_language
from voice_library import catalog_voices, resolve_reference

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


# Preserve existing public voice IDs while exposing real bundled reference voices.
import unicodedata
for _preset in supported_preset_voices():
    _existing=next((v for v in PRESETS if v.get('engine') == _preset['engine'] and v.get('speaker') == _preset['speaker']),None)
    if _existing is not None:
        _existing.update(gender=_preset['gender'],description=_preset['description'],category='preset')
        continue
    _slug=''.join(c for c in unicodedata.normalize('NFD',_preset['speaker'].lower().replace('đ','d')) if c.isascii() and (c.isalnum() or c==' ')).strip().replace(' ','-')
    PRESETS.append({**_preset,'id':f"preset-{_preset['engine']}-{_slug}",'category':'preset'})


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


app = FastAPI(title='Voice Studio Riêng', version='1.11.0', lifespan=lifespan)
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


def compact_job(job):
    """Keep scripts in their original file, not in every progress response."""
    text=job.get('text','')
    return {**{key:value for key,value in job.items() if key!='text'},
            'text_excerpt':text[:220], 'text_length':len(text)}


@lru_cache(maxsize=512)
def _cached_compact_job(filename,mtime_ns,size,inode):
    return compact_job(read_json(Path(filename)))


def read_compact_job(path):
    try:
        stat=path.stat()
    except FileNotFoundError:
        raise HTTPException(404,'Không tìm thấy mục này.') from None
    # Atomic job writes change the file identity/mtime. Progress stays separate
    # and is merged below, so live counters never come from this cache.
    return dict(_cached_compact_job(str(path.resolve()),stat.st_mtime_ns,stat.st_size,stat.st_ino))


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


def resident_model():
    if warm_worker is not None and warm_worker.poll() is None:
        try:
            state=json.loads((DATA/'warm-model.json').read_text(encoding='utf-8'))
            if state.get('pid')==warm_worker.pid:return state
        except (OSError,ValueError):pass
    return None


def effective_rendering_presets(engine='vieneu_nano',resource_profile='smooth',precision='fp32',cpu_execution='auto'):
    from calibration import read_saved_presets
    resident=resident_model()
    result={};by_execution={}
    for mode in ('fast','balanced','quality'):
        model_memory=choose_execution_model(engine,resource_profile,cpu_execution,resident,precision,
                                            data=DATA,render_mode=mode)
        if model_memory not in by_execution:
            defaults=rendering_presets(engine,resident=resident,resource_profile=resource_profile,precision=precision,execution_model=model_memory)
            limits=rendering_limits(engine,resident=resident,resource_profile=resource_profile,precision=precision,execution_model=model_memory)
            by_execution[model_memory]=read_saved_presets(DATA,defaults,engine,resident,resource_profile=resource_profile,
                                                         execution_model=model_memory,limits=limits,precision=precision,
                                                         use_auto_choice=cpu_execution=='auto')
        result[mode]=by_execution[model_memory][mode]
    return result


def resource_config():
    profiles=('maximum','smooth','light')
    return {'resource_profiles':[
        {'id':'maximum','name':'Tốc độ tối đa','description':'Dùng ngân sách CPU/RAM tối đa cho bộ đọc.'},
        {'id':'smooth','name':'Mượt khi làm việc','description':'Ưu tiên ứng dụng đang sử dụng, chừa CPU trên máy nhiều lõi.'},
        {'id':'light','name':'Ít RAM','description':'Một tác vụ, tối đa hai luồng; giữ giọng và chất lượng đã chọn.'}],
        'rendering_presets_by_resource':{profile:{engine:effective_rendering_presets(engine,profile)
            for engine in ('vieneu_nano','vieneu','voxcpm')} for profile in profiles},
        'cpu_execution_rendering_presets':{execution:{profile:{engine:effective_rendering_presets(engine,profile,cpu_execution=execution)
            for engine in ('vieneu_nano','vieneu')} for profile in profiles} for execution in ('shared','process')},
        'turbo_int8_rendering_presets_by_resource':{profile:effective_rendering_presets('vieneu',profile,'int8') for profile in profiles},
        'turbo_int8_cpu_execution_rendering_presets':{execution:{profile:effective_rendering_presets('vieneu',profile,'int8',execution)
            for profile in profiles} for execution in ('shared','process')},
        'voxcpm_int8_rendering_presets_by_resource':{profile:effective_rendering_presets('voxcpm',profile,'int8') for profile in profiles}}


def _config_values():
    from calibration import BENCHMARK_LANGUAGES
    from fast_multilingual import is_ready, cuda_available
    reference_languages={language for voice in catalog_voices() for language in voice['languages']}
    if model_ready('voxcpm'):reference_languages.add('th')
    return {
        'version': app.version,
        'native_multilingual_ready': is_ready(DATA),
        'native_multilingual_cpu_available': is_ready(DATA,device='cpu'),
        'native_multilingual_cuda_available': cuda_available(DATA),
        'rendering_presets': effective_rendering_presets(),
        'turbo_rendering_presets': effective_rendering_presets('vieneu'),
        'voxcpm_rendering_presets': effective_rendering_presets('voxcpm'),
        **resource_config(),
        'benchmark_languages': list(BENCHMARK_LANGUAGES),
        'delivery_profiles': profile_catalog(),
        'mode': 'local',
        'edition': 'standalone-voice',
        'languages': LANGUAGES,
        'ai_voice_languages': list(dict.fromkeys([*CORE_LANGUAGES,*sorted(reference_languages)])),
        'max_characters': MAX_CHARACTERS,
        'max_audio_minutes': 1440,
        'fast_vieneu': supports_int8() and (DATA / 'models' / 'vieneu_fast.ready').exists(),
        'int8_cpu': supports_int8(),
        'models': {name: model_ready(name) for name in ('vieneu', 'qwen', 'qwen_clone','voxcpm')},
        'hardware': 'CPU · Giọng Việt / mẫu quốc tế',
        'ffmpeg': bool(shutil.which('ffmpeg')),
        'cpu_cores': os.cpu_count() or 1,
        'nano_ready': (DATA / 'models' / 'vieneu_nano.ready').exists(),
        'worker_warm': warm_worker is not None and warm_worker.poll() is None,
    }


@app.get('/api/voices')
def voices():
    entries=available_voices()
    entries=[{**voice,'engine':voice.get('engine','vieneu' if voice.get('languages',['vi'])[0]=='vi' else 'qwen_clone')} for voice in entries]
    output=[]
    for voice in entries:
        has_sample=voice.get('has_sample',True) if voice.get('category')=='reference' else True
        readiness={}
        ready=model_ready(voice['engine']) and has_sample
        if voice['engine']=='voxcpm':
            from fast_multilingual import is_ready
            readiness={'ready_voxcpm':ready,'ready_native':is_ready(DATA) and has_sample}
            ready=ready or readiness['ready_native']
        reason=voice.get('missing_reason') if voice.get('has_sample') is False else None
        if not ready and not reason:
            reason=('Chạy TAI_GIONG_DA_NGON_NGU.bat một lần để tải bộ tạo giọng cho các mẫu quốc tế, kể cả tiếng Thái.'
                    if voice['engine']=='voxcpm' else 'Mô hình của giọng này chưa được chuẩn bị trên máy.')
        output.append({**voice,**readiness,'native_language':native_language(voice),'ready':ready,'missing_reason':reason})
    return {'voices':output}


def available_voices():
    return catalog_voices()+PRESETS+installed_voices()+records('voices')


def model_ready(engine):
    if engine=='system':return True
    marker=DATA/'models'/f'{engine}.ready'
    if engine=='voxcpm':
        from voxcpm_backend import runtime_python,prepared_model
        try:return runtime_python().is_file() and prepared_model(DATA).is_dir()
        except (OSError,ValueError,KeyError,TypeError,AttributeError):return False
    return marker.is_file()


@app.post('/api/voices/clone', status_code=201)
async def clone(name: str = Form(min_length=1, max_length=80), language: str = Form('vi'), transcript: str = Form('', max_length=2000), consent: bool = Form(False), file: UploadFile = File(...)):
    ident = uuid.uuid4().hex
    target = DATA / 'voices' / f'{ident}.wav'
    source = DATA / 'voices' / f'{ident}.upload'
    try:
        if not consent:
            raise HTTPException(422, 'Cần xác nhận quyền sử dụng mẫu giọng.')
        if language not in {*CORE_LANGUAGES,'th'}:raise HTTPException(422,'Bộ tạo giọng hiện chưa hỗ trợ nhân bản ngôn ngữ này.')
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
        record = {'id': ident, 'name': name.strip(), 'category': 'cloned','engine':'vieneu' if language in {'vi','en-US','en-GB'} else 'voxcpm', 'languages': [language], 'language': language, 'transcript': transcript.strip(), 'description': f'Mẫu giọng cá nhân · {duration:.1f}s', 'duration': duration, 'consent_at': now(), 'created_at': now()}
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
    try:path,_=resolve_reference(ident,DATA)
    except (OSError,ValueError):raise HTTPException(404,'Không tìm thấy mẫu giọng hợp lệ.') from None
    return FileResponse(path, media_type='audio/wav')


@app.delete('/api/voices/{ident}', status_code=204)
def delete_voice(ident: str):
    valid_id(ident)
    if any(voice['id']==ident for voice in catalog_voices()):raise HTTPException(403,'Giọng mặc định trong bộ mẫu riêng không bị xóa từ thư viện cá nhân.')
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
    nano_threads: int = Field(default=2, ge=1, le=8)
    nano_parallel: int = Field(default=1, ge=1, le=32)
    nano_steps: int = Field(default=8, ge=4, le=16)
    voxcpm_steps: int = Field(default=8, ge=4, le=10)
    international_precision: str = Field(default='fp32',pattern='^(fp32|int8)$')
    international_backend: str = Field(default='voxcpm',pattern='^(voxcpm|omnivoice)$')
    international_device: str = Field(default='cpu',pattern='^(cpu|cuda)$')
    omnivoice_steps: int = Field(default=16,ge=8,le=32)
    resource_profile: str = Field(default='smooth',pattern='^(maximum|smooth|light)$')
    cpu_execution: str = Field(default='auto',pattern='^(auto|shared|process)$')
    render_mode: str = Field(default='balanced', pattern='^(fast|balanced|quality)$')
    audio_fit_backend: str = Field(default='ffmpeg', pattern='^(wsola|ffmpeg)$')
    max_minutes: int = Field(default=1440, ge=1, le=1440)
    delivery: str = 'natural'
    paragraph_pause: float | None = Field(default=None, ge=0, le=3)
    quality: str = Field(default='auto', pattern='^(auto|standard|fast)$')
    max_cue_tempo: float = Field(default=1.5, ge=1, le=2)
    cue_fit: str = Field(default='auto', pattern='^(auto|strict|gap)$')
    timeline_seconds: float = Field(default=86400, gt=0, le=86400)


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
        env = dict(os.environ, VOICE_STUDIO_DATA_DIR=str(DATA), HF_HOME=str(DATA / 'models' / 'cache'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS=str(job.get('nano_threads',2)), OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1')
        code = execute_worker(path, env, work)
        if code == -2 or (work / 'cancel.flag').exists():
            if job.get('calibration'):
                from calibration import cleanup_measurements
                cleanup_measurements(DATA,ident)
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
            job.update(status='done', url=f'/api/audio/{ident}', finished_at=now(), wall_processing_seconds=round(elapsed, 3), speed_report=None if reused_parts or job.get('calibration') else speed_report(result.get('audio_seconds', 0), elapsed, result.get('spoken_audio_seconds')))
    except Exception as exc:
        job.update(status='error', error=str(exc))
    with lock:
        write_json(path, job)


@app.post('/api/speech', status_code=202)
def speech(body: Speech):
    return _submit_speech(body)


def _submit_speech(body: Speech,calibration=False):
    if not body.text.strip() or body.language not in LANGUAGES or body.format not in {'wav', 'mp3'} or body.delivery not in PROFILES:
        raise HTTPException(422, 'Kiểm tra nội dung, ngôn ngữ và định dạng xuất.')
    voice = next((v for v in available_voices() if v['id'] == body.voice_id), None)
    if not voice or body.language not in voice['languages']:
        raise HTTPException(422, 'Chọn giọng hỗ trợ ngôn ngữ này. Giọng cá nhân chỉ dùng với ngôn ngữ đã đăng ký.')
    engine = voice.get('engine', 'vieneu' if body.language == 'vi' else 'qwen_clone')
    native=engine=='voxcpm' and body.international_backend=='omnivoice'
    if body.international_backend!='voxcpm' and engine!='voxcpm':
        raise HTTPException(422,'Bộ đọc đa ngôn ngữ chỉ áp dụng cho mẫu giọng quốc tế.')
    if body.international_device!='cpu' and not native:
        raise HTTPException(422,'Chọn OmniVoice để dùng bộ chạy CUDA đa ngôn ngữ.')
    if native and body.omnivoice_steps not in {8,16,32}:
        raise HTTPException(422,'Chọn OmniVoice 8, 16 hoặc 32 bước.')
    if native and body.international_precision!='fp32':
        raise HTTPException(422,'OmniVoice dùng mô hình Q8 có sẵn; chọn bộ nhớ Tiêu chuẩn trước khi đổi bộ đọc.')
    if body.quality == 'auto':
        body.quality = 'fast' if engine != 'vieneu' or (supports_int8() and (DATA / 'models' / 'vieneu_fast.ready').exists()) else 'standard'
    precision=body.international_precision if engine=='voxcpm' else ('int8' if body.quality=='fast' and engine=='vieneu' else 'fp32')
    if engine not in {'vieneu_nano','vieneu'} and body.cpu_execution!='auto':
        raise HTTPException(422,'Chọn cách chạy CPU riêng cho giọng Nano hoặc Turbo.')
    if native:
        # One warm native session avoids replicating model weights, particularly
        # on the GTX 1060's 6 GB. VoxCPM's FP32 RAM budgets do not apply to GGUF.
        model_memory='native'
        body.nano_parallel=1
        if 'nano_threads' not in body.model_fields_set:
            body.nano_threads=min(8,os.cpu_count() or 1,2 if body.resource_profile=='light' else 4)
        if body.resource_profile=='light':body.nano_threads=min(body.nano_threads,2)
        if 'omnivoice_steps' not in body.model_fields_set:
            body.omnivoice_steps={'fast':8,'balanced':16,'quality':32}[body.render_mode]
    else:
        model_memory=choose_execution_model(engine,body.resource_profile,body.cpu_execution,resident_model(),precision,
                                            data=DATA,render_mode=body.render_mode)
        presets=effective_rendering_presets(engine,body.resource_profile,precision,body.cpu_execution)
        preset=presets[body.render_mode]
        for field,value in preset.items():
            if field not in body.model_fields_set:setattr(body,field,value)
    if body.nano_steps not in {4,8,16}:raise HTTPException(422,'Chọn Nano 4, 8 hoặc 16 bước.')
    if engine=='voxcpm':
        if body.voxcpm_steps not in {4,8,10}:raise HTTPException(422,'Chọn bộ đọc quốc tế 4, 8 hoặc 10 bước.')
    elif body.international_precision!='fp32':raise HTTPException(422,'INT8 quốc tế chỉ dùng với bộ giọng đa ngôn ngữ.')
    if engine in {'vieneu_nano','vieneu','voxcpm'} and not native:
        limits=rendering_limits(engine,resident=resident_model(),resource_profile=body.resource_profile,precision=precision,execution_model=model_memory)
        if engine=='voxcpm' and precision=='int8' and limits.get('memory_sufficient') is False:
            raise HTTPException(503,'INT8 quốc tế cần khoảng 24 GB RAM khả dụng khi nạp. Chọn FP32 hoặc giải phóng RAM rồi thử lại.')
        bounded=bounded_settings({'nano_parallel':body.nano_parallel,'nano_threads':body.nano_threads},limits)
        body.nano_parallel=bounded['nano_parallel'];body.nano_threads=bounded['nano_threads']
    if body.paragraph_pause is None:body.paragraph_pause=get_profile(body.delivery).pause
    from subtitles import normalize_script
    try:
        body.text, body.input_format = normalize_script(body.text, body.input_format)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    if voice.get('category')=='reference' and not voice.get('has_sample'):
        raise HTTPException(503,'Tệp mẫu của giọng mặc định đang thiếu hoặc không hợp lệ. Cài lại bộ mẫu riêng.')
    if native:
        from fast_multilingual import is_ready
        if not is_ready(DATA,device=body.international_device):
            raise HTTPException(503,'Chạy TAI_GIONG_DA_NGON_NGU_NHANH.bat để chuẩn bị OmniVoice và bộ chạy đã chọn. CUDA cần bản cài GPU tương thích với máy.')
    elif not model_ready(engine):
        raise HTTPException(503,'Chạy TAI_GIONG_DA_NGON_NGU.bat một lần để chuẩn bị các giọng quốc tế mới.' if engine=='voxcpm' else f'Mô hình {engine} chưa sẵn sàng. Chạy lệnh tải mô hình trong hướng dẫn cài đặt.')
    if calibration and engine not in {'vieneu_nano','vieneu'}:raise HTTPException(422,'Chọn giọng Nano hoặc Turbo để đo và tối ưu CPU.')
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
    if body.quality == 'fast' and engine == 'vieneu':
        if not supports_int8() or not (DATA / 'models' / 'vieneu_fast.ready').exists():
            raise HTTPException(503, 'Chế độ nhanh tiếng Việt cần tải vieneu_fast trên CPU có VNNI. Dùng chế độ Tiêu chuẩn hoặc chạy prepare_models.py vieneu_fast.')
    with lock:
        if sum(j['status'] in {'queued', 'running', 'cancelling'} for j in records('jobs')) >= 4:
            raise HTTPException(429, 'Hàng đợi đã có 4 tác vụ. Hãy đợi trước khi tạo thêm.')
        ident = uuid.uuid4().hex
        job = {**body.model_dump(), 'model_memory':model_memory, 'calibration':calibration, 'text': body.text.strip(), 'id': ident, 'voice_name': voice['name'], 'engine': engine, 'speaker': voice.get('speaker'), 'status': 'queued', 'segment_plan': segment_plan, 'total': len(segments), 'completed': 0, 'progress': 0, 'created_at': now()}
        write_json(DATA / 'jobs' / f'{ident}.json', job)
        executor.submit(run_job, ident)
    return job


@app.get('/api/history')
def history(compact:bool=False):
    if compact:
        jobs=[]
        for path in (DATA/'jobs').glob('*.json'):
            try:jobs.append(read_compact_job(path))
            except (ValueError,OSError,HTTPException):continue
    else:jobs=records('jobs')
    return {'items': [job_status(j) for j in sorted(jobs, key=lambda x: x['created_at'], reverse=True)[:100]]}


@app.get('/api/jobs/{ident}')
def get_job(ident: str,compact:bool=False):
    path=DATA/'jobs'/f'{valid_id(ident)}.json'
    return job_status(read_compact_job(path) if compact else read_json(path))


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
def resume_job(ident: str, auto_fit: bool = True):
    with lock:
        job = get_job(ident)
        if job['status'] not in {'cancelled', 'error'}:
            raise HTTPException(409, 'Chỉ tiếp tục tác vụ đã dừng hoặc có lỗi.')
        if sum(j['status'] in {'queued', 'running', 'cancelling'} for j in records('jobs')) >= 4:
            raise HTTPException(429, 'Hàng đợi đã đầy.')
        if not job.get('speaker'):
            try:resolve_reference(job['voice_id'],DATA)
            except (OSError,ValueError):raise HTTPException(409,'Mẫu giọng đã bị xóa hoặc không hợp lệ; không thể tiếp tục tác vụ này.') from None
        (DATA / 'parts' / ident / 'cancel.flag').unlink(missing_ok=True)
        if auto_fit and job.get('input_format') == 'srt':
            job['cue_fit'] = 'auto'
        job.update(status='queued')
        job.pop('error', None)
        write_json(DATA / 'jobs' / f'{ident}.json', job)
        executor.submit(run_job, ident)
        return job


@app.get('/api/system-info')
def machine_info(quick:bool=False):
    return {**system_info(include_cuda_probe=not quick), 'rendering_presets': effective_rendering_presets(), 'turbo_rendering_presets':effective_rendering_presets('vieneu'), 'voxcpm_rendering_presets':effective_rendering_presets('voxcpm'),**resource_config()}


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




@app.post('/api/scripts/import')
async def import_script(file: UploadFile = File(...)):
    from subtitles import decode_script, normalize_script
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.txt','.srt'}:raise HTTPException(422,'Chọn tệp TXT hoặc SRT.')
    raw=await file.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise HTTPException(422,'Tệp tối đa 8 MB.')
    try:
        text=decode_script(raw)
        if len(text)>MAX_CHARACTERS:raise ValueError('Tối đa 1.000.000 ký tự.')
        text,kind=normalize_script(text,suffix[1:])
        if len(text)>MAX_CHARACTERS:raise ValueError('Nội dung sau chuyển đổi vượt 1.000.000 ký tự; chia tệp thành các phần.')
        cues=parse_srt(text) if kind=='srt' else []
        return {'text':text,'input_format':kind,'duration':cues[-1]['end'] if cues else None}
    except UnicodeError:
        raise HTTPException(422,'Không đọc được mã hóa. Lưu tệp bằng UTF-8 hoặc Unicode UTF-16 rồi nhập lại.') from None
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None


class BenchmarkRequest(BaseModel):
    voice_id: str = Field(min_length=1,max_length=128)
    language: str = 'vi'
    render_mode: str = Field(default='balanced',pattern='^(fast|balanced|quality)$')
    delivery: str = 'natural'
    nano_steps: int | None = Field(default=None, ge=4, le=16)
    voxcpm_steps: int | None = Field(default=None, ge=4, le=10)
    resource_profile: str = Field(default='smooth',pattern='^(maximum|smooth|light)$')
    cpu_execution: str = Field(default='auto',pattern='^(auto|shared|process)$')
    international_precision: str = Field(default='fp32',pattern='^(fp32|int8)$')
    international_backend: str = Field(default='voxcpm',pattern='^(voxcpm|omnivoice)$')
    international_device: str = Field(default='cpu',pattern='^(cpu|cuda)$')
    omnivoice_steps: int | None = Field(default=None,ge=8,le=32)
    nano_parallel: int | None = Field(default=None, ge=1, le=32)
    nano_threads: int | None = Field(default=None, ge=1, le=8)
    audio_fit_backend: str | None = Field(default=None, pattern='^(wsola|ffmpeg)$')
    quality: str = Field(default='auto', pattern='^(auto|standard|fast)$')


@app.post('/api/benchmark',status_code=202)
def benchmark(body: BenchmarkRequest):
    from calibration import benchmark_sample_text, BENCHMARK_LANGUAGES
    voice=next((v for v in available_voices() if v['id']==body.voice_id),None)
    engine=voice.get('engine') if voice else None
    if not voice or body.language not in voice['languages'] or body.language not in BENCHMARK_LANGUAGES:
        raise HTTPException(422,'Chọn giọng và ngôn ngữ hỗ trợ mẫu đo.')
    if engine not in {'vieneu_nano','vieneu','voxcpm'}:raise HTTPException(422,'Đo tốc độ hiện hỗ trợ Nano, Turbo và bộ giọng mẫu đa ngôn ngữ.')
    native=engine=='voxcpm' and body.international_backend=='omnivoice'
    workers=1 if native else body.nano_parallel or effective_rendering_presets(engine,body.resource_profile,body.international_precision if engine=='voxcpm' else 'fp32',body.cpu_execution)[body.render_mode]['nano_parallel']
    text=benchmark_sample_text(body.language,workers,engine)
    settings=body.model_dump(exclude_none=True)
    payload=Speech(text=text,**settings,paragraph_pause=0,format='wav')
    job=speech(payload)
    return job


@app.post('/api/calibrate',status_code=202)
def calibrate_machine(body: BenchmarkRequest):
    from calibration import sample_text
    if body.language not in {'vi','en-US','en-GB'}:raise HTTPException(422,'Mẫu tối ưu CPU dùng giọng Nano hoặc Turbo tiếng Việt, tiếng Anh.')
    voice=next((v for v in available_voices() if v['id']==body.voice_id),None)
    if not voice or voice.get('engine') not in {'vieneu_nano','vieneu'}:raise HTTPException(422,'Chọn giọng Nano hoặc Turbo để tự đo CPU.')
    precision='int8' if (body.quality=='fast' or body.quality=='auto' and supports_int8() and (DATA/'models/vieneu_fast.ready').exists()) and voice['engine']=='vieneu' else 'fp32'
    execution=choose_execution_model(voice['engine'],body.resource_profile,body.cpu_execution,resident_model(),precision,
                                     data=DATA,render_mode=body.render_mode)
    preset=rendering_presets(voice['engine'],resource_profile=body.resource_profile,precision=precision,execution_model=execution)[body.render_mode]
    payload=Speech(text=sample_text(preset['nano_parallel'],body.language),voice_id=body.voice_id,language=body.language,
                   render_mode=body.render_mode,resource_profile=body.resource_profile,cpu_execution=body.cpu_execution,quality=body.quality,delivery=body.delivery,paragraph_pause=0,format='wav',**preset)
    return _submit_speech(payload,calibration=True)
