import json,traceback,urllib.request
for repo in ['svue1986/hmong-tts-pilot-v1','Darejkal/mms-hmong-20260113','Pakorn2112/F5TTS-Hmong','Xuajpaj2026/hmong-tts-weights']:
 try:
  with urllib.request.urlopen('https://huggingface.co/api/models/'+repo) as f:j=json.load(f)
  files=[x['rfilename'] for x in j.get('siblings',[])];print('::notice title=Hmong raw metadata::'+json.dumps({'repo':repo,'revision':j['sha'],'card':j.get('cardData'),'files':files[:40]},ensure_ascii=False)[:9000],flush=True)
  for name in ['README.md','config.json']:
   if name in files:
    try:
     with urllib.request.urlopen('https://huggingface.co/'+repo+'/resolve/main/'+name) as f:s=f.read().decode()
     print('::notice title=Hmong document '+repo+' '+name+'::'+s[:18000].replace('%','%25').replace('\n','%0A').replace('\r','%0D'),flush=True)
    except Exception:print('::notice title=Hmong document unavailable::'+repo+' '+traceback.format_exc()[-1500:].replace('\n','%0A'),flush=True)
 except Exception:print('::notice title=Hmong metadata failed::'+repo+' '+traceback.format_exc()[-2000:].replace('\n','%0A'),flush=True)
