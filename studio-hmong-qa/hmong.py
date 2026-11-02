import json,traceback
from pathlib import Path
from huggingface_hub import HfApi,hf_hub_download
try:
 api=HfApi()
 for repo in ['svue1986/hmong-tts-pilot-v1','Darejkal/mms-hmong-20260113','Darejkal/g-hmong-v1','Pakorn2112/F5TTS-Hmong','Xuajpaj2026/hmong-tts-weights']:
  try:
   info=api.model_info(repo)
   metadata={'repo':repo,'revision':info.sha,'pipeline':info.pipeline_tag,'card':dict(info.card_data or {}),'files':[x.rfilename for x in info.siblings]}
   print('::notice title=Hmong TTS candidate::'+json.dumps(metadata,ensure_ascii=False)[:9000],flush=True)
   for name in ['README.md','config.json']:
    if name in metadata['files']:
     f=hf_hub_download(repo,name,revision=info.sha);text=Path(f).read_text();print('::notice title='+repo+' '+name+'::'+text[:11000].replace('%','%25').replace('\n','%0A').replace('\r','%0D'),flush=True)
  except Exception as e:print('::notice title=Unavailable model::'+repo+' '+str(e).splitlines()[0],flush=True)
except Exception:
 print('::error title=Native Hmong test::'+traceback.format_exc().replace('\n','%0A'),flush=True);raise
