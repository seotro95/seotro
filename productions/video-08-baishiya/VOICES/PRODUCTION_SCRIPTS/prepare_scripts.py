import csv,hashlib,json,re,time,urllib.error,urllib.parse,urllib.request,sys
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';S.mkdir(parents=True,exist_ok=True);assert (R/'DOCUMENT_DELIVERY_STATE.json').exists()
source=[dict(id=int(a),start=(int(a)-1)*10,end=int(a)*10,voice=b) for a,b in (l.split('\t',1) for l in (R/'script_en.tsv').read_text().splitlines())]
(S/'en-US.json').write_text(json.dumps(source,ensure_ascii=False,indent=2));(S/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in source));chapters=list(csv.DictReader(open(R/'package/CHAPTERS_12.csv',encoding='utf-8-sig')))
LANGS={'mww':'hmn','vi-VN':'vi','es-ES':'es','fr-FR':'fr','ja-JP':'ja','ko-KR':'ko','de-DE':'de','it-IT':'it','pt-PT':'pt','nl-NL':'nl','pl-PL':'pl','sv-SE':'sv','da-DK':'da','fi-FI':'fi','nb-NO':'no','cs-CZ':'cs'}
NUMBERS={'three thousand two hundred eighty':'3280','one hundred sixty thousand':'160000','two thousand five hundred sixty seven':'2567','one thousand eight hundred fifty seven':'1857','one hundred ninety thousand':'190000','forty eight thousand':'48000','thirty two thousand':'32000','thirty thousand':'30000','nineteen eighty':'1980','two thousand nineteen':'2019','two thousand twenty four':'2024','Xiahe two':'Xiahe2','E P A S one':'EPAS1'}
def translation_source(ch):
 text=' '.join(r['voice'] for r in source if r['start']>=int(ch['start_seconds']) and r['end']<=int(ch['end_seconds']))
 for a,b in NUMBERS.items():text=text.replace(a,b)
 for a,b in {'Marks supported activities involving meat, marrow, and hides.': 'The physical marks provided evidence of processing meat, bone marrow, and animal skins.', 'The collection contained more than animals that simply happened to die nearby.': 'The marks showed that people had processed animal remains, so natural deaths near the cave could not explain the whole collection.', 'A pattern of processing tells us more than one dramatic looking broken bone.': 'Repeated evidence of processing is more informative than a single visually striking broken bone.', 'That first screen did not, by itself, deliver the complete identification.': 'That first molecular screening test did not provide a complete identification on its own.', 'A short rib fragment': 'A short fragment of a human rib bone', 'A rib can establish a connection': 'A human rib bone can establish a scientific relationship', 'This is a practical form of flexibility.': 'This shows practical flexibility in the use of materials.', 'Survival leaves an uneven archive.': 'Survival activities leave an incomplete archaeological record.'}.items():text=text.replace(a,b)
 fixes={'the jaw\'s age from its surroundings':'the estimated age of the jaw from its archaeological context','Uranium series measurements':'Measurements using the uranium-series method','a minimum age of about':'an estimated minimum age of about','ancient genetic material':'ancient DNA','fresh fracture':'fracture while the bone was still fresh','fresh breakage':'breakage while the bone was still fresh','The initial collagen evidence placed it among close human relatives':'The initial collagen evidence placed it within the human-related Homininae group','a rib can establish a connection':'a rib can establish a scientific relationship','Denisovan related ancestry':'ancestry related to Denisovans','Modern Tibetan populations':'Modern Tibetan human populations','bone replicas':'bone teaching models','tissue':'biological tissue'}
 for a,b in fixes.items():text=text.replace(a,b)
 for a,b in {'A blow produces a different record.': 'A blow leaves different physical traces.', 'hides': 'animal skins', 'hide': 'animal skin', 'Hide': 'Animal skin', 'percussion features': 'impact features', 'a percussion notch': 'an impact notch', 'an adult demonstrator': 'an adult person demonstrating a technique', 'anonymous adult': 'unnamed adult', 'Expedient does not mean meaningless.': 'A tool made with minimal shaping can still have practical value.', 'three expedient bone tools': 'three bone tools made with minimal shaping from existing fragments', 'a possible retoucher': 'a possible tool for retouching stone tools', 'Its modest size makes the point': 'Its modest size illustrates this idea', "The cave's deposits": "The cave's sediment deposits", 'oldest sampled deposits': 'oldest sampled sediment layers', 'a single survival scene tends to hide': 'a single survival scene tends to conceal', 'an ancient human lineage': 'an ancient group of people with a shared evolutionary history', 'a human lineage': 'a group of ancient people with a shared evolutionary history', 'a lineage': 'an ancient human group'}.items():text=text.replace(a,b)
 return text

