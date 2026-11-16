"""Complete-speech transport validation adapted from the successful Upano pipeline.
Original: https://github.com/seotro95/seotro/blob/2f1ab371cacc140d180966bfc447c36cc11dfc0c/upano-moi011/online_transport.py
The original Melo backend source remains unmodified; its download transport is wrapped.
"""
import asyncio
import difflib
import json
import os
from email.utils import parsedate_to_datetime
import time
from pathlib import Path
import unicodedata

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())

class IncompleteSpeechError(RuntimeError):
    pass

def configure(backend):
    import edge_tts
    import edge_tts.communicate
    import edge_tts.voices
    if os.environ.get('SSL_CERT_FILE'):
        for module in (edge_tts.communicate, edge_tts.voices):
            module._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
    async def download(text, voice, output):
        error = None
        for attempt in range(8):
            try:
                words = []
                stream = edge_tts.Communicate(text, voice, rate='+0%', volume='+0%', pitch='+0Hz',
                    boundary='WordBoundary', proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'),
                    connect_timeout=20, receive_timeout=60)
                async def receive():
                    with Path(output).open('wb') as target:
                        async for part in stream.stream():
                            if part['type'] == 'audio':
                                target.write(part['data'])
                            elif part['type'] == 'WordBoundary':
                                words.append(part)
                await asyncio.wait_for(receive(), timeout=150)
                expected = normalized(text)
                observed = normalized(''.join(w['text'] for w in words))
                ratio = difflib.SequenceMatcher(None, expected, observed, autojunk=False).ratio()
                edges = observed[:16] == expected[:16] and observed[-24:] == expected[-24:]
                if not words or not expected or not (observed == expected or (ratio >= .97 and edges)):
                    raise IncompleteSpeechError(f'Incomplete returned speech: coverage={ratio:.5f}')
                Path(output).with_suffix('.words.json').write_text(json.dumps({
                    'verified': True, 'coverage_ratio': ratio, 'expected': expected, 'observed': observed,
                    'words': words}, ensure_ascii=False), encoding='utf-8')
                return
            except Exception as caught:
                error = caught
                status=getattr(caught,'status',None)
                if status in (401,403):
                    raise
                print('TTS_RETRY',voice,type(caught).__name__,attempt+1,'of8',flush=True)
                if attempt<7:
                    delay=(2,4,8,12,20,30,45)[attempt]
                    if status==429:
                        retry_after=getattr(caught,'headers',{}).get('Retry-After') if getattr(caught,'headers',None) else None
                        if retry_after:
                            try:
                                delay=max(delay,float(retry_after))
                            except ValueError:
                                try:delay=max(delay,parsedate_to_datetime(retry_after).timestamp()-time.time())
                                except (TypeError,ValueError,OverflowError):pass
                    await asyncio.sleep(max(0,delay))
        if type(error).__name__ not in ('NoAudioReceived','IncompleteSpeechError'):
            raise error
        raise IncompleteSpeechError('No complete narration received; partial audio rejected.') from error
    backend.download_audio = download
    return backend
