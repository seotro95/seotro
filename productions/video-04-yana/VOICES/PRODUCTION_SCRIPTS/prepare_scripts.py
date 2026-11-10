import concurrent.futures,hashlib,json,re,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';S.mkdir(parents=True,exist_ok=True)
assert (R/'DOCUMENT_DELIVERY_STATE.json').exists()
source=[dict(id=int(a),start=(int(a)-1)*10,end=int(a)*10,voice=b) for a,b in (l.split('\t',1) for l in (R/'script_en.tsv').read_text().splitlines())]
(S/'en-US.json').write_text(json.dumps(source,ensure_ascii=False,indent=2));(S/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in source))
chapters=list(__import__('csv').DictReader(open(R/'package/CHAPTERS_12.csv')))
LANGS={'mww':'hmn','vi-VN':'vi','es-ES':'es','fr-FR':'fr','ja-JP':'ja','ko-KR':'ko','de-DE':'de','it-IT':'it','pt-PT':'pt','nl-NL':'nl','pl-PL':'pl','sv-SE':'sv','da-DK':'da','fi-FI':'fi','nb-NO':'no','cs-CZ':'cs'}
NUMBERS={'thirty one thousand six hundred':'31600','twenty four thousand':'24000','nine thousand eight hundred':'9800','two thousand nineteen':'2019','two thousand one':'2001'}
def translation_source(ch):
 rows=[r for r in source if r['start']>=int(ch['start_seconds']) and r['end']<=int(ch['end_seconds'])]
 text=' '.join(r['voice'] for r in rows)
 # Clarify technical metaphors faithfully for machine translation.
 fixes={
 'a population represented by those individuals':'a genetically studied group of ancient people represented by those individuals',
 'effective population size':'effective population size, a technical estimate of population genetic history',
 'a precise village census':'an exact count of people living in one village',
 'a population history':'a history of groups of people',
 'a guest list':'a list of visitors',
 'a travel diary':'a record of exact journeys',
 "Mal'ta":"the archaeological site of Mal'ta in Siberia",
 'in America,':'in the Americas,',
 'a model fits':'a scientific model fits',
 'a dramatic image of a glowing tooth':'an illustrative image of an artificially glowing tooth'}
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
  for y in ['2001','2019']:
   if y in en and y not in norm:raise ValueError(f'{loc} chapter{n+1}: missing year{y}')
  rows.append(dict(id=n+1,start=int(ch['start_seconds']),end=int(ch['end_seconds']),voice=out,source_en=en));partial.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
  print(json.dumps({'translation':loc,'chapters':len(rows),'characters':len(out)}),flush=True);time.sleep(1)
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(r['voice'] for r in rows));partial.unlink(missing_ok=True)
 p.with_suffix('.provenance.json').write_text(json.dumps({'source':'Original Yana English narration; metaphor/technical meaning clarified faithfully before translation','translation_service':'Google public translation web service, chapter context','locale':loc,'regional_voice_locale':loc,'timing':'Six120-second chapters then six110-second chapters','editorial_status':'Regional lexicon and scientific terminology adapted; independent native editorial/listening review pending','white_hmong_dialect_independently_verified':False if loc=='mww' else None},ensure_ascii=False,indent=2))
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
