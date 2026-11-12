import hashlib,importlib.metadata,json,sys,time,wave
from pathlib import Path
import numpy as np
from render_common import R,S,A,split
W=R.parent;lock=json.loads((R/'ADAM_VOICE_LOCK.json').read_text());assert importlib.metadata.version('vieneu')=='3.8.3'
import vieneu
asset=Path(vieneu.__file__).parent/'assets/voices_v3_turbo.json';assert hashlib.file_digest(asset.open('rb'),'sha256').hexdigest()==lock['voices_json_sha256']
preset=json.loads(asset.read_text())['presets']['Adam'];assert preset['gender']=='male' and hashlib.sha256(json.dumps(preset,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==lock['preset_sha256']
import vieneu._v3_turbo_engine.onnx_runtime_lite as ortmod
Original=ortmod.OnnxV3LiteEngine
def pinned(*args,**kw):kw['codec_dir']=str(W/'adam-models45/codec');return Original(*args,**kw)
ortmod.OnnxV3LiteEngine=pinned
from vieneu.v3turbo import V3TurboVieNeuTTS
reader=V3TurboVieNeuTTS(backbone_repo=str(W/'adam-models45/backbone'),onnx_dir=str(W/'adam-models45/backbone'),device='cpu',backend='onnx',precision='fp32',threads=2);assert 'Adam' in reader._preset_voices
sys.path.insert(0,str(W/'melo45'));import worker
rows=json.loads((S/'vi-VN.json').read_text());assert len(rows)==13 and rows[-1]['end']==1242 and (S/'vi-VN.reviewed45').exists();out=A/'vi-VN';out.mkdir(parents=True,exist_ok=True)
shard=int(sys.argv[1]);allowed=range(0,6) if shard==0 else range(6,13)
for i in allowed:
 parts=split(rows[i]['voice'],350)
 for j,text in enumerate(parts):
  p=out/f'raw-{i+1:03}-{j+1:02}.wav';m=p.with_suffix('.native.json');sig=hashlib.sha256(text.encode()).hexdigest()
  if p.exists() and m.exists():
   old=json.loads(m.read_text())
   if old.get('text_sha256')==sig and old.get('preset_sha256')==lock['preset_sha256']:continue
  start=time.monotonic();result=worker.synthesize(reader,'VI','Adam',text,p)
  with wave.open(str(p)) as w:sr=w.getframerate();frames=w.getnframes();assert sr==48000 and frames>sr*.25;pcm=w.readframes(frames)
  with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm+b'\0\0'*round(sr*.10))
  m.write_text(json.dumps({'text_sha256':sig,'voice_id':'Adam','preset_sha256':lock['preset_sha256'],'sdk_version':'3.8.3','model_revision':'61b85e3d937fbbacb387714180e8182823512523','seconds':frames/sr+.1,'complete_native_inference':True}))
  print('ADAM_PART',i+1,j+1,'audio',round(frames/sr,2),'wall',round(time.monotonic()-start,2),flush=True)
 print('ADAM_CHAPTER_DONE',i+1,len(parts),flush=True)
