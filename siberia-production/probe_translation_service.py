"""Check public web translation quality on nonprivate, original script examples."""
import json,time,urllib.parse,urllib.request
from pathlib import Path
examples=[
 'Around the outer region of the eddy, stronger circulation delivers heat more effectively, thinning the ice into a broad ring.',
 'A pale sand ridge fills the foreground. Sharp mountain ridges form a dramatic background.',
 'Batagaika is a thaw slump, not a meteorite crater. Its story is about exposed ice and collapse, not filling a hole.',
 'Researchers found a remarkable marker in the timber: a radiocarbon increase in 775. They dated construction to the summer of 777.',
 'The property is on UNESCO\'s Tentative List, not inscribed as a World Heritage Site.'
]
out={}
for language in ['vi','fr','ja','fi','hi']:
 q='\n\n'.join(examples)
 url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':'en','tl':language,'dt':'t','q':q})
 request=urllib.request.Request(url,headers={'User-Agent':'SiberiaProduction/1.0'})
 with urllib.request.urlopen(request,timeout=45) as response:data=json.load(response)
 text=''.join(item[0] for item in data[0] if item[0])
 out[language]=text
 print(language,text,flush=True);time.sleep(1)
Path('service_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
