"""Hmong Studio: local audio workspace with an explicit TTS adapter contract."""
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Query, Form, UploadFile, File
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
import json
import clone_store
import cosy_engine
import voice_jobs
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
import local_engine

BASE = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app):
    yield
    await voice_jobs.shutdown()

app = FastAPI(title='Hmong Studio', version='0.4.0', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    dialect: Literal['mww', 'vi', 'en']
    voice: str = Field(default='model-default', max_length=80)
    emotion: Literal['neutral', 'storytelling', 'warm', 'cheerful', 'sad', 'review', 'advertising', 'news', 'meditation'] = 'neutral'
    speed: float = Field(default=1, ge=0.5, le=2)
    reference_text: str = Field(default='', max_length=2000)


@app.get('/')
def index():
    return FileResponse(BASE / 'static/index.html')


@app.get('/api/status')
def status():
    remote = bool(os.getenv('HMONG_TTS_URL'))
    local = local_engine.availability()
    cosy = cosy_engine.availability()
    return {'tts_configured': cosy['ready'] or remote or (local['dependencies'] and local['tts_models']['mww']),
            'dialects': list(local_engine.LANGUAGES), 'languages': local_engine.LANGUAGES,
            'remote_tts': remote, 'remote_asr': bool(os.getenv('HMONG_ASR_URL')),
            'cloning': cosy['ready'] or (remote and os.getenv('HMONG_TTS_CLONING') == '1'),
            'emotions': cosy['ready'] or (remote and os.getenv('HMONG_TTS_EMOTIONS') == '1'),
            'local': local,
            'custom_cloning': cosy['ready'] or bool(os.getenv('HMONG_CLONE_URL')),
            'local_cloning': cosy['ready'], 'cosy': cosy,
            'clone_styles': cosy['styles'] if cosy['ready'] else [x.strip() for x in os.getenv('HMONG_CLONE_STYLES', 'neutral').split(',')],
            'message': 'Bộ máy nhân bản Hmong cục bộ đã sẵn sàng. Chọn mẫu Nam/Nữ, nhập lời rồi bấm Tạo voice. Không cần micro hay bản chép mẫu.' if cosy['ready'] else cosy['reason']}


@app.get('/api/voices')
def voices():
    cloning = bool(os.getenv('HMONG_TTS_URL')) and os.getenv('HMONG_TTS_CLONING') == '1'
    return {'voices': [
        {'id': 'model-default', 'name': 'Giọng gốc của mô hình', 'gender': None, 'reference': None},
        *[{'id': f'hmong-white-{gender}', 'name': name, 'gender': gender,
           'reference': f'/static/voices/hmong-white-{gender}.mp3',
           'generation_configured': cloning}
          for gender, name in [('female', 'Hmong Trắng · Nữ'), ('male', 'Hmong Trắng · Nam')]]]}


@app.post('/api/speech')
async def speech(payload: Speech):
    if not payload.text.strip():
        raise HTTPException(422, 'Nhập lời đọc trước khi tạo giọng.')
    reference_voice = payload.voice.startswith('custom-') or payload.voice in {'hmong-white-female', 'hmong-white-male'}
    use_local_clone = reference_voice and (cosy_engine.availability()['ready'] or (not os.getenv('HMONG_CLONE_URL') and not os.getenv('HMONG_TTS_URL')))
    if use_local_clone:
        if payload.dialect != 'mww':
            raise HTTPException(422, 'Bộ máy nhân bản này dành cho Hmong Trắng. Chọn Hmong Trắng trước khi tạo voice.')
        if payload.voice.startswith('custom-'):
            _, reference = clone_store.get(payload.voice)
        else:
            reference = BASE / 'static' / 'voices' / (payload.voice + '.mp3')
        try:
            data = await run_in_threadpool(cosy_engine.synthesize, payload.text, reference, payload.emotion, payload.speed)
            return Response(data, media_type='audio/wav', headers={'Cache-Control': 'no-store'})
        except cosy_engine.EngineError as exc:
            raise HTTPException(503, str(exc)) from None
    if payload.voice.startswith('custom-') or (payload.voice in {'hmong-white-female', 'hmong-white-male'} and os.getenv('HMONG_CLONE_URL')):
        return await clone_speech(payload)
    if payload.voice not in {'model-default', 'hmong-white-female', 'hmong-white-male'}:
        raise HTTPException(422, 'Giọng không hợp lệ.')
    url = os.getenv('HMONG_TTS_URL', '')
    if not url:
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


@app.post('/api/transcribe')
async def transcribe(request: Request, language: Literal['mww', 'vi', 'en'] = Query('mww')):
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > 50 * 1024 * 1024:
            raise HTTPException(413, 'Âm thanh tối đa 50 MB.')
    if not audio:
        raise HTTPException(422, 'Chọn hoặc thu âm trước khi nhận dạng.')
    url = os.getenv('HMONG_ASR_URL', '')
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


@app.get('/api/clones')
def list_clones():
    return {'voices': clone_store.list_voices()}


@app.post('/api/clones', status_code=201)
async def add_clone(file: UploadFile = File(...), name: str = Form(min_length=1, max_length=80),
                    transcript: str = Form(default='', max_length=2000), consent: bool = Form(False)):
    if not consent:
        raise HTTPException(422, 'Cần xác nhận bạn có quyền nhân bản mẫu giọng này.')
    raw = bytearray()
    while chunk := await file.read(64 * 1024):
        raw.extend(chunk)
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(413, 'Mẫu giọng tối đa 20 MB.')
    return await run_in_threadpool(clone_store.create, bytes(raw), name, transcript)


@app.get('/api/clones/{voice_id}/sample')
def clone_sample(voice_id: str):
    _, path = clone_store.get(voice_id)
    return FileResponse(path, media_type='audio/wav', headers={'Cache-Control': 'no-store'})


@app.delete('/api/clones/{voice_id}', status_code=204)
def remove_clone(voice_id: str):
    clone_store.delete(voice_id)
    return Response(status_code=204)


async def clone_speech(payload):
    builtin = payload.voice in {'hmong-white-female', 'hmong-white-male'}
    if builtin:
        path = BASE / 'static' / 'voices' / (payload.voice + '.mp3')
        metadata = {'transcript': payload.reference_text.strip()}
        if not metadata['transcript']:
            raise HTTPException(422, 'Nhập bản chép đúng lời trong mẫu nam/nữ đã chọn. Không dùng kịch bản mới làm bản chép mẫu.')
    else:
        metadata, path = clone_store.get(payload.voice)
    url = os.getenv('HMONG_CLONE_URL', '')
    if not url:
        raise HTTPException(503, 'Đã lưu mẫu giọng. Chưa có bộ máy nhân bản Hmong Trắng; mẫu âm thanh không tự trở thành mô hình AI.')
    if not metadata.get('transcript', '').strip():
        raise HTTPException(422, 'Dịch vụ ngoài cần bản chép mẫu chính xác; CosyVoice cục bộ không yêu cầu bản chép.')
    if payload.dialect != 'mww':
        raise HTTPException(422, 'Mẫu giọng này dành cho Hmong Trắng.')
    if not url.startswith('https://'):
        raise HTTPException(503, 'Dịch vụ nhân bản phải dùng HTTPS.')
    if 'mww' not in os.getenv('HMONG_CLONE_LANGUAGES', '').split(','):
        raise HTTPException(503, 'Chưa xác nhận bộ máy nhân bản hỗ trợ Hmong Trắng (mww).')
    if payload.emotion not in [x.strip() for x in os.getenv('HMONG_CLONE_STYLES', 'neutral').split(',')]:
        raise HTTPException(422, 'Bộ máy chưa hỗ trợ kiểu đọc này. Chọn Tự nhiên hoặc cấu hình đúng năng lực dịch vụ.')
    headers = {}
    if token := os.getenv('HMONG_CLONE_TOKEN'):
        headers['Authorization'] = 'Bearer ' + token
    try:
        async with httpx.AsyncClient(timeout=180, follow_redirects=False) as client:
            with path.open('rb') as sample:
                async with client.stream('POST', url, headers=headers,
                    data={'payload': json.dumps({**payload.model_dump(), 'reference_text': metadata['transcript']}, ensure_ascii=False)},
                    files={'reference_audio': (path.name, sample, 'audio/mpeg' if builtin else 'audio/wav')}) as result:
                    if result.status_code != 200:
                        raise HTTPException(502, f'Dịch vụ nhân bản trả mã {result.status_code}.')
                    content_type = result.headers.get('content-type', '').split(';')[0]
                    if content_type not in ('audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/ogg'):
                        raise HTTPException(502, 'Dịch vụ nhân bản không trả âm thanh hợp lệ.')
                    audio = bytearray()
                    async for chunk in result.aiter_bytes():
                        audio.extend(chunk)
                        if len(audio) > 50 * 1024 * 1024:
                            raise HTTPException(502, 'Âm thanh vượt 50 MB.')
                    if not audio:
                        raise HTTPException(502, 'Dịch vụ trả âm thanh rỗng.')
                    return Response(bytes(audio), media_type=content_type, headers={'Cache-Control': 'no-store'})
    except httpx.HTTPError:
        raise HTTPException(502, 'Không kết nối được bộ máy nhân bản giọng.') from None


@app.post('/api/speech/jobs', status_code=202)
async def create_speech_job(payload: Speech):
    if not payload.text.strip():
        raise HTTPException(422, 'Nhập lời đọc trước khi tạo voice.')
    return voice_jobs.create(payload.model_dump())


@app.get('/api/speech/jobs/{job_id}')
async def speech_job(job_id: str):
    return voice_jobs.view(voice_jobs.get(job_id))


@app.post('/api/speech/jobs/{job_id}/stop')
async def stop_speech_job(job_id: str):
    return await voice_jobs.cancel(job_id)


@app.get('/api/speech/jobs/{job_id}/audio')
async def speech_job_audio(job_id: str):
    job = voice_jobs.get(job_id)
    if job['status'] != 'completed':
        raise HTTPException(409, 'Chưa có voice hoàn tất để tải.')
    return FileResponse(Path(job['temp'].name) / 'audio.bin', media_type=job['media_type'], headers={'Cache-Control': 'no-store'})
