from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VOICE_STUDIO_DATA_DIR', str(BASE / '.data'))).resolve()
for folder in ('voices', 'audio', 'jobs', 'models'):
    (DATA / folder).mkdir(parents=True, exist_ok=True)
LANGUAGES = {'vi': 'Tiếng Việt', 'en-US': 'English · US', 'en-GB': 'English · UK', 'ja': '日本語 · Nhật', 'ko': '한국어 · Hàn', 'zh': '中文 · Trung', 'fr': 'Français · Pháp', 'de': 'Deutsch · Đức', 'es': 'Español · Tây Ban Nha', 'it': 'Italiano · Ý', 'pt': 'Português · Bồ Đào Nha', 'ru': 'Русский · Nga'}
PRESETS = [
    {'id': 'vi-maianh', 'name': 'Mai Anh', 'engine': 'vieneu', 'speaker': 'Mai Anh', 'languages': ['vi', 'en-US', 'en-GB'], 'description': 'Giọng có sẵn · VieNeu'},
    {'id': 'vi-haidang', 'name': 'Hải Đăng', 'engine': 'vieneu', 'speaker': 'Hải Đăng', 'languages': ['vi', 'en-US', 'en-GB'], 'description': 'Giọng có sẵn · VieNeu'},
    {'id': 'qw-ryan', 'name': 'Ryan', 'engine': 'qwen', 'speaker': 'Ryan', 'languages': list(LANGUAGES)[1:], 'description': 'Giọng nam · tiếng Anh bản ngữ'},
    {'id': 'qw-aiden', 'name': 'Aiden', 'engine': 'qwen', 'speaker': 'Aiden', 'languages': list(LANGUAGES)[1:], 'description': 'Giọng nam · tiếng Anh bản ngữ'},
    {'id': 'qw-ono', 'name': 'Ono Anna', 'engine': 'qwen', 'speaker': 'Ono_Anna', 'languages': list(LANGUAGES)[1:], 'description': 'Giọng nữ · tiếng Nhật bản ngữ'},
    {'id': 'qw-sohee', 'name': 'Sohee', 'engine': 'qwen', 'speaker': 'Sohee', 'languages': list(LANGUAGES)[1:], 'description': 'Giọng nữ · tiếng Hàn bản ngữ'},
    {'id': 'qw-vivian', 'name': 'Vivian', 'engine': 'qwen', 'speaker': 'Vivian', 'languages': list(LANGUAGES)[1:], 'description': 'Giọng nữ · tiếng Trung bản ngữ'},
]
@asynccontextmanager
async def lifespan(application):
    # A previous process cannot finish jobs after this local server restarts.
    for interrupted in records('jobs'):
        if interrupted.get('status') in {'queued', 'running'}:
            interrupted.update(status='error', error='Ứng dụng đã khởi động lại trước khi hoàn tất. Bạn có thể tạo lại bản thu.')
            write_json(DATA / 'jobs' / f"{interrupted['id']}.json", interrupted)
    yield


