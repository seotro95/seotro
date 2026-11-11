import os,sys,json,re,time,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'hmong166/voice-studio'));sys.path.insert(0,str(R))
os.environ['HMOOB_MODEL_DIR']=str(R.parent/'hmong-models');os.environ['HMOOB_DEVICE']='cpu';os.environ['HMOOB_PRECISION']='fp32'
import numpy as np,soundfile as sf
from hmong_native import SpeechEngine,validate_text
from hmong_native_models import verify_models
from review_translations import save
from render import final,split
texts=re.split(r'\n\s*\n',(R/'mww-reviewed.txt').read_text().strip())
save('mww',texts,'Assistant rewritten Hmong draft from source story; White Hmong dialect and native listening not independently verified')
rows=json.loads((R/'voice/scripts/mww.json').read_text())
for row in rows:validate_text(row['voice'])
reference=R.parent/'hmong166/voice-studio/assets/hmong/female-3.wav'
assert hashlib.sha256(reference.read_bytes()).hexdigest()=='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17'
verify_models();engine=SpeechEngine();engine._load()
import torch
torch.set_num_threads(2)
out=R/'voice/audio/mww';out.mkdir(parents=True,exist_ok=True)
raws=[]
for idx,row in enumerate(rows):
    if os.environ.get('NATIVE_CHAPTER') and idx+1!=int(os.environ['NATIVE_CHAPTER']):continue
    paths=[]
    for n,piece in enumerate(split(validate_text(row['voice']),limit=350)):
        path=out/f'raw-{idx+1:03}-{n+1:02}.wav';paths.append(path)
        if not path.exists():
            started=time.monotonic()
            speed=.98 if '?' in piece or idx in [0,12] else 1.02
            samples,rate=engine.synthesize(piece,str(reference),'',speed=speed,quality='fast',audio_profile='clear-v1')
            samples=np.concatenate([samples,np.zeros(round(rate*.08),dtype=samples.dtype)])
            peak=np.max(np.abs(samples))
            if peak>.95:samples=samples*(.95/peak)
            sf.write(path,samples,rate,subtype='PCM_16')
            print('NATIVE_PART',idx+1,n+1,'audio',round(len(samples)/rate,2),'wall',round(time.monotonic()-started,2),flush=True)
    raws.append(paths);print('NATIVE_CHAPTER',idx+1,len(paths),flush=True)
if not os.environ.get('NATIVE_CHAPTER'):final('mww',rows,raws)
