"""Optional online services. Chat credentials exist only during each request."""
from __future__ import annotations
import asyncio
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from urllib.request import getproxies, proxy_bypass
import httpx

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('VIDEO_STUDIO_DATA', str(ROOT / 'data'))).resolve()
CATALOG_LOCK = threading.Lock()
DEFAULT_VOICES = [
    {'id':'vi-VN-HoaiMyNeural','name':'Hoài My · Nữ · vi-VN','language':'vi','locale':'vi-VN'},
    {'id':'vi-VN-NamMinhNeural','name':'Nam Minh · Nam · vi-VN','language':'vi','locale':'vi-VN'},
    {'id':'en-US-AriaNeural','name':'Aria · Nữ · en-US','language':'en','locale':'en-US'},
    {'id':'en-US-GuyNeural','name':'Guy · Nam · en-US','language':'en','locale':'en-US'},
]


def edge_module():
    import edge_tts
    # Keep certificate verification; include the configured enterprise CA bundle.
    bundle = os.environ.get('SSL_CERT_FILE')
    if bundle and Path(bundle).is_file():
        import edge_tts.voices
        import edge_tts.communicate
        edge_tts.voices._SSL_CTX.load_verify_locations(cafile=bundle)
        edge_tts.communicate._SSL_CTX.load_verify_locations(cafile=bundle)
    return edge_tts


def normalize_voices(items):
    if not isinstance(items, list) or len(items) > 5000:
        raise ValueError('Danh mục giọng không hợp lệ.')
    voices = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        identifier, locale = item.get('ShortName', ''), item.get('Locale', '')
        if not isinstance(identifier, str) or not isinstance(locale, str):
            continue
        if not re.fullmatch(r'[a-z]{2,3}-[A-Za-z0-9-]{2,30}', locale):
            continue
        if not re.fullmatch(r'[A-Za-z0-9-]{5,100}Neural', identifier) or not identifier.startswith(locale + '-'):
            continue
        gender = {'Female':'Nữ','Male':'Nam'}.get(item.get('Gender'), '')
        name = identifier[len(locale)+1:].removesuffix('Neural')
        voices[identifier] = {'id':identifier,'name':f'{name} · {gender} · {locale}', 'gender':item.get('Gender', ''),
                              'language':locale.split('-')[0],'locale':locale}
    if not voices:
        raise ValueError('Danh mục giọng trống; giữ lại danh mục cũ.')
    return sorted(voices.values(), key=lambda v: (v['language'] != 'vi', v['locale'], v['id']))


def voice_catalog():
    try:
        result = json.loads((DATA / 'edge-voices.json').read_text(encoding='utf-8'))
        # Revalidate cached metadata before it reaches the synthesis service.
        voices = normalize_voices([{'ShortName':v['id'],'Locale':v['locale'], 'Gender':v.get('gender','')} for v in result['voices']])
        if any(not isinstance(result.get(key), (int, float)) or not math.isfinite(result[key]) or result[key] < 0
               for key in ('updated','checked')) or not isinstance(result.get('message'), str):
            raise ValueError('Metadata cache không hợp lệ.')
        return {'voices':voices, 'updated':result['updated'], 'checked':result['checked'], 'message':result['message'][:500]}
    except (OSError, ValueError, KeyError, TypeError):
        return {'voices':DEFAULT_VOICES, 'updated':0, 'checked':0,
                'message':'Danh mục khởi đầu. Làm mới để lấy các giọng hiện có từ Microsoft Edge.'}


def sync_voices(force=False):
    with CATALOG_LOCK:
        current = voice_catalog()
        if not force and time.time() - current.get('checked', 0) < 86400:
            return current
        async def fetch():
            return await asyncio.wait_for(edge_module().list_voices(), timeout=25)
        try:
            voices = normalize_voices(asyncio.run(fetch()))
            result = {'voices':voices,'updated':time.time(), 'checked':time.time(),
                      'message':f'Đã làm mới {len(voices)} giọng Microsoft Edge. Dịch vụ online, không cần API key.'}
        except Exception:
            result = {**current,'checked':time.time(),
                      'message':'Chưa kết nối được kho giọng Edge. Đang giữ danh mục cũ; bạn vẫn có thể dùng Piper offline.'}
        DATA.mkdir(parents=True, exist_ok=True)
        temporary = DATA / 'edge-voices.tmp'
        temporary.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
        temporary.replace(DATA / 'edge-voices.json')
        return result


def speak_edge(text, voice, output, speed=1):
    if voice not in {v['id'] for v in voice_catalog()['voices']}:
        raise ValueError('Giọng Edge chưa có trong danh mục. Hãy làm mới danh sách.')
    async def synthesize():
        proxy = None if proxy_bypass('speech.platform.bing.com') else getproxies().get('https')
        await asyncio.wait_for(edge_module().Communicate(text, voice, rate=f'{round((speed-1)*100):+d}%',
                                                        proxy=proxy).save(str(output)), timeout=180)
    try:
        asyncio.run(synthesize())
    except Exception:
        Path(output).unlink(missing_ok=True)
        raise ValueError('Không tạo được giọng Edge. Kiểm tra mạng hoặc chọn Piper offline; dịch vụ có thể giới hạn truy cập.') from None


def chat(provider, key, model, messages):
    if not key.strip():
        raise ValueError('Nhập API key trong ô kết nối, hoặc dùng nút mở trang chat không cần key.')
    if provider not in ('openai','gemini') or not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', model):
        raise ValueError('Nhà cung cấp hoặc tên model không hợp lệ.')
    if provider == 'openai':
        url = 'https://api.openai.com/v1/responses'
        headers = {'Authorization':'Bearer ' + key.strip()}
        body = {'model':model,'input':messages,'max_output_tokens':2048,'store':False}
    else:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        headers = {'x-goog-api-key':key.strip()}
        body = {'contents':[{'role':'model' if m['role']=='assistant' else 'user',
                             'parts':[{'text':m['content']}]} for m in messages],
                'generationConfig':{'maxOutputTokens':2048}}
    try:
        with httpx.Client(timeout=httpx.Timeout(90, connect=15), follow_redirects=False) as client:
            response = client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            reasons = {401:'API key không hợp lệ.',403:'Tài khoản hoặc mạng chưa được phép truy cập.',
                       404:'Không tìm thấy model. Kiểm tra tên model và quyền truy cập.',
                       429:'Hết hạn mức hoặc dịch vụ đang giới hạn lượt gọi.'}
            raise ValueError(reasons.get(response.status_code, f'Dịch vụ chat báo lỗi HTTP {response.status_code}.'))
        data = response.json()
        if provider == 'openai':
            answer = '\n'.join(part['text'] for item in data.get('output', [])
                               for part in item.get('content', []) if part.get('type') == 'output_text')
        else:
            answer = '\n'.join(part['text'] for candidate in data.get('candidates', [])[:1]
                               for part in candidate.get('content', {}).get('parts', [])
                               if 'text' in part and not part.get('thought'))
        if not answer.strip():
            raise ValueError('Dịch vụ chưa trả nội dung. Thử yêu cầu khác hoặc kiểm tra model.')
        return answer
    except (httpx.HTTPError, KeyError, TypeError, AttributeError, json.JSONDecodeError):
        raise ValueError('Không kết nối được dịch vụ chat. Kiểm tra mạng, API key và tên model.') from None
