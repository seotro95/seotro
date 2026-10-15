"""Local Ollama writing by default, optional keyed cloud providers."""
import os
import re
import threading

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

KEYS = {}
KEY_LOCK = threading.Lock()
ENV_KEYS = {'openai': ('OPENAI_API_KEY',), 'gemini': ('GEMINI_API_KEY', 'GOOGLE_API_KEY')}
DEFAULT_MODELS = {'ollama': 'qwen3:4b', 'openai': 'gpt-4.1-mini', 'gemini': 'gemini-2.5-flash'}


def get_key(provider):
    if provider not in ENV_KEYS:
        raise HTTPException(422, 'Chọn OpenAI hoặc Gemini.')
    with KEY_LOCK:
        return KEYS.get(provider) or next((os.environ[k] for k in ENV_KEYS[provider] if os.environ.get(k)), '')


class Connection(BaseModel):
    provider: str = 'ollama'
    api_key: str = Field(default='', max_length=512)


class WritingRequest(BaseModel):
    provider: str = 'ollama'
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
    if body.provider == 'ollama':
        status = await local_status()
        return {'connected': True, 'provider': 'ollama', **status}
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
    if body.provider not in DEFAULT_MODELS:
        raise HTTPException(422, 'Chọn Ollama, OpenAI hoặc Gemini.')
    key = '' if body.provider == 'ollama' else get_key(body.provider)
    if body.provider != 'ollama' and not key:
        raise HTTPException(503, 'Chưa kết nối API key. Kết nối trong mục AI viết kịch bản.')
    model = body.model.strip() or DEFAULT_MODELS[body.provider]
    if not re.fullmatch(r'(?:[a-zA-Z0-9._-]+/)*[a-zA-Z0-9._-]+(?::[a-zA-Z0-9._-]+)?' if body.provider == 'ollama' else r'[a-zA-Z0-9._-]{1,100}', model):
        raise HTTPException(422, 'Tên model không hợp lệ.')
    if not body.prompt.strip():
        raise HTTPException(422, 'Nhập chủ đề hoặc yêu cầu viết.')
    task = {'script': 'Write narration ready to speak', 'rewrite': 'Rewrite the provided text for expressive narration', 'outline': 'Write a detailed chapter outline'}[body.kind]
    prompt = f'{task}. Output language: {body.language}. Target total length: {body.minutes} minutes, about 140 words/minute. For long works, produce a numbered chapter outline and the first chapter, and state clearly what remains. Respect explicit word/sentence limits in the brief over the duration target. Never claim a short answer is a complete three-hour script. Return plain text, no tables. Mark occasional emphasis as **words**, and breathing pauses as [pause=0.8] (0–10 seconds). Never wrap pause markers in emphasis. Avoid leading/trailing pauses. Do not put instructions to actors in brackets.\nUser brief:\n{body.prompt}'
    if body.provider == 'ollama':
        if 'cloud' in model.lower():
            raise HTTPException(422, 'Chế độ cục bộ chỉ dùng mô hình tải về máy, không dùng model cloud.')
        status = await local_status()
        if model not in status['models'] and model + ':latest' not in status['models']:
            raise HTTPException(503, f'Chưa tải model {model}. Chạy setup_local_writer.bat hoặc ollama pull với model này.')
        data = await request_local('/api/chat', {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False, 'think': False, 'keep_alive': '0s', 'options': {'num_ctx': 8192, 'num_predict': 4096, 'temperature': 0.7}})
        text = data.get('message', {}).get('content', '')
        incomplete = data.get('done_reason') == 'length'
    elif body.provider == 'openai':
        data = await request_api('POST', 'https://api.openai.com/v1/responses', headers={'Authorization': f'Bearer {key}'}, json={'model': model, 'input': prompt, 'max_output_tokens': 8192})
        text = '\n'.join(block.get('text', '') for item in data.get('output', []) for block in item.get('content', []) if block.get('type') == 'output_text')
        incomplete = data.get('status') == 'incomplete'
    else:
        data = await request_api('POST', f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', headers={'x-goog-api-key': key}, json={'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': 8192}})
        candidates = data.get('candidates', [])
        text = '\n'.join(part.get('text', '') for part in (candidates[0].get('content', {}).get('parts', []) if candidates else []) if not part.get('thought'))
        incomplete = bool(candidates and candidates[0].get('finishReason') == 'MAX_TOKENS')
    text = re.sub(r'\*\*\s*(\[pause=\d+(?:\.\d+)?\])\s*\*\*', r'\1', text)
    if not re.sub(r'\[pause=\d+(?:\.\d+)?\]|\*\*', '', text).strip():
        raise HTTPException(502, 'AI không trả nội dung văn bản. Thử điều chỉnh yêu cầu hoặc model.')
    return {'text': text.strip(), 'provider': body.provider, 'model': model, 'incomplete': incomplete, 'note': 'Kịch bản dài cần viết tiếp theo chương; thời lượng là mục tiêu ước tính.'}


async def request_local(path, payload=None):
    # A fixed loopback endpoint prevents accidentally sending a brief to an external host.
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(900, connect=2)) as client:
            response = await client.request('GET' if payload is None else 'POST', 'http://127.0.0.1:11434' + path, json=payload)
    except httpx.TimeoutException:
        raise HTTPException(504, 'AI cục bộ phản hồi quá lâu. Giảm độ dài yêu cầu hoặc chọn model nhỏ hơn.') from None
    except httpx.RequestError:
        raise HTTPException(503, 'Chưa mở Ollama. Cài/mở Ollama rồi chạy setup_local_writer.bat. Không cần API key.') from None
    if response.is_error:
        raise HTTPException(502, f'Ollama trả lỗi {response.status_code}. Kiểm tra model đã tải và RAM trống.')
    return response.json()


async def local_status():
    data = await request_local('/api/tags')
    models = [m['name'] for m in data.get('models', []) if isinstance(m.get('name'), str) and 'cloud' not in m['name'].lower() and not m.get('remote_host')]
    return {'connected': True, 'models': models, 'default_model': DEFAULT_MODELS['ollama'], 'requires_key': False}
