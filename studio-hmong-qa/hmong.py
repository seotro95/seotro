import traceback
try:
 import json,os,time,hashlib
 from pathlib import Path
 import torch,numpy as np,soundfile as sf
 from huggingface_hub import snapshot_download
 from transformers import VitsModel,AutoTokenizer
 from safetensors.torch import load_file
 repo='svue1986/hmong-tts-pilot-v1';revision='d2c2c012afbf729c9542570516eb3eeaa11f42d3'
 folder=Path(snapshot_download(repo,revision=revision,allow_patterns=['*.json','*.safetensors','README.md']))
 tokenizer=AutoTokenizer.from_pretrained(folder)
 model,info=VitsModel.from_pretrained(folder,output_loading_info=True)
 print('::notice title=Native Hmong loading::'+json.dumps(info,default=str)[:6000],flush=True)
 if info['missing_keys']:
  state=load_file(folder/'model.safetensors');print('::notice title=Hmong weight keys::'+json.dumps(list(state)[:35]),flush=True)
  raise ValueError('Native model did not load all inference weights')
 model.eval();torch.set_num_threads(4)
 out=Path(os.environ['RUNNER_TEMP'])/'hmong-qa';out.mkdir();results=[]
 for i,text in enumerate(['Nyob zoo, kuv yog Hmoob Dawb. Hnub no peb zoo siab tau ntsib koj.','Kuv zoo siab heev. Peb yog Hmoob Dawb.','Koj puas nyob zoo? Ua tsaug ntau.']):
  data=tokenizer(text,return_tensors='pt');assert not (data['input_ids']==tokenizer.unk_token_id).any()
  t=time.perf_counter()
  with torch.inference_mode():x=model(**data).waveform[0].numpy()
  assert x.size>1000 and np.isfinite(x).all() and np.max(np.abs(x))>0
  sf.write(out/f'hmong-rpa-{i}.wav',x,model.config.sampling_rate,subtype='PCM_16')
  r={'text':text,'seconds':len(x)/model.config.sampling_rate,'elapsed':time.perf_counter()-t};results.append(r);print('::notice title=Native Hmong WAV::'+json.dumps(r,ensure_ascii=False),flush=True)
 report={'repo':repo,'revision':revision,'results':results,'dialect_verified_by_native_listener':False,'gender':'Unknown','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}}
 (out/'HMONG-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
except Exception:
 print('::error title=Hmong pilot integration::'+traceback.format_exc()[-6000:].replace('%','%25').replace('\n','%0A'),flush=True);raise
