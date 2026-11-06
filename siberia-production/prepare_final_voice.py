"""Use existing verified-timeline translations, then apply reviewed passages."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys

base=Path(__file__).resolve().parent;code=sys.argv[1]
master=json.loads((base/'master_timeline.json').read_text())
curation=json.loads((base/'curated_cues.json').read_text())
out=Path('translated');out.mkdir(exist_ok=True)
if code=='vi':
 rows=[{**c,'source_text':c['text'],'text':curation['vi'][str(c['id'])]} for c in master['cues']]
else:
 cached=out/(code+'.json')
 subprocess.run([sys.executable,str(base/'translate_web.py'),code],check=True)
 rows=json.loads(cached.read_text())
 assert len(rows)==len(master['cues'])
 for source,row in zip(master['cues'],rows):
  for field in ['id','start_ms','end_ms','chapter']:assert source[field]==row[field],(code,field)
  assert row['source_text']==source['text'],(code,row['id'],'stale source script')
  if str(row['id']) in curation.get(code,{}):row['text']=curation[code][str(row['id'])]
assert len(rows)==59 and rows[-1]['end_ms']==1536000
def stamp(ms):
 s,ms=divmod(ms,1000);m,s=divmod(s,60);h,m=divmod(m,60);return f'{h:02}:{m:02}:{s:02},{ms:03}'
srt='\n\n'.join(str(c['id'])+'\n'+stamp(c['start_ms'])+' --> '+stamp(c['end_ms'])+'\n'+re.sub(r'\s+',' ',c['text']).strip() for c in rows)+'\n'
(base/'voices'/(code+'.srt')).write_text(srt,encoding='utf-8')
(out/(code+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(out/(code+'.txt')).write_text('\n\n'.join(c['text'] for c in rows),encoding='utf-8')
meta={'master_timeline_sha256':hashlib.sha256((base/'master_timeline.json').read_bytes()).hexdigest(),
 'narration_srt_sha256':hashlib.sha256(srt.encode()).hexdigest(),'curation_sha256':hashlib.sha256((base/'curated_cues.json').read_bytes()).hexdigest(),
 'curated_cue_ids':list(curation.get(code,{})),
 'translation_status':'Vietnamese wording revised in all 59 cues' if code=='vi' else 'Public web translation of the original script, with clarified technical English and targeted scientific passage corrections; native-speaker review remains recommended',
 'source_timeline_verified':True}
(out/(code+'-text-review.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared',code,59,'timed paragraphs;',len(curation.get(code,{})),'reviewed cue replacements',flush=True)
