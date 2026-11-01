"""Native Azure Neural voices; explicit cloud configuration, no local fallback.

Only the fixed regional Speech API receives text. Keys stay outside jobs/history;
Windows persists them with DPAPI bound to the signed-in user.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.request
import wave
from xml.sax.saxutils import escape

REGIONS = ('southeastasia', 'eastasia', 'eastus', 'eastus2', 'westus', 'westus2', 'westus3',
           'centralus', 'northcentralus', 'southcentralus', 'westcentralus', 'canadacentral',
           'canadaeast', 'brazilsouth', 'northeurope', 'westeurope', 'francecentral', 'uksouth',
           'ukwest', 'germanywestcentral', 'switzerlandnorth', 'norwayeast', 'swedencentral',
           'australiaeast', 'australiasoutheast', 'japaneast', 'japanwest', 'koreacentral',
           'koreasouth', 'centralindia', 'southindia', 'westindia', 'uaenorth', 'southafricanorth',
           'qatarcentral', 'polandcentral', 'italynorth', 'israelcentral', 'spaincentral',
           'mexicocentral', 'indonesiacentral', 'newzealandnorth')
_GROUPS = (
    ('en-GB', 'en-GB', ('Ryan', 'Thomas', 'Oliver')),
    ('ko', 'ko-KR', ('InJoon', 'SunHi')),
    ('ru', 'ru-RU', ('Dmitry', 'Svetlana', 'Dariya')),
    ('ja', 'ja-JP', ('Keita', 'Daichi', 'Naoki')),
    ('fr', 'fr-FR', ('Henri', 'Denise', 'Eloise')),
    ('es', 'es-ES', ('Alvaro', 'Elvira', 'Ximena')),
    ('th', 'th-TH', ('Niwat', 'Premwadee')),
)
VOICES = tuple({'id': 'azure-' + locale + '-' + name, 'name': name + ' · ' + locale,
                'speaker': locale + '-' + name + 'Neural', 'locale': locale,
                'languages': [language], 'native_language': language.split('-')[0],
                'engine': 'azure', 'category': 'online', 'readonly': True,
                'description': 'Giọng Azure Neural bản ngữ · Internet · có thể tính phí',
                'requires_internet': True}
               for language, locale, names in _GROUPS for name in names)


class AzureSpeechError(RuntimeError):
    pass


def _validate(region, key):
    if region not in REGIONS or not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_+/=.-]{16,256}', key):
        raise ValueError('Kiểm tra vùng Azure và khóa Speech. Không nhập đường dẫn endpoint hoặc khóa có khoảng trắng.')
    return region, key


def _dpapi(data, protect):
    if os.name != 'nt':
        raise AzureSpeechError('Mã hóa khóa Windows chỉ chạy trên Windows.')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    args = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    fn.argtypes, fn.restype = args, wintypes.BOOL
    # CRYPTPROTECT_UI_FORBIDDEN, current Windows user; never machine-wide scope.
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise AzureSpeechError('Không mở được khóa Azure cho tài khoản Windows này. Nhập lại khóa trong tool.')
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(ctypes.cast(result.data, ctypes.c_void_p))


def _read(path, maximum=65536):
    if path.stat().st_size > maximum:
        raise ValueError('Bản ghi dịch vụ quá lớn.')
    return json.loads(path.read_text(encoding='utf-8'))


def _atomic(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.azure-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save_configuration(data, region, key):
    region, key = _validate(region, key.strip())
    payload = json.dumps({'region': region, 'key': key}).encode()
    if os.name == 'nt':
        record = {'schema': 1, 'protection': 'windows-dpapi',
                  'payload': base64.b64encode(_dpapi(payload, True)).decode('ascii')}
    else:
        # Development/non-Windows installations use a private 0600 file.
        record = {'schema': 1, 'protection': 'private-file', 'payload': base64.b64encode(payload).decode('ascii')}
    _atomic(Path(data)/'settings/azure-speech.json', record)
    (Path(data)/'settings/azure-voices.json').unlink(missing_ok=True)


def credentials(data):
    region, key = os.environ.get('AZURE_SPEECH_REGION'), os.environ.get('AZURE_SPEECH_KEY')
    if region or key:
        return _validate(region, key)
    try:
        path = Path(data)/'settings/azure-speech.json'
        record = _read(path, 8192)
        if record.get('schema') != 1:
            raise ValueError('Sai định dạng cấu hình Azure.')
        payload = base64.b64decode(record['payload'], validate=True)
        if record['protection'] == 'windows-dpapi':
            payload = _dpapi(payload, False)
        elif record['protection'] != 'private-file' or os.name == 'nt':
            raise ValueError('Chưa có khóa được mã hóa cho tài khoản Windows này.')
        value = json.loads(payload)
        return _validate(value['region'], value['key'])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise AzureSpeechError('Chưa có cấu hình Azure Speech hợp lệ. Nhập khóa và vùng dịch vụ trong tool.') from None


def _fingerprint(region, key):
    return hashlib.sha256((region + ':' + key).encode()).hexdigest()


def status(data):
    try:
        region, key = credentials(data)
    except (AzureSpeechError, ValueError):
        return {'configured': False, 'verified': False, 'region': None, 'available_voices': [],
                'message': 'Nhập khóa và vùng Azure Speech, sau đó kiểm tra kết nối.'}
    available, checked = [], None
    try:
        record = _read(Path(data)/'settings/azure-voices.json')
        checked = record['checked_at']
        if (record['fingerprint'] == _fingerprint(region, key) and type(checked) in {float, int}
                and 0 <= time.time() - checked < 86400):
            available = [v for v in record['voices'] if isinstance(v, str)]
        else:
            checked = None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        checked = None
    return {'configured': True, 'verified': checked is not None, 'region': region,
            'available_voices': available, 'checked_at': checked,
            'message': 'Đã kiểm tra danh sách giọng; tạo mẫu để xác nhận âm thanh và tốc độ.' if checked is not None
            else 'Đã có khóa; bấm Kiểm tra kết nối để xác nhận các giọng trong tài khoản.'}


def catalog(data):
    state = status(data)
    return [{**voice, 'ready': voice['speaker'] in state['available_voices'],
             'missing_reason': None if voice['speaker'] in state['available_voices'] else
             (state['message'] if not state['verified'] else 'Vùng/tài khoản Azure này chưa trả về giọng đã chọn. Kiểm tra vùng hoặc chọn giọng khác.')}
            for voice in VOICES]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise AzureSpeechError('Azure trả về chuyển hướng ngoài dự kiến; đã dừng để giữ khóa trong endpoint đã chọn.')


def _cancelled(cancel):
    if cancel is not None and Path(cancel).exists():
        raise InterruptedError('Đã dừng yêu cầu giọng trực tuyến.')


def _request(region, key, route, *, payload=None, maximum=32*1024**2, cancel=None):
    _validate(region, key)
    url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/{route}'
    headers = {'Ocp-Apim-Subscription-Key': key, 'User-Agent': 'VoiceStudio/1.13.0'}
    if payload is not None:
        headers.update({'Content-Type': 'application/ssml+xml; charset=utf-8',
                        'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm'})
    for attempt in range(3):
        _cancelled(cancel)
        request = urllib.request.Request(url, data=payload, headers=headers,
                                         method='POST' if payload is not None else 'GET')
        try:
            with urllib.request.build_opener(_NoRedirect()).open(request, timeout=30) as response:
                data = bytearray()
                started = time.monotonic()
                while True:
                    _cancelled(cancel)
                    block = response.read(65536)
                    if not block:
                        return bytes(data)
                    data.extend(block)
                    if len(data) > maximum or time.monotonic() - started > 90:
                        raise AzureSpeechError('Phản hồi Azure quá lớn hoặc quá lâu; chưa lưu âm thanh.')
        except urllib.error.HTTPError as error:
            code = error.code
            retry_after = error.headers.get('Retry-After', '1')
            error.close()
            if code in {429, 503} and attempt < 2:
                delay = min(5, max(1, int(retry_after))) if retry_after.isdigit() else 2
                until = time.monotonic() + delay
                while time.monotonic() < until:
                    _cancelled(cancel)
                    time.sleep(.1)
                continue
            message = {401: 'Khóa Azure không hợp lệ hoặc không khớp vùng.',
                       403: 'Tài khoản Azure chưa cho phép tạo giọng; kiểm tra quyền và hạn mức.',
                       429: 'Azure đang giới hạn yêu cầu hoặc hết hạn mức. Giảm số tác vụ và kiểm tra tài khoản.',
                       400: 'Azure từ chối yêu cầu giọng/ngôn ngữ. Kiểm tra lại danh sách giọng.',
                       404: 'Không tìm thấy dịch vụ Speech trong vùng đã chọn.'}.get(code,
                       'Dịch vụ Azure chưa đáp ứng được yêu cầu. Thử lại sau.')
            raise AzureSpeechError(message) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            # A timed-out POST may already have been billed. Never resubmit it
            # automatically or expose a raw response that could contain input.
            raise AzureSpeechError('Không kết nối được Azure Speech. Kiểm tra Internet và vùng dịch vụ; không tự gửi lại yêu cầu bị mất kết nối.') from None
    raise AzureSpeechError('Azure chưa đáp ứng được yêu cầu.')


def check_connection(data):
    region, key = credentials(data)
    # Clear stale readiness before a failed connection/authentication check.
    (Path(data)/'settings/azure-voices.json').unlink(missing_ok=True)
    raw = _request(region, key, 'voices/list', maximum=2*1024**2)
    try:
        records = json.loads(raw)
        if not isinstance(records, list):
            raise ValueError()
        # Accept only exact native locale and Neural model records. Never use a
        # different multilingual voice as an undisclosed replacement.
        available = {r.get('ShortName'): r for r in records if isinstance(r, dict)}
        names = [v['speaker'] for v in VOICES if v['speaker'] in available
                 and available[v['speaker']].get('Locale') == v['locale']
                 and available[v['speaker']].get('VoiceType') == 'Neural'
                 and available[v['speaker']].get('Status') != 'Deprecated']
    except (ValueError, TypeError, KeyError):
        raise AzureSpeechError('Danh sách giọng Azure không hợp lệ; chưa xác nhận giọng sẵn sàng.') from None
    _atomic(Path(data)/'settings/azure-voices.json', {'fingerprint': _fingerprint(region, key),
            'checked_at': time.time(), 'voices': names})
    return status(data)


def clear_configuration(data):
    for name in ('azure-speech.json', 'azure-voices.json'):
        (Path(data)/'settings'/name).unlink(missing_ok=True)
    return status(data)


def ssml(text, voice):
    if not isinstance(text, str) or not text.strip() or len(text) > 8000 or any(ord(c) < 32 and c not in '\t\n\r' for c in text):
        raise ValueError('Nội dung Azure rỗng, quá dài hoặc chứa ký tự không hợp lệ.')
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{voice["locale"]}">'
            f'<voice name="{voice["speaker"]}">{escape(text)}</voice></speak>').encode('utf-8')


def create_synthesizer(data, voice_id, language, cancel=None):
    voice = next((v for v in VOICES if v['id'] == voice_id), None)
    if voice is None or language not in voice['languages']:
        raise ValueError('Chọn đúng giọng Azure cho ngôn ngữ lời đọc.')
    if voice['speaker'] not in status(data)['available_voices']:
        raise AzureSpeechError('Giọng Azure chưa được xác nhận sẵn sàng. Kiểm tra kết nối trong tool.')
    region, key = credentials(data)
    def synthesize(text, output):
        raw = _request(region, key, 'v1', payload=ssml(text, voice), cancel=cancel)
        try:
            with wave.open(io.BytesIO(raw), 'rb') as audio:
                frames = audio.getnframes()
                if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 24000, 'NONE') or not frames:
                    raise ValueError()
                if len(audio.readframes(frames)) != frames * 2:
                    raise ValueError()
        except (ValueError, wave.Error, EOFError):
            raise AzureSpeechError('Azure không trả về WAV PCM đầy đủ; không thay bằng giọng khác.') from None
        _cancelled(cancel)
        Path(output).write_bytes(raw)
    return synthesize
