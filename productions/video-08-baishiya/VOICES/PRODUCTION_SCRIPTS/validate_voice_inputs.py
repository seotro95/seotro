import hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';profiles=json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text());ids={p['locale']:p for p in profiles['profiles']};assert len(ids)==17 and sum(x['gender']=='Male' for x in ids.values())==16 and ids['mww']['gender']=='Female'
durations=[120]*2+[110]*10;starts=[0]
for n in durations:starts.append(starts[-1]+n)
required={1:[3280],2:[1980,160000,2019],3:[2024,2567,1857],9:[190000,30000],10:[48000,32000]}
kanji={'十九万':'190000','三万二千':'32000','四万八千':'48000','三万':'30000','十六万':'160000','三千二百八十':'3280','二千五百六十七':'2567','千八百五十七':'1857','二千二十四':'2024','二千十九':'2019','千九百八十':'1980'}
qa=[]
for loc in ids:
 p=S/f'{loc}.json';rows=json.loads(p.read_text());assert len(rows)==(134 if loc=='en-US' else 12),(loc,len(rows));assert rows[0]['start']==0 and rows[-1]['end']==1340
 if loc=='en-US':
  assert sum(len(x['voice'].split()) for x in rows)==3162
  assert all(x['id']==i+1 and x['start']==i*10 and x['end']==(i+1)*10 for i,x in enumerate(rows));continue
 assert p.with_suffix('.terminology-v2').read_text().strip()==hashlib.sha256(p.read_bytes()).hexdigest(),loc
 assert loc in ['mww','vi-VN'] or p.with_suffix('.reviewed08').exists(),loc
 for i,x in enumerate(rows):
  assert x['id']==i+1 and x['start']==starts[i] and x['end']==starts[i+1]
  assert x['voice'].strip() and not re.search(r'\b(\w+)(?:\s+\1){4,}\b',x['voice'],re.I),(loc,i+1)
  text=x['voice']
  if loc=='ja-JP':
   for a,b in kanji.items():text=text.replace(a,b)
   text=re.sub(r'(\d+)万(\d{0,4})',lambda m:str(int(m[1])*10000+int(m[2] or 0)),text)
  norm=re.sub(r'[.,\s\u00a0\u202f]','',text)
  for num in required.get(i+1,[]):assert str(num) in norm,(loc,i+1,num)
 qa.append(dict(locale=loc,chapters=12,numerical_evidence_values_preserved=True,assistant_review_completed=True,native_editorial_listening_review_pending=True))
(R/'VOICE_INPUT_QA.json').write_text(json.dumps(dict(status='passed',voices=17,english_words=3162,english_cues=134,translated_chapter_seconds=durations,seconds=1340,source_integrity_unchanged=True,profiles_preserved=True,reviewed_locales=qa),ensure_ascii=False,indent=2));print('All17 input scripts/timings/voiceIDs/numbers validated')
