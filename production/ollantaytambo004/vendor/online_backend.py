"""Optional Edge Read Aloud integration; not the paid/official Azure Speech API."""
import asyncio
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import time

CATALOG = None


def catalog_file():
    root = Path(os.environ.get('MELO_VIET_ROOT', Path.home()/'.local/share/melo-viet-local'))
    folder = root/'models'; folder.mkdir(parents=True,exist_ok=True)
    return folder/'edge-voices.json'


async def fetch_catalog():
    import edge_tts
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy') or None
    voices = await asyncio.wait_for(edge_tts.list_voices(proxy=proxy),timeout=45)
    valid = [v for v in voices if all(isinstance(v.get(key),str) for key in ('ShortName','Locale','Gender','FriendlyName'))]
    if not valid:
        raise ValueError('Dịch vụ không trả về danh mục giọng hợp lệ.')
    return valid


def get_catalog(force=False):
    global CATALOG
    if CATALOG is not None and not force:
        return CATALOG
    cache = catalog_file()
    if not force and cache.is_file() and time.time()-cache.stat().st_mtime < 86400:
        try:
            data = json.loads(cache.read_text(encoding='utf-8'))
            if data and all(isinstance(v,dict) and all(k in v for k in ('ShortName','Locale','Gender','FriendlyName')) for v in data):
                CATALOG = data; return data
        except (OSError,ValueError):
            pass
    CATALOG = asyncio.run(fetch_catalog())
    # Different worker lanes can fetch together. A PID-specific temporary file is atomic.
    temporary = cache.with_name(cache.name+'.'+str(os.getpid())+'.partial')
    temporary.write_text(json.dumps(CATALOG,ensure_ascii=False),encoding='utf-8'); temporary.replace(cache)
    return CATALOG


async def download_audio(text, voice, output):
    import edge_tts
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy') or None
    error = None
    for attempt in range(3):
        try:
            speech = edge_tts.Communicate(text, voice, rate='+0%', volume='+0%', pitch='+0Hz',
                proxy=proxy, connect_timeout=15, receive_timeout=60)
            await asyncio.wait_for(speech.save(str(output)),timeout=120)
            return
        except Exception as caught:
            error = caught
            if attempt < 2:
                await asyncio.sleep(1.5 * (2**attempt))
    kind=type(error).__name__;status=getattr(error,'status',None)
    if status in {401,403}:
        help_text='Dịch vụ từ chối kết nối (HTTP '+str(status)+'). Kiểm tra ngày/giờ Windows và Ubuntu, kết nối mạng rồi làm mới danh mục. Danh sách giọng tải được chưa bảo đảm đường tạo âm thanh kết nối được.'
    elif 'Certificate' in kind or 'SSL' in kind:
        help_text='Lỗi chứng chỉ hoặc ngày/giờ hệ thống khi kết nối. Kiểm tra giờ Windows/Ubuntu và mạng; không tắt xác minh TLS.'
    elif 'Proxy' in kind or 'Connector' in kind:
        help_text='Không kết nối được dịch vụ/proxy từ Ubuntu WSL. Kiểm tra cấu hình mạng của WSL.'
    elif 'Timeout' in kind:
        help_text='Dịch vụ giọng đọc hết thời gian chờ. Thử lại hoặc dùng bộ đọc trên máy.'
    elif 'NoAudioReceived' in kind:
        help_text='Dịch vụ không trả về âm thanh cho giọng đã chọn. Làm mới danh mục và Nghe thử lại; có thể chọn giọng khác cùng tiếng.'
    else:
        help_text='Không tạo được giọng trực tuyến. Kiểm tra Internet, làm mới danh mục và thử lại.'
    detail=re.sub(r'https?://\S+|wss?://\S+','[địa chỉ dịch vụ]',str(error))[:200]
    raise RuntimeError(help_text+' ['+kind+'] '+detail)


def handle(request):
    if os.environ.get('HF_HUB_OFFLINE')=='1':
        raise ValueError('Đang ngoại tuyến; giọng Edge cần Internet.')
    all_voices = get_catalog(bool(request.get('refresh')))
    voices = [{'id':v['ShortName'],'name':v['FriendlyName'], 'locale':v['Locale'], 'gender':v['Gender']} for v in all_voices]
    if request['op']=='catalog':
        locales = {v['locale']:0 for v in voices}
        for v in voices:
            locales[v['locale']] += 1
        return {'voices':voices,'locales':locales,'provider':'Microsoft Edge qua edge-tts', 'model_load_seconds':0}
    voices = [v for v in voices if v['locale']==request['language']]
    if not voices:
        raise ValueError('Ngôn ngữ/quốc gia không còn trong danh mục giọng trực tuyến.')
    if request['op']=='voices':
        return {'voices':voices,'model_load_seconds':0}
    if request['op']!='render' or request.get('voice') not in {v['id'] for v in voices}:
        raise ValueError('Chọn giọng trực tuyến thực thuộc đúng ngôn ngữ/quốc gia.')
    text = request.get('text')
    if not isinstance(text,str) or not text.strip() or len(text)>1200 or '\x00' in text:
        raise ValueError('Mỗi đoạn trực tuyến cần 1–1.200 ký tự hợp lệ.')
    if not shutil.which('ffmpeg'):
        raise ValueError('Thiếu ffmpeg để giải mã âm thanh. Đóng tool và chạy CAP_NHAT.bat hoặc CAI_DAT.bat.')
    output = Path(request['output']); mp3 = output.with_suffix('.edge.mp3'); temporary = output.with_suffix('.edge.partial.wav')
    started = time.perf_counter()
    try:
        asyncio.run(download_audio(text,request['voice'],mp3))
        result = subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(mp3),
            '-ac','1','-ar','24000','-af','volume=0.95','-c:a','pcm_s16le',str(temporary)],capture_output=True,timeout=90)
        if result.returncode:
            raise RuntimeError('Không giải mã được âm thanh trực tuyến: '+result.stderr.decode('utf-8','replace')[-250:])
        import wave
        with wave.open(str(temporary),'rb') as audio:
            seconds = audio.getnframes()/audio.getframerate()
            if not seconds:
                raise RuntimeError('Dịch vụ trả về âm thanh rỗng.')
        temporary.replace(output)
    finally:
        mp3.unlink(missing_ok=True); temporary.unlink(missing_ok=True)
    return {'audio_seconds':seconds,'sample_rate':24000,'model_load_seconds':0,'voice':request['voice'],
            'engine':'Microsoft Edge trực tuyến','inference_and_save_seconds':time.perf_counter()-started}
