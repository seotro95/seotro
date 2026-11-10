import hashlib,json,os,sys
from pathlib import Path
ROOT=Path('/workspace/work/baishiya');sys.path.insert(0,str(ROOT))
assert (ROOT/'DOCUMENT_DELIVERY_STATE.json').exists()
assert (ROOT/'voice/scripts/mww.terminology-v2').exists()
os.environ['HMOOB_MODEL_DIR']='/workspace/work/hmong-models'
os.environ['HMOOB_DEVICE']='cpu';os.environ['HMOOB_PRECISION']='fp32'
NATIVE=Path('/workspace/work/hmong166/voice-studio');sys.path.insert(0,str(NATIVE))
import numpy as np,soundfile as sf,torch
from hmong_native import SpeechEngine,validate_text
from hmong_native_models import verify_models
from render_common import AUDIO,BASE,PROFILES,chunks,finalize

locale='mww';profile=PROFILES[locale];reference=NATIVE/'assets/hmong/female-3.wav'
assert hashlib.sha256(reference.read_bytes()).hexdigest()==profile['reference_sha256']
verify_models();torch.set_num_threads(2);engine=SpeechEngine()
rows=json.loads((BASE/'scripts/mww.json').read_text());out=AUDIO/locale;out.mkdir(exist_ok=True)
if (out/'render_report.json').exists():print('Hmong already verified');sys.exit(0)
records=[]
for cue,row in enumerate(rows):
    for index,text in enumerate(chunks(validate_text(row['voice']),limit=320)):
        path=out/f'raw-{cue+1:03d}-{index+1:02d}.wav'
        if not path.exists():
            speed=.97 if cue in [0,9,10,11] or '?' in text else 1.03 if index%2 else 1.0
            samples,rate=engine.synthesize(text,str(reference),'',speed=speed,quality='fast',audio_profile='clear-v1')
            gain_db=-.3 if cue==11 else .6 if any(w in text for w in ['caj ces','tsis yog','pov thawj']) else 0
            samples=samples*(10**(gain_db/20))
            pause=.16 if '?' in text else .12 if cue in [0,11] else .07
            samples=np.concatenate([samples,np.zeros(round(rate*pause),dtype=samples.dtype)])
            peak=float(np.max(np.abs(samples)))
            if peak>.95:samples=samples*(.95/peak)
            sf.write(path,samples,rate,subtype='PCM_16')
        records.append((cue,text,path))
    print(json.dumps({'hmong_chapter_synthesized':cue+1,'total':12}),flush=True)
finalize(locale,rows,records,out)