app = FastAPI(title='Voice Studio · Local AI', version='1.0.0', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
executor = ThreadPoolExecutor(max_workers=1)
lock = threading.RLock()


def now():
    return datetime.now(UTC).isoformat()


def write_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


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
    return FileResponse(BASE / 'static' / 'index.html')


@app.get('/api/config')
def config():
    return {'mode': 'local', 'languages': LANGUAGES, 'max_characters': 2000, 'models': {name: (DATA / 'models' / f'{name}.ready').exists() for name in ('vieneu', 'qwen', 'qwen_clone')}, 'hardware': 'GPU' if shutil.which('nvidia-smi') else 'CPU', 'ffmpeg': bool(shutil.which('ffmpeg'))}


@app.get('/api/voices')
def voices():
    return {'voices': PRESETS + records('voices')}


@app.post('/api/voices/clone', status_code=201)
async def clone(name: str = Form(min_length=1, max_length=80), language: str = Form('vi'), transcript: str = Form('', max_length=2000), consent: bool = Form(False), file: UploadFile = File(...)):
    ident = uuid.uuid4().hex
    target = DATA / 'voices' / f'{ident}.wav'
    source = DATA / 'voices' / f'{ident}.upload'
    try:
        if not consent:
            raise HTTPException(422, 'Cần xác nhận quyền sử dụng mẫu giọng.')
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
        if any(j['status'] in {'queued', 'running'} and j.get('voice_id') == ident for j in records('jobs')):
            raise HTTPException(409, 'Giọng đang được dùng trong hàng đợi. Đợi tác vụ hoàn tất trước khi xóa.')
        for suffix in ('.json', '.wav'):
            (DATA / 'voices' / f'{ident}{suffix}').unlink(missing_ok=True)


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice_id: str = Field(min_length=1, max_length=128)
    language: str = 'vi'
    speed: float = Field(default=1, ge=0.7, le=1.4)
    format: str = 'wav'


def run_job(ident):
    path = DATA / 'jobs' / f'{ident}.json'
    with lock:
        job = read_json(path)
        job['status'] = 'running'
        write_json(path, job)
    try:
        env = dict(os.environ, VOICE_STUDIO_DATA_DIR=str(DATA), HF_HOME=str(DATA / 'models' / 'cache'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS=os.environ.get('VOICE_STUDIO_THREADS', '4'))
        completed = subprocess.run([sys.executable, str(BASE / 'worker.py'), str(path)], env=env, capture_output=True, timeout=1800, text=True, check=False)
        if completed.returncode:
            # Keep diagnostics local. Client gets a short actionable error, not a traceback.
            (DATA / 'jobs' / f'{ident}.log').write_text(completed.stderr[-20000:], encoding='utf-8')
            raise RuntimeError('Không tạo được âm thanh. Kiểm tra mô hình đã tải đầy đủ và nhật ký tác vụ trên máy chủ.')
        output = DATA / 'audio' / f"{ident}.{job['format']}"
        if not output.exists() or output.stat().st_size < 100:
            raise RuntimeError('Mô hình không tạo ra âm thanh hợp lệ.')
        job.update(status='done', url=f'/api/audio/{ident}', finished_at=now())
    except subprocess.TimeoutExpired:
        job.update(status='error', error='Tác vụ vượt 30 phút trên máy này. Rút ngắn văn bản hoặc dùng GPU.')
    except Exception as exc:
        job.update(status='error', error=str(exc))
    with lock:
        write_json(path, job)


@app.post('/api/speech', status_code=202)
def speech(body: Speech):
    if not body.text.strip() or body.language not in LANGUAGES or body.format not in {'wav', 'mp3'}:
        raise HTTPException(422, 'Kiểm tra nội dung, ngôn ngữ và định dạng xuất.')
    voice = next((v for v in PRESETS + records('voices') if v['id'] == body.voice_id), None)
    if not voice or body.language not in voice['languages']:
        raise HTTPException(422, 'Chọn giọng hỗ trợ ngôn ngữ này. Giọng cá nhân chỉ dùng với ngôn ngữ đã đăng ký.')
    engine = voice.get('engine', 'vieneu' if body.language == 'vi' else 'qwen_clone')
    if not (DATA / 'models' / f'{engine}.ready').exists():
        raise HTTPException(503, f'Mô hình {engine} chưa sẵn sàng. Chạy lệnh tải mô hình trong hướng dẫn cài đặt.')
    with lock:
        if sum(j['status'] in {'queued', 'running'} for j in records('jobs')) >= 4:
            raise HTTPException(429, 'Hàng đợi đã có 4 tác vụ. Hãy đợi trước khi tạo thêm.')
        ident = uuid.uuid4().hex
        job = {**body.model_dump(), 'text': body.text.strip(), 'id': ident, 'voice_name': voice['name'], 'engine': engine, 'speaker': voice.get('speaker'), 'status': 'queued', 'created_at': now()}
        write_json(DATA / 'jobs' / f'{ident}.json', job)
        executor.submit(run_job, ident)
    return job


@app.get('/api/history')
def history():
    return {'items': sorted(records('jobs'), key=lambda x: x['created_at'], reverse=True)[:100]}


@app.get('/api/jobs/{ident}')
def get_job(ident: str):
    return read_json(DATA / 'jobs' / f'{valid_id(ident)}.json')


@app.get('/api/audio/{ident}')
def audio(ident: str):
    job = get_job(ident)
    if job['status'] != 'done':
        raise HTTPException(404, 'Bản thu chưa sẵn sàng.')
    path = DATA / 'audio' / f"{ident}.{job['format']}"
    if not path.exists():
        raise HTTPException(404, 'Không tìm thấy bản thu.')
    return FileResponse(path, media_type='audio/wav' if job['format'] == 'wav' else 'audio/mpeg', filename=f"voice-studio-{ident[:8]}.{job['format']}", content_disposition_type='inline')


@app.delete('/api/history/{ident}', status_code=204)
def delete_record(ident: str):
    with lock:
        job = get_job(ident)
        if job['status'] in {'queued', 'running'}:
            raise HTTPException(409, 'Đợi tác vụ hoàn tất trước khi xóa.')
        for path in [DATA / 'audio' / f'{ident}.wav', DATA / 'audio' / f'{ident}.mp3', DATA / 'jobs' / f'{ident}.json', DATA / 'jobs' / f'{ident}.log']:
            path.unlink(missing_ok=True)
