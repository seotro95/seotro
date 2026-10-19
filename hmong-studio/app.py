"""Hmong Studio: local audio workspace with an explicit TTS adapter contract."""
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from starlette.concurrency import run_in_threadpool
import local_engine

BASE = Path(__file__).resolve().parent
app = FastAPI(title='Hmong Studio', version='0.2.0')
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    dialect: Literal['mww', 'vi', 'en']
    voice: Literal['model-default', 'hmong-white-female', 'hmong-white-male'] = 'model-default'
    emotion: Literal['neutral', 'storytelling', 'warm', 'cheerful', 'sad'] = 'neutral'
    speed: float = Field(default=1, ge=0.5, le=2)


@app.get('/')
def index():
    return FileResponse(BASE / 'static/index.html')


@app.get('/api/status')
def status():
    remote = bool(os.getenv('HMONG_TTS_URL'))
    local = local_engine.availability()
    return {'tts_configured': remote or (local['dependencies'] and local['tts_models']['mww']),
            'dialects': list(local_engine.LANGUAGES), 'languages': local_engine.LANGUAGES,
            'remote_tts': remote, 'remote_asr': bool(os.getenv('HMONG_ASR_URL')),
            'cloning': remote and os.getenv('HMONG_TTS_CLONING') == '1',
            'emotions': remote and os.getenv('HMONG_TTS_EMOTIONS') == '1',
            'local': local,
            'message': 'Chọn ngôn ngữ và bộ xử lý. AI cục bộ cần cài thư viện, tải mô hình; Hmong Trắng cần mô hình đúng phương ngữ. Mẫu nam/nữ chỉ dùng tạo giọng khi dịch vụ hỗ trợ nhân bản.'}


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
