import asyncio,hashlib,json,os,sys,threading
from pathlib import Path
from render_common import R,PROFILES,digest
LOCAL=threading.local()
def configure(locale):
 import edge_tts,edge_tts.communicate,edge_tts.voices
 for module in [edge_tts.communicate,edge_tts.voices]:
  if os.environ.get('SSL_CERT_FILE'):module._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
 sys.path.insert(0,str(R.parent/'melo45'));import online_backend
 voice=PROFILES[locale]['voice_id'];catalog={v['ShortName']:v for v in online_backend.get_catalog()}
 assert catalog[voice]['Locale']==locale and catalog[voice]['Gender']=='Male'
 async def download(text,voice,output):
  for attempt in range(5):
   try:
    async def receive():
     words=[];stream=edge_tts.Communicate(text,voice,rate=LOCAL.rate,volume='+0%',pitch='+0Hz',boundary='WordBoundary',proxy=os.environ.get('HTTPS_PROXY'),connect_timeout=20,receive_timeout=60)
     with Path(output).open('wb') as f:
      async for chunk in stream.stream():
       if chunk['type']=='audio':f.write(chunk['data'])
       elif chunk['type']=='WordBoundary':words.append(chunk)
     assert Path(output).stat().st_size>0 and words;Path(output).with_suffix('.words.json').write_text(json.dumps(words,ensure_ascii=False))
    await asyncio.wait_for(receive(),timeout=150);return
   except Exception as e:
    if getattr(e,'status',None) in [401,403,429]:raise
    print('TTS_TRANSIENT',locale,type(e).__name__,attempt+1,'of5',flush=True)
    if attempt==4:raise
    await asyncio.sleep([5,15,30,60][attempt])
 online_backend.download_audio=download
 return online_backend
BACKENDS={}
def request(locale,text,path,rate):
 if locale not in BACKENDS:BACKENDS[locale]=configure(locale)
 assert 0<len(text)<=1200
 LOCAL.rate=rate;voice=PROFILES[locale]['voice_id'];sig=hashlib.sha256((text+'\0'+voice+'\0'+rate).encode()).hexdigest();meta=path.with_suffix('.request.json')
 if path.exists() and meta.exists():
  j=json.loads(meta.read_text())
  if j['request_signature']==sig and j['sha256']==digest(path):return json.loads(path.with_suffix('.edge.words.json').read_text())
 BACKENDS[locale].handle({'op':'render','language':locale,'voice':voice,'text':text,'output':str(path)})
 words=json.loads(path.with_suffix('.edge.words.json').read_text());meta.write_text(json.dumps({'request_signature':sig,'sha256':digest(path),'voice_id':voice,'rate':rate}))
 return words
