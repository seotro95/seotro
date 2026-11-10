import concurrent.futures,hashlib,json,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from prepare_scripts import LANGS
R=Path(__file__).parent;S=R/'voice/scripts';O=R/'backtranslation_review';O.mkdir(exist_ok=True)
def back(text,source_lang):
 url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode(dict(client='gtx',sl=source_lang,tl='en',dt='t',q=text))
 for n in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=45) as f:j=json.load(f)
   return ' '.join(''.join(x[0] for x in j[0] if x and x[0]).split())
  except urllib.error.HTTPError as e:
   if e.code in [401,403] or n==2:raise
   wait=max(5*(n+1),int(e.headers.get("Retry-After","0")))
   time.sleep(wait)
  except (TimeoutError,urllib.error.URLError):
   if n==2:raise
   time.sleep(5*(n+1))
def run(loc):
 rows=json.loads((S/f'{loc}.json').read_text());result=[]
 for n in range(12):
  row=rows[n];h=hashlib.sha256(row['voice'].encode()).hexdigest();p=O/f'{loc}-{n+1:02d}.json'
  if p.exists() and json.loads(p.read_text()).get('voice_text_sha256')==h:continue
  text=back(row['voice'],LANGS[loc]);obj=dict(locale=loc,chapter=n+1,voice_text_sha256=h,backtranslated_en=text,note='Machine backtranslation used only for assistant meaning audit, not native certification or replacement of the localized script.');p.write_text(json.dumps(obj,ensure_ascii=False,indent=2));print(json.dumps({'back_review_ready':loc,'chapter':n+1}),flush=True);time.sleep(1)
 return loc
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for x in pool.map(run,[l for l in LANGS if l not in ['mww','vi-VN']]):print('BACK_READY',x,flush=True)
