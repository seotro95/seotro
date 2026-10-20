"""Hmong Studio: local audio workspace with an explicit TTS adapter contract."""
import os
import json
import math
import subprocess
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from starlette.concurrency import run_in_threadpool
import local_engine
import cloning_engine
from audio_workspace import router as audio_router, load_profile

BASE = Path(__file__).resolve().parent
app = FastAPI(title='Hmong Studio', version='0.3.0')
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
app.include_router(audio_router)


def remote_enabled():
    # Local mode never forwards text or audio just because a legacy URL is set.
    return os.getenv('HMONG_ENGINE', 'local') == 'remote'


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    dialect: Literal['mww', 'vi', 'en']
    voice: Literal['model-default', 'hmong-white-female', 'hmong-white-male'] = 'model-default'
    emotion: Literal['neutral', 'storytelling', 'warm', 'cheerful', 'sad'] = 'neutral'
    speed: float = Field(default=1, ge=0.5, le=2)
    profile_id: str | None = Field(default=None, pattern=r'^[0-9a-f]{32}$')


class ReferenceSettings(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)


def reference_path(voice):
    if voice not in ('hmong-white-male', 'hmong-white-female'):
        raise HTTPException(404, 'Không tìm thấy mẫu giọng mặc định.')
    return BASE / 'static' / 'voices' / f'{voice}.mp3'


def reference_config_path(voice):
    reference_path(voice)
    root = Path(os.getenv('HMONG_STUDIO_DATA', str(BASE / '.data'))) / 'references'
    return root / f'{voice}.json'


def reference_settings(voice):
    path = reference_path(voice)
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)],
                                check=True, capture_output=True, text=True, timeout=15)
        duration = float(json.loads(result.stdout)['format']['duration'])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('duration')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise HTTPException(503, 'Không đọc được mẫu giọng. Kiểm tra FFmpeg/ffprobe.') from None
    settings = {'text': '', 'start': 0, 'end': min(8, duration), 'duration': duration}
    try:
        saved = ReferenceSettings.model_validate_json(reference_config_path(voice).read_text(encoding='utf-8'))
        if saved.text.strip() and 3 <= saved.end - saved.start <= 8 and saved.end <= duration:
            settings.update(saved.model_dump())
    except (OSError, ValueError):
        pass
    return settings


@app.put('/api/voices/{voice}/reference')
def save_reference(voice: str, payload: ReferenceSettings):
    settings = reference_settings(voice)
    if not payload.text.strip() or not 3 <= payload.end - payload.start <= 8 or payload.end > settings['duration']:
        raise HTTPException(422, 'Chọn đoạn mẫu dài 3–8 giây trong bản gốc và nhập đúng lời của đoạn này.')
    path = reference_config_path(voice)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(payload.model_dump_json())
    temporary.replace(path)
    return {'saved': True, 'reference_settings': reference_settings(voice)}


@app.get('/')
def index():
    return FileResponse(BASE / 'static/index.html')


@app.get('/api/status')
def status():
    remote = remote_enabled() and bool(os.getenv('HMONG_TTS_URL'))
    local = local_engine.availability()
    clone = cloning_engine.availability()
    local['cloning'] = clone['ready']
    local['clone_engine'] = clone
    return {'tts_configured': remote or clone['ready'] or (local['dependencies'] and local['tts_models']['mww']),
            'dialects': list(local_engine.LANGUAGES), 'languages': local_engine.LANGUAGES,
            'engine': 'remote' if remote_enabled() else 'local',
            'remote_tts': remote, 'remote_asr': remote_enabled() and bool(os.getenv('HMONG_ASR_URL')),
            'cloning': clone['ready'] or (remote and os.getenv('HMONG_TTS_CLONING') == '1'),
            'emotions': remote and os.getenv('HMONG_TTS_EMOTIONS') == '1',
            'local': local,
            'message': 'Chế độ cục bộ không cần API key. Hai giọng nam/nữ đã có mẫu gốc; cần mô hình nhân bản và lời mẫu khớp âm thanh để tạo lời mới. ' + clone['reason']}


@app.get('/api/voices')
def voices():
    cloning = cloning_engine.availability()['ready']
    return {'voices': [
        {'id': 'model-default', 'name': 'Giọng gốc của mô hình', 'gender': None, 'reference': None},
        *[{'id': f'hmong-white-{gender}', 'name': name, 'gender': gender,
           'reference': f'/static/voices/hmong-white-{gender}.mp3',
           'reference_settings': reference_settings(f'hmong-white-{gender}'),
           'generation_configured': cloning and bool(reference_settings(f'hmong-white-{gender}')['text'])}
          for gender, name in [('female', 'Hmong Trắng · Nữ'), ('male', 'Hmong Trắng · Nam')]]]}


