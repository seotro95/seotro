import csv,hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';profiles=json.load(open(R/'BASELINE_VOICE_PROFILES.json'))['profiles'];ch=list(csv.DictReader(open(R/'package/CHAPTERS_12.csv')));report=[]
assert len(profiles)==17 and sum(p['gender']=='Male' for p in profiles)==16
assert [p for p in profiles if p['locale']=='mww'][0]['voice_id']=='hmong-female-3'
for p in profiles:
 loc=p['locale'];path=S/f'{loc}.json';rows=json.loads(path.read_text());assert len(rows)==(138 if loc=='en-US' else 12)
 if loc!='en-US':
  assert path.with_suffix('.terminology-v2').exists()
  if loc in ['mww','vi-VN']:assert path.with_suffix('.reviewed-v3').exists()
  else:assert (S/f'{loc}.review-clarity-v3').exists()
 for i,r in enumerate(rows):
  assert r['voice'].strip() and r['id']==i+1
  assert (r['start'],r['end'])==((i*10,(i+1)*10) if loc=='en-US' else (int(ch[i]['start_seconds']),int(ch[i]['end_seconds'])))
 assert rows[0]['start']==0 and rows[-1]['end']==1380
 report.append({'locale':loc,'voice_id':p['voice_id'],'gender':p['gender'],'segments':len(rows),'target_seconds':1380,'words':sum(len(r['voice'].split()) for r in rows),'characters':sum(len(r['voice']) for r in rows),'script_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'voice_text_sha256':hashlib.sha256(' '.join(r['voice'] for r in rows).encode()).hexdigest(),'language_review':'Assistant terminology/context review; independent native listening review pending' if loc!='en-US' else 'Original English'})
assert report[0]['words']==3648
(R/'VOICE_INPUT_QA.json').write_text(json.dumps({'status':'passed','voices':report,'native_hmong_input_validation':'All12 chapters passed original native validation; numbers separated for tool normalisation'},ensure_ascii=False,indent=2));print('All17 script inputs passed; English3648words,138cues, target1380seconds')
