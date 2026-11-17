import concurrent.futures,json,time,urllib.error,urllib.parse,urllib.request,subprocess
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';S=R/'voice/scripts'
chapters=json.loads((D/'CHAPTERS_13.json').read_text())
patch=[('twenty-five hundred BCE','2500 BCE'),('three thousand BCE','3000 BCE'),('twenty twenty-four','2024'),('twenty twenty-six','2026'),('twenty twenty','2020'),('nineteen fifty-eight','1958'),('Stone fifty-eight','Stone 58'),('twenty-five kilometers','25 kilometers'),('Fifty of the fifty-two stones','50 of the 52 stones'),('The center of mass matters.','The position of the stone block’s centre of gravity matters.'),('Dressing and fitting required time and skilled effort.','Shaping the rock surfaces and fitting the stone joints required time and skilled effort.'),('human transport','people transporting the stone'),('human movement','movement of the stone by people'),('human journey','journey of the stone with people'),('A core from Stone 58','A cylindrical drill-core rock sample from Stone 58'),('a socket','a stonehole in the ground'),('the socket','the stonehole in the ground'),('sockets','stoneholes in the ground'),('packing of a stonehole','small stones packed around the base inside a stonehole'),('rubble packing','small rubble stones packed around the upright base'),('Packing around its base','Small rubble stones packed around its base'),('socket,','stonehole in the ground,'),('socket.','stonehole in the ground.'),('Horizontal lintels','Horizontal stone beams'),('the lintels','the horizontal stone beams'),('adjoining lintels','adjoining horizontal stone beams'),('a lintel','a horizontal stone beam'),('A sledge','A wooden hauling sled'),('a sledge','a wooden hauling sled'),('the sledge','the wooden hauling sled'),('raising frame','timber frame proposed for erecting stones'),('raising it','erecting the stone'),('ways of raising','ways of erecting the stone'),('the raising','erecting the stones'),('an upright','an upright standing stone'),('An upright','An upright standing stone'),('recesses in','carved hollows in'),('concrete evidence','direct physical evidence'),('which faces and connections','which stone surfaces and joints')]
for c in chapters:
 c['original_voice']=c['voice']
 for a,b in patch:c['voice']=c['voice'].replace(a,b)
(R/'LOCALIZATION_SOURCE_CHAPTERS.json').write_text(json.dumps(chapters,ensure_ascii=False,indent=2)+'\n')
languages={'vi-VN':'vi','es-ES':'es','fr-FR':'fr','ja-JP':'ja','ko-KR':'ko','de-DE':'de','it-IT':'it','pt-PT':'pt-PT','nl-NL':'nl','pl-PL':'pl','sv-SE':'sv','da-DK':'da','fi-FI':'fi','nb-NO':'no','cs-CZ':'cs'}
def translate(text,language):
 query=urllib.parse.urlencode({'client':'gtx','sl':'en','tl':language,'dt':'t','q':text})
 for attempt in range(4):
  try:
   req=urllib.request.Request('https://translate.googleapis.com/translate_a/single?'+query,headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=40) as response:result=json.load(response)
   body=''.join(x[0] for x in result[0] if x and x[0]).replace('\u200b','').strip()
   assert body!=text and len(body)>len(text)*.1
   return body
  except urllib.error.HTTPError as e:
   if e.code in (401,403,429) or attempt==3:raise
   time.sleep(min(8,2**attempt))
  except Exception:
   if attempt==3:raise
   time.sleep(min(8,2**attempt))
def job(item):
 locale,language=item;p=S/(locale+'.context-draft.json');rows=json.loads(p.read_text()) if p.exists() else []
 for c in chapters[len(rows):]:
  rows.append({**c,'source_voice':c['voice'],'voice':translate(c['voice'],language),'locale':locale,'translation_method':'Automated contextual draft; assistant review pending; not independently native-reviewed'})
  p.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print('DRAFT',locale,len(rows),flush=True);time.sleep(.25)
 assert len(rows)==13 and rows[-1]['end']==1292
 return locale
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for locale in pool.map(job,languages.items()):print('DRAFT_DONE',locale,flush=True)
