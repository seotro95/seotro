import json,re,hashlib,subprocess,sys,unicodedata,difflib
from pathlib import Path
import numpy as np
from render import split
R=Path(__file__).resolve().parent
records=[];metadata=[]
for root in sorted((R/'voice/audio').iterdir()):
    p=root/'render_report.json'
    if not p.exists():continue
    j=json.loads(p.read_text());mp3=root/j['filename']
    assert hashlib.sha256(mp3.read_bytes()).hexdigest()==j['sha256']
    assert j['decoded_frames_48000']==59616000 and j['decoded_seconds']==1242
    samples=np.frombuffer(subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error','-i',str(mp3),'-f','f32le','-ar','16000','-ac','1','pipe:1']),dtype='<f4')
    assert len(samples)==1242*16000 and np.isfinite(samples).all()
    blocks=samples[:len(samples)//1600*1600].reshape(-1,1600)
    rms=np.sqrt(np.mean(blocks.astype(np.float64)**2,axis=1))
    silent=rms<10**(-50/20);longest=0;run=0
    for x in silent:
        run=run+1 if x else 0;longest=max(longest,run)
    peak=float(np.max(np.abs(samples)));assert peak>0.01 and peak<1 and longest/10<5,(j['locale'],peak,longest)
    records.append(dict(locale=j['locale'],seconds=len(samples)/16000,peak_dbfs=float(20*np.log10(peak)),longest_interval_below_minus50dB_seconds=longest/10,complete_decode=True,sha256=j['sha256']))
    if j['locale']=='mww':continue
    rows=json.loads((R/'voice/scripts'/f'{j["locale"]}.json').read_text());ratios=[]
    for idx,row in enumerate(rows):
        for n,text in enumerate(split(row['voice'])):
            words=json.loads((root/f'raw-{idx+1:03}-{n+1:02}.edge.words.json').read_text())
            actual=''.join(w['text'] for w in words)
            norm=lambda s:''.join(c for c in unicodedata.normalize('NFKC',s).lower() if c.isalnum())
            ratio=difflib.SequenceMatcher(None,norm(text),norm(actual),autojunk=False).ratio();assert ratio>=.97,(j['locale'],idx+1,n+1,ratio)
            ratios.append(ratio)
    metadata.append(dict(locale=j['locale'],pieces=len(ratios),minimum_normalized_metadata_text_similarity=min(ratios),threshold=.97))
    print('QA_AUDIO',j['locale'],flush=True)
(R/'documents/VOICE_RELEASE_QA.json').write_text(json.dumps(dict(target_seconds=1242,voices_checked=len(records),audio=records,online_provider_metadata_checks=metadata,metadata_is_not_independent_ASR_or_listening=True,hmong_word_level_verification=False,independent_native_language_review=False),ensure_ascii=False,indent=2))
print('QA_COMPLETE',len(records),flush=True)
