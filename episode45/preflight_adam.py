import hashlib,importlib.metadata,json,sys,time,wave
from pathlib import Path
R=Path(__file__).parent;W=R.parent;lock=json.loads((R/'ADAM_VOICE_LOCK.json').read_text())
assert importlib.metadata.version('vieneu')=='3.8.3'
import vieneu,numpy as np
asset=Path(vieneu.__file__).parent/'assets/voices_v3_turbo.json';assert hashlib.file_digest(asset.open('rb'),'sha256').hexdigest()==lock['voices_json_sha256']
preset=json.loads(asset.read_text())['presets']['Adam'];assert preset['gender']=='male' and hashlib.sha256(json.dumps(preset,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==lock['preset_sha256']
import vieneu._v3_turbo_engine.onnx_runtime_lite as ortmod
OriginalEngine=ortmod.OnnxV3LiteEngine
def pinned_engine(*args,**kwargs):kwargs['codec_dir']=str(W/'adam-models45/codec');return OriginalEngine(*args,**kwargs)
ortmod.OnnxV3LiteEngine=pinned_engine
from vieneu.v3turbo import V3TurboVieNeuTTS
start=time.monotonic();reader=V3TurboVieNeuTTS(backbone_repo=str(W/'adam-models45/backbone'),onnx_dir=str(W/'adam-models45/backbone'),device='cpu',backend='onnx',precision='fp32',threads=2)
assert 'Adam' in reader._preset_voices
sys.path.insert(0,str(W/'melo45'));import worker
text='Một bữa ăn hôm nay chưa chắc đã trở thành bữa ăn ngày mai. Những dấu vết nhỏ có thể kể lại câu chuyện ấy.'
result=worker.synthesize(reader,'VI','Adam',text,R/'ADAM_NATIVE_PREVIEW.wav')
with wave.open(str(R/'ADAM_NATIVE_PREVIEW.wav')) as w:seconds=w.getnframes()/w.getframerate();assert w.getframerate()==48000 and 4<=seconds<=35
qa={'status':'passed','voice_id':'Adam','gender':'Male','locale':'vi-VN','region':'Nam','sdk_version':'3.8.3','preset_sha256':lock['preset_sha256'],'backend':'Melo1.3.1worker/VieNeuONNXFP32','sample_seconds':seconds,'sample_bytes':(R/'ADAM_NATIVE_PREVIEW.wav').stat().st_size,'sample_sha256':hashlib.file_digest((R/'ADAM_NATIVE_PREVIEW.wav').open('rb'),'sha256').hexdigest(),'wall_seconds':round(time.monotonic()-start,2),'independent_native_listening_review':False}
(R/'ADAM_PREFLIGHT_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));print(json.dumps(qa,ensure_ascii=False),flush=True)
