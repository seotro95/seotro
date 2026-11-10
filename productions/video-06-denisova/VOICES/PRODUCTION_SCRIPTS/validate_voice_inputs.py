import hashlib,json,re
from pathlib import Path
R=Path(__file__).parent
profiles=json.load(open(R/'BASELINE_VOICE_PROFILES.json'))['profiles'];assert len(profiles)==17
report={'topic':6,'target_seconds':1260,'review':'Assistant scientific/context review including machine backtranslation of chapters2,4,5,10 for14 locales, followed by direct assistant review of concise timing rewrites; independent native editorial/listening review pending.','voices':[]}
for p in profiles:
 loc=p['locale'];f=R/'voice/scripts'/f'{loc}.json';rows=json.load(open(f));assert len(rows)==(126 if loc=='en-US' else 12)
 assert rows[0]['start']==0 and rows[-1]['end']==1260
 assert all(x['end']==y['start'] for x,y in zip(rows,rows[1:]))
 assert all(x['voice'].strip() for x in rows)
 if loc=='en-US':
  assert all(x['end']-x['start']==10 for x in rows)
  assert sum(len(x['voice'].split()) for x in rows)==3425
  assert '\n\n'.join(x['voice'] for x in rows).strip()==(R/'package/KICH_BAN_EN_21_PHUT.txt').read_text().strip()
 else:
  assert [x['end']-x['start'] for x in rows]==[110]*6+[100]*6
  assert (R/'voice/scripts'/f'{loc}.terminology-v2').exists()
  assert (R/'voice/scripts'/(f'{loc}.'+('reviewed-v3' if loc in ['vi-VN','mww'] else 'review-clarity-v4'))).exists()
 for x in rows:assert not re.search(r'\b(\w+)(?:\s+\1){4,}\b',x['voice'],re.I),(loc,x['id'])
 assert p['gender']==('Female' if loc=='mww' else 'Male')
 report['voices'].append({'locale':loc,'voice_id':p['voice_id'],'gender':p['gender'],'segments':len(rows),'seconds':1260,'script_json_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'voice_text_sha256':hashlib.sha256('\n\n'.join(x['voice'] for x in rows).encode()).hexdigest()})
f=Path('/workspace/work/hmong166/voice-studio/assets/hmong/female-3.wav');assert hashlib.sha256(f.read_bytes()).hexdigest()=='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17'
report['native_reference_verified']=True;report['passed']=True
(R/'VOICE_INPUT_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('INPUT_QA_PASS17')
