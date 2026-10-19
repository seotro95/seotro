"""Hmong Studio: local audio workspace with an explicit TTS adapter contract."""
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

BASE = Path(__file__).resolve().parent
app = FastAPI(title='Hmong Studio')
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    dialect: Literal['mww']
    voice: Literal['hmong-white-female', 'hmong-white-male'] = 'hmong-white-female'
    speed: float = Field(default=1, ge=0.5, le=2)


@app.get('/')
def index():
    return FileResponse(BASE / 'static/index.html')


@app.get('/api/status')
def status():
    configured = bool(os.getenv('HMONG_TTS_URL'))
    return {'tts_configured': configured, 'dialects': ['mww'],
            'message': 'Đã cấu hình bộ chuyển tiếp; cần kiểm chứng giọng với người bản ngữ.' if configured else
            'Chưa kết nối mô hình Hmong. Bạn vẫn có thể thu âm, biên tập và xuất WAV.'}


@app.post('/api/speech')
async def speech(payload: Speech):
    if not payload.text.strip():
        raise HTTPException(422, 'Nhập lời đọc trước khi tạo giọng.')
    url = os.getenv('HMONG_TTS_URL', '')
    if not url:
        raise HTTPException(503, 'Chưa cấu hình HMONG_TTS_URL cho dịch vụ đọc Hmong.')
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