def translate(text,lang):
 url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode(dict(client='gtx',sl='en',tl=lang,dt='t',q=text))
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=50) as f:j=json.load(f)
   out=''.join(x[0] for x in j[0] if x and x[0]);assert out.strip();return ' '.join(out.replace('\u200b','').split())
  except urllib.error.HTTPError as e:
   if e.code not in [429,500,502,503,504] or attempt==2:raise
   delay=e.headers.get('Retry-After','');delay=int(delay) if delay.isdigit() else 30*(attempt+1)
   print('PROVIDER_BACKOFF',e.code,delay,flush=True);time.sleep(min(delay,60))
  except Exception:
   if attempt==2:raise
   time.sleep(10)

def adapt(t,loc):
 fixes={'pt-PT':[('DNA','ADN'),('equipe','equipa'),('registro','registo'),('pesquisadores','investigadores'),('sequenciamento','sequenciação'),('compartilhar','partilhar'),('planejar','planear'),('contato','contacto'),('confiável','fiável')],'vi-VN':[('DNA','ADN'),('cừu xanh','cừu xanh bharal'),('hẹn hò','ước tính niên đại'),('tủy sống','tủy xương'),('tủy răng','tủy xương')],'es-ES':[('computadoras','ordenadores')],'mww':[('DNA','cov ntaub ntawv noob caj ces'),('cov pej xeem','cov pab neeg'),('carbon monoxide','carbon')],'ja-JP':[],'ko-KR':[]}
 for a,b in fixes.get(loc,[]):t=t.replace(a,b)
 return t

def run(loc):
 p=S/f'{loc}.json';marker=p.with_suffix('.terminology-v2');partial=p.with_suffix('.partial.json')
 if p.exists() and marker.exists():return
 rows=json.loads(partial.read_text()) if partial.exists() else []
 for n in range(len(rows),12):
  ch=chapters[n];en=translation_source(ch);out=adapt(translate(en,LANGS[loc]),loc)
  english=[x.strip() for x in re.split(r'(?<=[.!?])\s+',en) if len(x.strip())>=20]
  same=[x for x in english if x in out]
  if same:
   for sentence in same:
    time.sleep(3);replacement=adapt(translate(sentence,LANGS[loc]),loc)
    if sentence in replacement:raise ValueError(f'{loc}chapter{n+1}: repeated untranslated sentence: '+sentence[:80])
    out=out.replace(sentence,replacement)
   print('ENGLISH_SPANS_REPAIRED',loc,n+1,len(same),flush=True)
  rows.append(dict(id=n+1,start=int(ch['start_seconds']),end=int(ch['end_seconds']),voice=out,source_en=en,editorial_status='Machine translation with regional terminology adaptation; assistant review pending; native review pending'));partial.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
  print(json.dumps(dict(locale=loc,chapter=n+1,chars=len(out))),flush=True);time.sleep(3)
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(r['voice'] for r in rows));partial.unlink(missing_ok=True)
 p.with_suffix('.provenance.json').write_text(json.dumps(dict(source='Original Baishiya English narration;technical meaning clarified before translation',translation_service='Google public translation web service,chapter context',locale=loc,timing='2chapters120s,10chapters110s',editorial_status='Regional/scientific terminology adapted;independent native editorial/listening review pending',white_hmong_dialect_independently_verified=False if loc=='mww' else None),ensure_ascii=False,indent=2));marker.write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');print('SCRIPT_READY',loc,flush=True)
if __name__=='__main__':
 errors=[]
 for loc in (sys.argv[1:] or list(LANGS)):
  try:run(loc)
  except urllib.error.HTTPError as e:
   print('PROVIDER_ERROR_STOP',e,flush=True);raise
  except Exception as e:errors.append(loc);print('SCRIPT_ERROR',loc,type(e).__name__,str(e),flush=True)
 if errors:raise SystemExit('Incomplete locales: '+','.join(errors))
