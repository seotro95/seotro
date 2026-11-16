#!/usr/bin/env python3
"""Short read-only Edge voice health diagnostic; does not create full narration."""
import asyncio
import difflib
import json
import os
from pathlib import Path
import time
import unicodedata
import edge_tts
import edge_tts.communicate
import edge_tts.voices

ROOT=Path(__file__).resolve().parent
OUT=Path('outputs/voice_health')
CASES=[('en','en-US','en-US-AndrewNeural'),('sv','sv-SE','sv-SE-MattiasNeural'),
       ('nl','nl-NL','nl-NL-MaartenNeural'),('no','nb-NO','nb-NO-FinnNeural'),
       ('da','da-DK','da-DK-JeppeNeural'),('fi','fi-FI','fi-FI-HarriNeural'),
       ('en','en-US','en-US-AndrewMultilingualNeural')]

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',text).casefold() if c.isalnum())

def first_text(language):
    from render_voices import extract_rows
    path=ROOT/'script_master.json' if language=='en' else ROOT/'translations'/f'{language}.json'
    return extract_rows(json.loads(path.read_text(encoding='utf-8-sig')),language)[1]

async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if os.environ.get('SSL_CERT_FILE'):
        for module in (edge_tts.communicate,edge_tts.voices):
            module._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
    proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    catalogue={}
    catalogue_error=None
    try:
        catalogue={v['ShortName']:v for v in await asyncio.wait_for(edge_tts.list_voices(proxy=proxy),timeout=25)}
    except Exception as error:
        catalogue_error={'type':type(error).__name__,'message':str(error)}
    report={'diagnostic_only':True,'full_narration_generated':False,'single_attempt_per_voice_and_boundary':True,
            'timeout_seconds':25,'catalogue_error':catalogue_error,'results':[]}
    tests=[(language,locale,voice,boundary) for language,locale,voice in CASES for boundary in ('SentenceBoundary','WordBoundary')]
    for language,locale,voice,boundary in tests:
        text=first_text(language)
        path=OUT/(voice+'_'+boundary+'.mp3')
        words=[]
        result={'language':language,'locale':locale,'voice_id':voice,'boundary':boundary,'source_text':text,
                'catalogue_entry':catalogue.get(voice),'audio_bytes':0,'metadata_count':0,
                'normalized_coverage':0,'complete':False}
        started=time.monotonic()
        try:
            stream=edge_tts.Communicate(text,voice,rate='+0%',volume='+0%',pitch='+0Hz',
                boundary=boundary,proxy=proxy,connect_timeout=15,receive_timeout=20)
            async def receive():
                with path.open('wb') as audio:
                    async for chunk in stream.stream():
                        if chunk['type']=='audio':audio.write(chunk['data'])
                        elif chunk['type'] in ('WordBoundary','SentenceBoundary'):words.append(chunk)
            await asyncio.wait_for(receive(),timeout=25)
            expected=normalized(text);observed=normalized(''.join(w['text'] for w in words))
            ratio=difflib.SequenceMatcher(None,expected,observed,autojunk=False).ratio()
            result.update(audio_bytes=path.stat().st_size,metadata_count=len(words),
                normalized_coverage=ratio,observed_words=''.join(w['text'] for w in words))
            result['complete']=bool(result['audio_bytes'] and words and
                (expected==observed or (ratio>=.97 and expected[:16]==observed[:16] and expected[-24:]==observed[-24:])))
        except Exception as error:
            result['error']={'type':type(error).__name__,'message':str(error),'status':getattr(error,'status',None)}
            result['audio_bytes']=path.stat().st_size if path.exists() else 0
            result['metadata_count']=len(words)
        result['elapsed_seconds']=round(time.monotonic()-started,3)
        report['results'].append(result)
        (OUT/'HEALTH_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('HEALTH_RESULT '+json.dumps(result,ensure_ascii=False),flush=True)
    print('HEALTH_DIAGNOSTIC_FINISHED',flush=True)

if __name__=='__main__':
    asyncio.run(main())
