"""Translate the owner's nonprivate original narration; keep paragraph boundaries."""
from pathlib import Path
import argparse,json,re,time,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parent

def clear_technical_english(text):
 for a,b in [('June thirtieth, nineteen oh eight','30 June 1908'),('nineteen forty-nine','1949'),('twenty eleven','2011'),('seven seventy-five','775'),('seven seventy-seven','777'),
  ('ice-rich permafrost','permanently frozen ground containing a large amount of ice'),
  ('a thaw slump','a landslide caused by thawing permanently frozen ground'),
  ('the slump','the landslide'),('frost shattering','the breaking of rock caused by water freezing in its cracks'),
  ('bogs, fens, and forested mires','rain-fed peatlands, groundwater-fed peatlands, and forested peatlands'),
  ('A vast area of forest was flattened','The trees across a vast area of forest were knocked down'),
  ("the eddy's centre",'the centre of the rotating water'),('The boundary matters.','The outer edge of the rotating water matters.')]:text=text.replace(a,b)
 # A scientific eddy is a rotating body of water, not an ordinary proper name.
 text=re.sub(r'\beddy\b','rotating water',text)
 return text

def translate(text,language):
 query={'client':'gtx','sl':'en','tl':language,'dt':'t','q':text}
 request=urllib.request.Request('https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode(query),headers={'User-Agent':'SiberiaProduction/1.0'})
 with urllib.request.urlopen(request,timeout=60) as response:result=json.load(response)
 return ''.join(item[0] for item in result[0] if item[0]).strip()

def main(code):
 master=json.loads((ROOT/'master_timeline.json').read_text());rows=[];out=Path('translated');out.mkdir(exist_ok=True)
 for chapter in master['chapters']:
  cues=[c for c in master['cues'] if c['chapter']==chapter['title']]
  source='\n\n'.join(clear_technical_english(c['text']) for c in cues)
  text=translate(source,code)
  parts=re.split(r'\n\s*\n',text)
  if len(parts)!=len(cues):
   parts=[]
   for cue in cues:parts.append(translate(clear_technical_english(cue['text']),code));time.sleep(3)
  assert len(parts)==len(cues)
  for cue,part in zip(cues,parts):
   assert part.strip(),(code,cue['id'])
   for year in re.findall(r'\b(?:1949|2011|775|777|1908)\b',clear_technical_english(cue['text'])):
    assert year in part,(code,cue['id'],'year not retained',year)
   rows.append({**cue,'source_text':cue['text'],'text':part})
  (out/(code+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
  print('Translated',code,chapter['title'],len(rows),'of 59 paragraphs',flush=True);time.sleep(3)
 assert len(rows)==59
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('language');main(p.parse_args().language)
