"""Resume missing Andrew cues with two independent backend requests at a time."""
import os
os.environ['MELO_VIET_ROOT']='/workspace/restored-mustang/work/melo-runtime'
os.environ.pop('HF_HUB_OFFLINE',None)
os.environ.pop('TRANSFORMERS_OFFLINE',None)
import hashlib,json,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import soundfile as sf
from cloud_edge_trust import configure
configure()
sys.path.insert(0,'/workspace/restored-mustang/work/melo-source')
from online_backend import get_catalog,handle
ROOT=Path(__file__).resolve().parents[1]
profile=next(x for x in json.loads((ROOT/'VOICE_PROFILES.json').read_text())['profiles'] if x['language']=='en')
rows=json.loads((ROOT/'scripts/en.json').read_text());cache=ROOT/'scratch/en';cache.mkdir(exist_ok=True,parents=True)
get_catalog()

def render(row):
 n=row['scene'];text=row['text'];voice=profile['voice_id']
 key=hashlib.sha256((voice+profile['engine']+text+str(row['duration_seconds'])).encode()).hexdigest()
 raw=cache/f'{n:03d}-raw.wav';stamp=cache/f'{n:03d}.sha256'
 if raw.exists() and stamp.exists() and stamp.read_text()==key:return n,'cached'
 temporary=cache/f'{n:03d}-prefetch.wav'
 for attempt in range(4):
  try:
   handle({'op':'render','language':'en-US','voice':voice,'text':text,'output':str(temporary)})
   samples,rate=sf.read(temporary,dtype='float32');assert len(samples)>rate*.2 and np.isfinite(samples).all() and np.max(np.abs(samples))>.001
   temporary.replace(raw);stamp.write_text(key);(cache/f'{n:03d}-fit.wav').unlink(missing_ok=True)
   return n,'generated'
  except RuntimeError as e:
   if 'NoAudioReceived' not in str(e) or attempt==3:raise
   time.sleep(2)

errors=[]
with ThreadPoolExecutor(max_workers=2) as pool:
 pending={pool.submit(render,row):row['scene'] for row in rows}
 for future in as_completed(pending):
  try:print(json.dumps(dict(cue=future.result()[0],status=future.result()[1])),flush=True)
  except Exception as e:errors.append(pending[future]);print(json.dumps(dict(cue=pending[future],error=str(e)[:300])),flush=True)
assert not errors,errors
print('All 129 Andrew cues cached through the original Melo online backend; ready for fitting.',flush=True)
