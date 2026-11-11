import hashlib,json,os,sys,time
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R.parent/'hmong166/voice-studio'));sys.path.insert(0,str(R))
os.environ['HMOOB_MODEL_DIR']=str(R.parent/'hmong-models');os.environ['HMOOB_DEVICE']='cpu';os.environ['HMOOB_PRECISION']='fp32'
from hmong_native import SpeechEngine,validate_text
from hmong_native_models import verify_models
from render_episode import split,finish
import numpy as np,soundfile as sf,torch
assert json.loads((R/'DOCUMENT_DELIVERY_STATE.json').read_text())['documents_published']
rows=json.loads((R/'voice/scripts/mww.json').read_text());assert len(rows)==14 and rows[-1]['end']==1352
assert (R/'voice/scripts/mww.reviewed38').exists()
reference=R.parent/'hmong166/voice-studio/assets/hmong/female-3.wav'
assert hashlib.file_digest(reference.open('rb'),'sha256').hexdigest()=='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17'
for row in rows:validate_text(row['voice'])
verify_models();engine=SpeechEngine();engine._load();torch.set_num_threads(2)
out=R/'voice/audio/mww';out.mkdir(parents=True,exist_ok=True);shard=int(sys.argv[1]);allowed=range(shard*7,min((shard+1)*7,14));raws=[]
for i in allowed:
 row=rows[i];parts=split(validate_text(row['voice']),limit=350);paths=[]
 for j,text in enumerate(parts):
  path=out/f'raw-{i+1:03}-{j+1:02}.wav';paths.append(path);meta=path.with_suffix('.native.json');sig=hashlib.sha256(text.encode()).hexdigest()
  if path.exists() and meta.exists() and json.loads(meta.read_text()).get('text_sha256')==sig:continue
  started=time.monotonic();speed=.98 if i in [0,13] or '?' in text else 1.02
  samples,rate=engine.synthesize(text,str(reference),'',speed=speed,quality='fast',audio_profile='clear-v1')
  assert np.isfinite(samples).all() and len(samples)>rate
  samples=np.concatenate([samples,np.zeros(round(rate*.08),dtype=samples.dtype)]);peak=float(np.abs(samples).max())
  if peak>.95:samples=samples*(.95/peak)
  sf.write(path,samples,rate,subtype='PCM_16');meta.write_text(json.dumps({'text_sha256':sig,'reference_sha256':'ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17','speed':speed,'audio_profile':'clear-v1','seconds':len(samples)/rate,'complete_native_inference':True}))
  print('NATIVE_PART',i+1,j+1,'audio',round(len(samples)/rate,2),'wall',round(time.monotonic()-started,2),flush=True)
 print('NATIVE_CHAPTER_DONE',i+1,len(paths),flush=True)
print('NATIVE_SHARD_DONE',shard,flush=True)
