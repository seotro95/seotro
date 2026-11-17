import hashlib,json,re,unicodedata,zipfile
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';D=R/'documents'
chapters=json.loads((R/'LOCALIZATION_SOURCE_CHAPTERS.json').read_text())
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())['profiles']
patches=json.loads((R/'LOCALIZATION_PATCHES.json').read_text())
review=dict(topic_id='MOI-027',independent_native_review=False,independent_native_listening_review=False,
 source_adaptation='13 complete English chapters retained in order; ambiguous engineering terms clarified. Vietnamese assistant rewrite condenses repeated transitions while retaining source findings, transport and erection limits.',
 assistant_review_scope='Full Vietnamese rewrite; selected source, Altar Stone, 2026 ice-model, gravity, joint, fixed-track and stone-dressing passages across all fourteen other languages; years and closing reviewed; whole-script five-word English leak scan. French chapter 6 rewritten to remove English fragments. No independent native editorial or listening review.',
 rejected_initial_draft_issues=['mineral grains translated as food grain','ground and socket translated as electrical parts','stone joints translated as anatomical joints','ramp translated as lamp','part of the route confused with part of the boulder','featureless load translated as weightless load','French chapter 6 contained English fragments'],locales={})
for p in profiles:
 locale=p['locale']
 if locale=='en-US':continue
 edits=[]
 if locale=='vi-VN':
  pieces=re.split(r'^## \d+\n',(R/'VI_NARRATION.txt').read_text(),flags=re.M)[1:]
  assert len(pieces)==13,len(pieces)
  rows=[{**c,'source_voice':c['voice'],'voice':body.strip(),'locale':locale,'translation_method':'Assistant Vietnamese rewrite; independent native review pending'} for c,body in zip(chapters,pieces)]
 else:
  rows=json.loads((S/f'{locale}.context-draft.json').read_text());assert len(rows)==13
  for row,c in zip(rows,chapters):
   assert row['source_voice']==c['voice']
   body=unicodedata.normalize('NFC',row['voice'])
   for old,new in patches[locale]:
    if old.startswith('__'):continue
    if old in body:body=body.replace(old,new);edits.append(dict(chapter=row['id'],old=old,new=new))
   if locale=='fr-FR' and row['id']==6:
    body=(R/'FRENCH_CHAPTER_6.txt').read_text().strip();edits.append(dict(chapter=6,action='Full assistant French rewrite removes English fragments'))
   row['voice']=body;row['translation_method']='Automated contextual draft with assistant selected technical passage, date and closing edits; independent native review pending'
 out=S/f'{locale}.json';out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 review['locales'][locale]=dict(chapters=13,assistant_full_rewrite=locale=='vi-VN',targeted_edits=edits,independent_native_review=False)
 sha=hashlib.sha256(out.read_bytes()).hexdigest()
 (S/f'{locale}.context_checked').write_text(json.dumps(dict(script_sha256=sha,independent_native_review=False,review_scope=review['assistant_review_scope']),ensure_ascii=False,indent=2)+'\n')
qa=dict(status='passed',topic_id='MOI-027',target_seconds=1292,voices=16,script_sha256={},english_leaks={},chapter_counts={},independent_native_review=False)
for p in profiles:
 locale=p['locale'];path=S/f'{locale}.json';rows=json.loads(path.read_text())
 assert len(rows)==(130 if locale=='en-US' else 13) and rows[0]['start']==0 and rows[-1]['end']==1292
 assert all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
 assert all(x['voice'].strip() and '\ufffd' not in x['voice'] for x in rows)
 leaks=[]
 if locale!='en-US':
  for row in rows:
   source=re.findall('[a-z]+',row['source_voice'].lower());target=' '.join(re.findall('[a-z]+',row['voice'].lower()))
   found={' '.join(source[i:i+5]) for i in range(len(source)-4) if ' '.join(source[i:i+5]) in target}
   if found:leaks.append(dict(chapter=row['id'],phrases=sorted(found)))
  assert not leaks,(locale,leaks)
  if locale!='vi-VN':assert all(year in rows[ch]['voice'] for ch,year in [(1,'2020'),(1,'1958'),(3,'2024'),(6,'2026')])
 qa['script_sha256'][locale]=hashlib.sha256(path.read_bytes()).hexdigest();qa['english_leaks'][locale]=leaks;qa['chapter_counts'][locale]=len(rows)
for name,obj in [('VOICE_INPUT_QA.json',qa),('TRANSLATION_REVIEW.json',review)]:
 (R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STONEHENGE_16VOICE_INPUT_QA_PASSED',flush=True)
