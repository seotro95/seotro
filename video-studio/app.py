from __future__ import annotations
import os
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, ConfigDict
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
import engine
from subtitles import parse_srt, to_srt

app = FastAPI(title='Video Studio VN', version='0.2.0')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
app.mount('/static', StaticFiles(directory=engine.RESOURCE_ROOT / 'static'), name='static')


@app.middleware('http')
async def local_requests(request, call_next):
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'Yêu cầu cần xuất phát từ giao diện của tool.'}, status_code=403)
    return await call_next(request)


@app.exception_handler(ValueError)
async def invalid_input(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=422)


@app.get('/')
def index():
    return FileResponse(engine.RESOURCE_ROOT / 'static' / 'index.html')


@app.get('/api/health')
def health():
    def available(name):
        try:
            engine.executable(name)
            return True
        except ValueError:
            return False
    from offline_models import status
    from updater import local_version
    return {'version':local_version(), 'ffmpeg':available('ffmpeg'), 'ffprobe':available('ffprobe'),
            'workers':2, **status()}



@app.get('/api/assets')
def assets():
    return engine.list_assets()


@app.post('/api/upload', status_code=201)
async def upload(file: UploadFile = File(...)):
    name = Path((file.filename or 'video').replace('\\', '/')).name
    suffix = Path(name).suffix.lower()
    if suffix not in ('.mp4', '.mkv', '.mov', '.webm', '.avi', '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.srt', '.txt'):
        await file.close()
        raise ValueError('Hỗ trợ video, âm thanh, SRT và TXT.')
    folder = engine.DATA / 'uploads' / str(uuid.uuid4())
    folder.mkdir(parents=True)
    target = folder / ('source' + suffix)
    limit = 2 * 1024 ** 3 if suffix not in ('.srt', '.txt') else 2 * 1024 ** 2
    count = 0
    try:
        with target.open('wb') as output:
            while chunk := await file.read(1024 * 1024):
                count += len(chunk)
                if count > limit:
                    raise HTTPException(413, 'Tệp quá lớn. Giới hạn media 2 GB, phụ đề 2 MB.')
                output.write(chunk)
        identifier = await run_in_threadpool(engine.register, target, name)
        return {'asset_id': identifier}
    except Exception:
        target.unlink(missing_ok=True)
        folder.rmdir()
        raise
    finally:
        await file.close()


@app.get('/api/assets/{identifier}/file')
def asset_file(identifier: str):
    row = engine.asset(identifier)
    return FileResponse(row['path'], filename=row['name'], content_disposition_type='inline')


@app.get('/api/assets/{identifier}/text')
def asset_text(identifier: str):
    row = engine.asset(identifier)
    if row['kind'] not in ('subtitle', 'text'):
        raise ValueError('Tệp này không phải văn bản.')
    return {'text': Path(row['path']).read_text(encoding='utf-8-sig')}


class SubtitleSave(BaseModel):
    name: str = Field(default='phu_de.srt', max_length=120)
    text: str = Field(min_length=1, max_length=2000000)


@app.post('/api/subtitles', status_code=201)
def save_subtitle(req: SubtitleSave):
    cues = parse_srt(req.text)
    folder = engine.DATA / 'subtitles' / str(uuid.uuid4())
    folder.mkdir(parents=True)
    path = folder / 'subtitle.srt'
    path.write_text(to_srt(cues), encoding='utf-8')
    return {'asset_id': engine.register(path, Path(req.name.replace('\\', '/')).stem + '.srt'), 'cues': len(cues)}


@app.get('/api/jobs')
def jobs():
    return engine.jobs()


@app.post('/api/jobs/{identifier}/cancel', status_code=202)
def cancel(identifier: str):
    engine.cancel(identifier)
    return {'ok': True}


class DownloadRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=30)


@app.post('/api/download', status_code=202)
def download(req: DownloadRequest):
    allowed = ('youtube.com', 'youtu.be', 'bilibili.com', 'b23.tv', 'douyin.com', 'iesdouyin.com', 'tiktok.com')
    for url in req.urls:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443) or not any(host == h or host.endswith('.' + h) for h in allowed) or len(url) > 4096:
            raise ValueError('Hãy dùng link HTTPS của YouTube, TikTok, Douyin hoặc Bilibili.')
    return {'job_ids': [engine.enqueue('download', 'Tải video ' + str(i + 1), {'url': url}) for i, url in enumerate(req.urls)]}


class STTRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1, max_length=30)
    language: str = Field(default='', max_length=10, pattern=r'^[a-z-]*$')
    model: str = 'tiny'

    @field_validator('model')
    @classmethod
    def model_choice(cls, value):
        if value not in ('tiny', 'base', 'small', 'medium', 'large-v3'):
            raise ValueError('Model Whisper không hợp lệ.')
        return value


def batch_assets(action, ids, payload, kinds):
    rows = [engine.asset(identifier) for identifier in ids]
    if any(row['kind'] not in kinds for row in rows):
        raise ValueError('Loại tệp đã chọn không phù hợp tác vụ.')
    return {'job_ids': [engine.enqueue(action, row['name'], {**payload, 'asset_id': row['id']}) for row in rows]}


@app.post('/api/stt', status_code=202)
def stt(req: STTRequest):
    return batch_assets('stt', req.asset_ids, req.model_dump(exclude={'asset_ids'}), ('video', 'audio'))


class TranslateRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1, max_length=30)
    source_language: str = 'auto'
    language: str = 'vi'

    @field_validator('source_language', 'language')
    @classmethod
    def language_choice(cls, value, info):
        from offline_models import LANGUAGES
        if value not in LANGUAGES and not (info.field_name == 'source_language' and value == 'auto'):
            raise ValueError('Ngôn ngữ chưa được hỗ trợ.')
        return value


@app.post('/api/translate', status_code=202)
def translate(req: TranslateRequest):
    return batch_assets('translate', req.asset_ids, req.model_dump(exclude={'asset_ids'}), ('subtitle',))


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str = 'vi_VN-vais1000-medium'
    speed: float = Field(default=1, ge=.6, le=1.5, allow_inf_nan=False)

    @field_validator('voice')
    @classmethod
    def voice_choice(cls, value):
        from offline_models import VOICES
        if value not in VOICES:
            raise ValueError('Giọng đọc chưa được hỗ trợ.')
        return value


@app.post('/api/tts', status_code=202)
def tts(req: TTSRequest):
    return {'job_ids':[engine.enqueue('tts', 'Tạo giọng đọc cục bộ', req.model_dump())]}


class RenderRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1, max_length=30)
    subtitle_id: str | None = None
    audio_id: str | None = None
    start: float = Field(default=0, ge=0, allow_inf_nan=False)
    end: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    speed: float = Field(default=1, ge=.5, le=2, allow_inf_nan=False)
    height: int = 0
    crf: int = Field(default=20, ge=16, le=32)
    title: str = Field(default='', max_length=300)
    font_size: int = Field(default=22, ge=12, le=72)
    subtitle_color: str = Field(default='#ffffff', pattern=r'^#[0-9A-Fa-f]{6}$')

    @field_validator('height')
    @classmethod
    def height_choice(cls, value):
        if value not in (0, 360, 480, 720, 1080):
            raise ValueError('Kích thước xuất không hợp lệ.')
        return value


@app.post('/api/render', status_code=202)
def render(req: RenderRequest):
    if req.subtitle_id:
        if engine.asset(req.subtitle_id)['kind'] != 'subtitle':
            raise ValueError('Phụ đề cần là SRT.')
    if req.audio_id:
        engine.asset(req.audio_id)
    return batch_assets('render', req.asset_ids, req.model_dump(exclude={'asset_ids'}), ('video',))


class AIRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)
    task: str = 'tidy'

    @field_validator('task')
    @classmethod
    def task_choice(cls, value):
        if value not in ('tidy', 'titles', 'outline'):
            raise ValueError('Tác vụ biên tập không hợp lệ.')
        return value


@app.post('/api/ai', status_code=202)
def ai(req: AIRequest):
    return {'job_ids':[engine.enqueue('ai', 'Biên tập cục bộ', req.model_dump())]}


class LocalSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    auto_update: bool = True


@app.get('/api/config')
def config():
    from updater import settings, local_version
    return {'auto_update':settings()['auto_update'], 'version':local_version(), 'local_only':True}


@app.post('/api/config')
def save_config(req: LocalSettings):
    from updater import save_settings
    with engine.LOCK:
        save_settings(req.model_dump())
    return config()


@app.post('/api/models/prepare', status_code=202)
def prepare_models():
    return {'job_ids':[engine.enqueue('prepare', 'Chuẩn bị model Việt / Anh', {})]}


@app.get('/api/updates/check')
def updates():
    from updater import check_update
    return check_update()


@app.post('/api/updates/request')
def request_update():
    from updater import save_settings
    with engine.LOCK:
        save_settings({'update_requested':True})
    return {'message':'Đã hẹn cập nhật. Đóng cửa sổ khởi động rồi mở lại khoi_dong.bat để áp dụng.'}
