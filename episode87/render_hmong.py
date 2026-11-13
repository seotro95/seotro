import hashlib,json,os,sys,time
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R.parent/'hmong166/voice-studio'));sys.path.insert(0,str(R))
os.environ['HMOOB_MODEL_DIR']=str(R.parent/'hmong-models');os.environ['HMOOB_DEVICE']='cpu';os.environ['HMOOB_PRECISION']='fp32'
from hmong_native import SpeechEngine,validate_text
from hmong_native_models import verify_models
from render_common import split
import numpy as np,soundfile as sf,torch
rows=json.loads((R/'voice/scripts/mww.json').read_text());assert len(rows)==13 and rows[-1]['end']==1222 and (R/'voice/scripts/mww.reviewed87').exists()
reference=R.parent/'hmong166/voice-studio/assets/hmong/female-3.wav';refsha='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17';assert hashlib.file_digest(reference.open('rb'),'sha256').hexdigest()==refsha
for row in rows:validate_text(row['voice'])
verify_models();engine=SpeechEngine();engine._load();torch.set_num_threads(2)
out=R/'voice/audio/mww';out.mkdir(parents=True,exist_ok=True);shard=int(sys.argv[1]);allowed=range(0,6) if shard==0 else range(6,13)
for i in allowed:
 parts=split(validate_text(rows[i]['voice']),350)
 for j,text in enumerate(parts):
  p=out/f'raw-{i+1:03}-{j+1:02}.wav';m=p.with_suffix('.native.json');sig=hashlib.sha256(text.encode()).hexdigest()
  if p.exists() and m.exists() and json.loads(m.read_text()).get('text_sha256')==sig:continue
  started=time.monotonic();speed=.98 if i in [0,12] or '?' in text else 1.02
  audio,rate=engine.synthesize(text,str(reference),'',speed=speed,quality='fast',audio_profile='clear-v1');assert np.isfinite(audio).all() and len(audio)>rate*.25
  audio=np.concatenate([audio,np.zeros(round(rate*.08),dtype=audio.dtype)]);peak=float(np.abs(audio).max())
  if peak>.95:audio=audio*(.95/peak)
  sf.write(p,audio,rate,subtype='PCM_16');m.write_text(json.dumps({'text_sha256':sig,'voice_id':'hmong-female-3','reference_sha256':refsha,'speed':speed,'seconds':len(audio)/rate,'complete_native_inference':True}))
  print('HMONG_PART',i+1,j+1,'audio',round(len(audio)/rate,2),'wall',round(time.monotonic()-started,2),flush=True)
 print('HMONG_CHAPTER_DONE',i+1,len(parts),flush=True)
