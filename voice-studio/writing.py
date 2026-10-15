"""Optional paid writing APIs. Keys stay in server memory; never return them."""
import os
import re
import threading

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

KEYS = {}
KEY_LOCK = threading.Lock()
ENV_KEYS = {'openai': ('OPENAI_API_KEY',), 'gemini': ('GEMINI_API_KEY', 'GOOGLE_API_KEY')}
DEFAULT_MODELS = {'openai': 'gpt-4.1-mini', 'gemini': 'gemini-2.5-flash'}


def get_key(provider):
    if provider not in ENV_KEYS:
        raise HTTPException(422, 'Chọn OpenAI hoặc Gemini.')
    with KEY_LOCK:
        return KEYS.get(provider) or next((os.environ[k] for k in ENV_KEYS[provider] if os.environ.get(k)), '')


class Connection(BaseModel):
    provider: str
    api_key: str = Field(min_length=1, max_length=512)


class WritingRequest(BaseModel):
    provider: str
    model: str = Field(default='', max_length=100)
    prompt: str = Field(min_length=1, max_length=20000)
    language: str = Field(default='vi', max_length=16)
    kind: str = Field(default='script', pattern='^(script|rewrite|outline)$')
    minutes: int = Field(default=5, ge=1, le=180)


async def request_api(method, url, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15)) as client:
            response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException:
        raise HTTPException(504, 'AI viết phản hồi quá lâu. Hãy thử yêu cầu ngắn hơn.') from None
    except httpx.RequestError:
        raise HTTPException(502, 'Không kết nối được dịch vụ AI. Kiểm tra mạng.') from None
    if response.is_error:
        descriptions = {401: 'API key không hợp lệ.', 403: 'API key hoặc khu vực chưa có quyền truy cập.', 404: 'Không tìm thấy model. Hãy kiểm tra tên model.', 429: 'Đã hết hạn mức hoặc vượt giới hạn yêu cầu. Kiểm tra thanh toán API.'}
        raise HTTPException(502, descriptions.get(response.status_code, f'Dịch vụ AI trả lỗi {response.status_code}.'))
    return response.json()


async def verify_connection(body):
    if body.provider not in ENV_KEYS or not body.api_key.strip():
        raise HTTPException(422, 'Chọn nhà cung cấp và nhập API key.')
    key = body.api_key.strip()
    if body.provider == 'openai':
        await request_api('GET', 'https://api.openai.com/v1/models', headers={'Authorization': f'Bearer {key}'})
    else:
        await request_api('GET', 'https://generativelanguage.googleapis.com/v1beta/models', headers={'x-goog-api-key': key})
    with KEY_LOCK:
        KEYS[body.provider] = key
    return {'connected': True, 'provider': body.provider}


async def generate(body):
    key = get_key(body.provider)
    if not key:
        raise HTTPException(503, 'Chưa kết nối API key. Kết nối trong mục AI viết kịch bản.')
    model = body.model.strip() or DEFAULT_MODELS[body.provider]
    if not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}', model):
        raise HTTPException(422, 'Tên model không hợp lệ.')
    if not body.prompt.strip():
        raise HTTPException(422, 'Nhập chủ đề hoặc yêu cầu viết.')
    task = {'script': 'Write narration ready to speak', 'rewrite': 'Rewrite the provided text for expressive narration', 'outline': 'Write a detailed chapter outline'}[body.kind]
    prompt = f'{task}. Output language: {body.language}. Target total length: {body.minutes} minutes, about 140 words/minute. For long works, produce a numbered chapter outline and the first chapter, and state clearly what remains. Never claim a short answer is a complete three-hour script. Return plain text, no tables. Mark occasional emphasis as **words**, and breathing pauses as [pause=0.8] (0–10 seconds). Do not put instructions to actors in brackets.\nUser brief:\n{body.prompt}'
    if body.provider == 'openai':
        data = await request_api('POST', 'https://api.openai.com/v1/responses', headers={'Authorization': f'Bearer {key}'}, json={'model': model, 'input': prompt, 'max_output_tokens': 8192})
        text = '\n'.join(block.get('text', '') for item in data.get('output', []) for block in item.get('content', []) if block.get('type') == 'output_text')
        incomplete = data.get('status') == 'incomplete'
    else:
        data = await request_api('POST', f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', headers={'x-goog-api-key': key}, json={'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': 8192}})
        candidates = data.get('candidates', [])
        text = '\n'.join(part.get('text', '') for part in (candidates[0].get('content', {}).get('parts', []) if candidates else []) if not part.get('thought'))
        incomplete = bool(candidates and candidates[0].get('finishReason') == 'MAX_TOKENS')
    if not text.strip():
        raise HTTPException(502, 'AI không trả nội dung văn bản. Thử điều chỉnh yêu cầu hoặc model.')
    return {'text': text.strip(), 'provider': body.provider, 'model': model, 'incomplete': incomplete, 'note': 'Kịch bản dài cần viết tiếp theo chương; thời lượng là mục tiêu ước tính.'}
