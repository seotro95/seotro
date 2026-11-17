import hashlib,json,re,unicodedata,zipfile
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';D=R/'documents'
chapters=json.loads((R/'LOCALIZATION_SOURCE_CHAPTERS.json').read_text());assert len(chapters)==14
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())['profiles']
patches=json.loads((R/'LOCALIZATION_PATCHES.json').read_text())
overrides=json.loads((R/'LOCALIZATION_OVERRIDES.json').read_text())
review=dict(topic_id='MOI-030',independent_native_review=False,independent_native_listening_review=False,
 source_adaptation='Fourteen complete English chapters retained in sequence; ambiguous engineering words clarified for machine translation. Vietnamese rewritten by assistant, preserving mechanism, source and chronology limits, with a modestly brisker density.',
 assistant_review_scope='Full Vietnamese rewrite; selected technical passages across the other fourteen languages covering source elevation, gallery, access shafts, example slope, water-use periods, water quality, recharge, historical uncertainty and aflaj; full-script five-word English leak scan. No independent native editorial or listening review.',locales={})
for profile in profiles:
 locale=profile['locale']
 if locale=='en-US':continue
 edits=[]
 if locale=='vi-VN':
  pieces=re.split(r'^## \d+\n',(R/'VI_NARRATION.txt').read_text(),flags=re.M)[1:];assert len(pieces)==14
  rows=[dict(id=c['id'],start=c['start'],end=c['end'],voice=body.strip(),source_voice=c['voice'],locale=locale,translation_method='Assistant Vietnamese rewrite; independent native review pending') for c,body in zip(chapters,pieces)]
 else:
  drafts=json.loads((S/f'{locale}.context-draft.json').read_text());assert len(drafts)==14
  rows=[]
  for row,c in zip(drafts,chapters):
   assert row['source_voice']==c['voice']
   body=unicodedata.normalize('NFC',row['voice'])
   if str(row['id']) in overrides.get(locale,{}):
    body=overrides[locale][str(row['id'])];edits.append(dict(chapter=row['id'],action='Assistant contextual chapter rewrite'))
   for old,new in patches.get(locale,[]):
    if old in body:body=body.replace(old,new);edits.append(dict(chapter=row['id'],old=old,new=new))
   rows.append(dict(id=c['id'],start=c['start'],end=c['end'],voice=body,source_voice=c['voice'],locale=locale,translation_method='Automated contextual translation with assistant selected-passage edits; independent native review pending'))
 out=S/f'{locale}.json';out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 record=dict(chapters=14,assistant_full_rewrite=locale=='vi-VN',targeted_edits=edits,independent_native_review=False)
 review['locales'][locale]=record
 sha=hashlib.sha256(out.read_bytes()).hexdigest()
 (S/f'{locale}.context_checked').write_text(json.dumps(dict(script_sha256=sha,independent_native_review=False,review_scope=review['assistant_review_scope']),ensure_ascii=False,indent=2)+'\n')
qa=dict(status='passed',topic_id='MOI-030',target_seconds=1362,voices=16,script_sha256={},english_leaks={},chapter_counts={},independent_native_review=False)
for profile in profiles:
 locale=profile['locale'];path=S/f'{locale}.json';rows=json.loads(path.read_text())
 assert len(rows)==(137 if locale=='en-US' else 14) and rows[0]['start']==0 and rows[-1]['end']==1362
 assert all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
 assert all(x['voice'].strip() and '\ufffd' not in x['voice'] for x in rows)
 leaks=[]
 if locale!='en-US':
  for row in rows:
   source=re.findall('[a-z]+',row['source_voice'].lower());target=' '.join(re.findall('[a-z]+',row['voice'].lower()))
   found={' '.join(source[i:i+5]) for i in range(len(source)-4) if ' '.join(source[i:i+5]) in target}
   if found:leaks.append(dict(chapter=row['id'],phrases=sorted(found)))
  assert not leaks,(locale,leaks)
 qa['script_sha256'][locale]=hashlib.sha256(path.read_bytes()).hexdigest();qa['english_leaks'][locale]=leaks;qa['chapter_counts'][locale]=len(rows)
if (R/'PACING_SCRIPT_REPAIRS.json').exists():review['pacing_script_repairs']=json.loads((R/'PACING_SCRIPT_REPAIRS.json').read_text())
for name,obj in [('VOICE_INPUT_QA.json',qa),('TRANSLATION_REVIEW.json',review)]:
 (R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with zipfile.ZipFile(R/'VOICE_INPUTS.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in profiles:
  locale=p['locale'];z.write(S/f'{locale}.json',f'voice/scripts/{locale}.json')
  if locale!='en-US':z.write(S/f'{locale}.context_checked',f'voice/scripts/{locale}.context_checked')
 for name in ['VOICE_INPUT_QA.json','TRANSLATION_REVIEW.json','LOCALIZATION_SOURCE_CHAPTERS.json']:z.write(R/name,name)
(R/'VOICE_INPUTS.sha256').write_text(hashlib.sha256((R/'VOICE_INPUTS.zip').read_bytes()).hexdigest()+'\n')
print('QANAT_16VOICE_INPUT_QA_PASSED',flush=True)
