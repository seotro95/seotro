import concurrent.futures,hashlib,json,re,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';S.mkdir(parents=True,exist_ok=True)
assert (R/'DOCUMENT_DELIVERY_STATE.json').exists()
source=[dict(id=int(a),start=(int(a)-1)*10,end=int(a)*10,voice=b) for a,b in (l.split('\t',1) for l in (R/'script_en.tsv').read_text().splitlines())]
(S/'en-US.json').write_text(json.dumps(source,ensure_ascii=False,indent=2));(S/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in source))
chapters=list(__import__('csv').DictReader(open(R/'package/CHAPTERS_12.csv')))
LANGS={'mww':'hmn','vi-VN':'vi','es-ES':'es','fr-FR':'fr','ja-JP':'ja','ko-KR':'ko','de-DE':'de','it-IT':'it','pt-PT':'pt','nl-NL':'nl','pl-PL':'pl','sv-SE':'sv','da-DK':'da','fi-FI':'fi','nb-NO':'no','cs-CZ':'cs'}
NUMBERS={'one hundred forty six thousand':'146000','one hundred sixty thousand':'160000','two thousand twenty six':'2026','two thousand twenty five':'2025','two thousand twenty four':'2024','two thousand twenty one':'2021','two thousand nineteen':'2019','two thousand eighteen':'2018','two thousand fourteen':'2014','two thousand twelve':'2012','two thousand ten':'2010','two thousand eight':'2008','Denisova eleven':'Denisova 11','E P A S one':'EPAS1'}
def translation_source(ch):
 rows=[r for r in source if r['start']>=int(ch['start_seconds']) and r['end']<=int(ch['end_seconds'])]
 text=' '.join(r['voice'] for r in rows)
 # Clarify technical metaphors faithfully for machine translation.
 fixes={
 'a population history':'a history of ancient groups of people',
 'nuclear genome':'genome in the cell nucleus',
 'nuclear results':'results from DNA in the cell nucleus',
 'mitochondrial DNA':'mitochondrial DNA, the genetic material in mitochondria',
 'high coverage':'high sequencing coverage',
 'a reading error':'an error in reading a DNA sequence',
 'a genetic grouping':'a group defined by genetic comparisons',
 'a cave can actually preserve about people':'evidence in a cave can actually reveal about people',
 'a ready made photograph':'a complete verified photographic portrait',
 'a census of an ancient population':'a count of all people in an ancient group',
 'a group':'a group',
 'generic':'generic'}
 for a,b in fixes.items():text=text.replace(a,b)
 for a,b in NUMBERS.items():text=text.replace(a,b)
 return text

def translate(text,lang):
 url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode(dict(client='gtx',sl='en',tl=lang,dt='t',q=text))
 for attempt in range(4):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=45) as f:j=json.load(f)
   out=''.join(x[0] for x in j[0] if x and x[0]).replace('\u200b','');assert out.strip();return ' '.join(out.split())
  except urllib.error.HTTPError as e:
   if e.code not in [429,500,502,503,504] or attempt==3:raise
   h=e.headers.get('Retry-After','');delay=int(h) if h.isdigit() else 10*(attempt+1);time.sleep(min(delay,60))
  except Exception:
   if attempt==3:raise
   time.sleep(4*(attempt+1))

def adapt(text,loc):
 replacements={
 'pt-PT':[('DNA','ADN'),('equipe','equipa'),('registro','registo'),('planejar','planear'),('compartilhar','partilhar'),('sequenciamento','sequenciação')],
 'es-ES':[('computadoras','ordenadores')],
 'vi-VN':[('DNA','ADN'),('người Mỹ bản địa','người bản địa châu Mỹ'),('Người Mỹ bản địa','Người bản địa châu Mỹ'),('kích thước dân số hiệu quả','quy mô quần thể hiệu dụng theo mô hình di truyền'),('quy mô dân số hiệu quả','quy mô quần thể hiệu dụng theo mô hình di truyền'),('luồng gen','sự trao đổi gene giữa các quần thể')],
 'mww':[('cov pa roj carbon monoxide','carbon'),('pa roj carbon monoxide','carbon'),('cov pej xeem thaum ub','cov pab neeg thaum ub')],
 'ja-JP':[('有効人口規模','有効集団サイズ'),('有効人口サイズ','有効集団サイズ')],
 'ko-KR':[('유효 인구 규모','유효 집단 크기')],
 'fi-FI':[('tehokas väestökoko','tehollinen populaatiokoko')]
 }
 for a,b in replacements.get(loc,[]):text=text.replace(a,b)
 if loc=='mww':text=re.sub(r'\bDNA\b','cov ntaub ntawv noob caj noob ces',text)
 return text

def run(loc):
 p=S/f'{loc}.json';marker=p.with_suffix('.terminology-v2');partial=p.with_suffix('.partial.json')
 if p.exists() and marker.exists():return loc
 rows=json.loads(partial.read_text()) if partial.exists() else []
 for n in range(len(rows),12):
  ch=chapters[n];en=translation_source(ch);out=adapt(translate(en,LANGS[loc]),loc)
  # Years should survive direct translation; grouping separators may change.
  norm=re.sub(r'[.,\s\u00a0\u202f]','',out)
  for y in ['2008','2010','2012','2014','2018','2019','2021','2024','2025','2026']:
   if y in en and y not in norm:raise ValueError(f'{loc} chapter{n+1}: missing year{y}')
  rows.append(dict(id=n+1,start=int(ch['start_seconds']),end=int(ch['end_seconds']),voice=out,source_en=en));partial.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
  print(json.dumps({'translation':loc,'chapters':len(rows),'characters':len(out)}),flush=True);time.sleep(1)
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(r['voice'] for r in rows));partial.unlink(missing_ok=True)
 p.with_suffix('.provenance.json').write_text(json.dumps({'source':'Original Denisova English narration; metaphor/technical meaning clarified faithfully before translation','translation_service':'Google public translation web service, chapter context','locale':loc,'regional_voice_locale':loc,'timing':'Six110-second chapters then six100-second chapters','editorial_status':'Regional lexicon and scientific terminology adapted; independent native editorial/listening review pending','white_hmong_dialect_independently_verified':False if loc=='mww' else None},ensure_ascii=False,indent=2))
 marker.write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');return loc
if __name__=='__main__':
 import sys
 langs=sys.argv[1:] or list(LANGS)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  fs={pool.submit(run,l):l for l in langs};errors=[]
  for f in concurrent.futures.as_completed(fs):
   try:print('SCRIPT_READY',f.result(),flush=True)
   except Exception as e:errors.append(fs[f]);print('TRANSLATION_ERROR',fs[f],type(e).__name__,str(e),flush=True)
 if errors:raise SystemExit(1)