@app.post('/api/speech')
async def speech(payload: Speech):
    if not payload.text.strip():
        raise HTTPException(422, 'Nhập lời đọc trước khi tạo giọng.')
    url = os.getenv('HMONG_TTS_URL', '') if remote_enabled() else ''
    if not url:
        if payload.profile_id or payload.voice != 'model-default':
            if payload.dialect != 'mww' or payload.emotion != 'neutral':
                raise HTTPException(422, 'Nhân bản Hmong cục bộ chỉ nhận Hmong Trắng và cách đọc Tự nhiên.')
            try:
                if payload.profile_id:
                    metadata, sample = load_profile(payload.profile_id)
                    data = await run_in_threadpool(cloning_engine.synthesize, payload.text, payload.speed, sample, metadata['transcript'])
                else:
                    settings = await run_in_threadpool(reference_settings, payload.voice)
                    if not settings['text'].strip():
                        raise HTTPException(422, 'Nhập và lưu đúng lời đoạn mẫu 3–8 giây của giọng đã chọn trước khi nhân bản.')
                    data = await run_in_threadpool(clone_builtin, payload, settings)
                return Response(data, media_type='audio/wav', headers={'Cache-Control': 'no-store'})
            except cloning_engine.CloningError as exc:
                raise HTTPException(503, str(exc)) from None
        try:
            data = await run_in_threadpool(local_engine.synthesize, payload.text, payload.dialect, payload.speed, payload.voice, payload.emotion)
            return Response(data, media_type='audio/wav', headers={'Cache-Control': 'no-store'})
        except local_engine.EngineError as exc:
            raise HTTPException(503, str(exc)) from None
    if payload.voice != 'model-default' and os.getenv('HMONG_TTS_CLONING') != '1':
        raise HTTPException(422, 'Dịch vụ chưa xác nhận hỗ trợ hai mẫu giọng. Chọn Giọng gốc hoặc cấu hình adapter nhân bản.')
    if payload.emotion != 'neutral' and os.getenv('HMONG_TTS_EMOTIONS') != '1':
        raise HTTPException(422, 'Dịch vụ chưa xác nhận hỗ trợ cảm xúc. Chọn Tự nhiên.')
    if not url.startswith('https://'):
        raise HTTPException(503, 'Dịch vụ giọng phải dùng HTTPS.')
    headers = {}
    if token := os.getenv('HMONG_TTS_TOKEN'):
        headers['Authorization'] = f'Bearer {token}'
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=False) as client:
            async with client.stream('POST', url, json=payload.model_dump(), headers=headers) as result:
                if result.status_code != 200:
                    raise HTTPException(502, f'Dịch vụ giọng trả mã {result.status_code}. Kiểm tra cấu hình phía máy chủ.')
                content_type = result.headers.get('content-type', '').split(';')[0]
                if content_type not in ('audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/ogg'):
                    raise HTTPException(502, 'Dịch vụ không trả định dạng âm thanh được hỗ trợ.')
                audio = bytearray()
                async for chunk in result.aiter_bytes():
                    audio.extend(chunk)
                    if len(audio) > 50 * 1024 * 1024:
                        raise HTTPException(502, 'Âm thanh vượt giới hạn 50 MB.')
                if not audio:
                    raise HTTPException(502, 'Dịch vụ trả âm thanh rỗng.')
                return Response(bytes(audio), media_type=content_type, headers={'Cache-Control': 'no-store'})
    except httpx.HTTPError:
        raise HTTPException(502, 'Không kết nối được dịch vụ giọng. Kiểm tra mạng và cấu hình máy chủ.') from None


def clone_builtin(payload, settings):
    with tempfile.TemporaryDirectory(prefix='hmong-reference-') as folder:
        sample = Path(folder) / 'reference.wav'
        try:
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(settings['start']),
                            '-i', str(reference_path(payload.voice)), '-t', str(settings['end'] - settings['start']),
                            '-map', '0:a:0', '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(sample)],
                           check=True, capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            raise cloning_engine.CloningError('Không trích xuất được đoạn mẫu. Kiểm tra FFmpeg và tệp giọng gốc.') from None
        return cloning_engine.synthesize(payload.text, payload.speed, sample, settings['text'])


@app.post('/api/transcribe')
async def transcribe(request: Request, language: Literal['mww', 'vi', 'en'] = Query('mww')):
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > 50 * 1024 * 1024:
            raise HTTPException(413, 'Âm thanh tối đa 50 MB.')
    if not audio:
        raise HTTPException(422, 'Chọn hoặc thu âm trước khi nhận dạng.')
    url = os.getenv('HMONG_ASR_URL', '') if remote_enabled() else ''
    if not url:
        try:
            text = await run_in_threadpool(local_engine.transcribe, bytes(audio), language)
        except local_engine.EngineError as exc:
            raise HTTPException(503, str(exc)) from None
    else:
        if not url.startswith('https://'):
            raise HTTPException(503, 'Dịch vụ nhận dạng phải dùng HTTPS.')
        headers = {'Content-Type': 'application/octet-stream'}
        if token := os.getenv('HMONG_ASR_TOKEN'):
            headers['Authorization'] = f'Bearer {token}'
        try:
            async with httpx.AsyncClient(timeout=180, follow_redirects=False) as client:
                async with client.stream('POST', url, params={'language': language}, content=bytes(audio), headers=headers) as result:
                    if result.status_code != 200:
                        raise HTTPException(502, f'Dịch vụ nhận dạng trả mã {result.status_code}.')
                    body = bytearray()
                    async for chunk in result.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 1024 * 1024:
                            raise HTTPException(502, 'Kết quả nhận dạng vượt giới hạn 1 MB.')
                    import json
                    text = json.loads(body).get('text')
        except (httpx.HTTPError, ValueError, AttributeError):
            raise HTTPException(502, 'Không nhận được kết quả nhận dạng hợp lệ từ dịch vụ.') from None
    if not isinstance(text, str) or not text.strip() or len(text) > 50000:
        raise HTTPException(502, 'Kết quả nhận dạng rỗng hoặc vượt 50.000 ký tự.')
    return {'text': text, 'language': language, 'warning': 'Nhận dạng có thể sai dấu, từ và mốc câu. Hãy kiểm tra với người bản ngữ trước khi dùng.'}
