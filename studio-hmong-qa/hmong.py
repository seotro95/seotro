import traceback
try:
 import json,os,hashlib,time
 from pathlib import Path
 import numpy as np
 import torch,soundfile as sf
 from huggingface_hub import HfApi,snapshot_download
 from transformers import VitsModel,AutoTokenizer
 root=Path(os.environ['RUNNER_TEMP'])/'hmong-qa';root.mkdir()
 repo='facebook/mms-tts-mww'
 info=HfApi().model_info(repo)
 print('::notice title=Hmong source::'+json.dumps({'repo':repo,'revision':info.sha,'card':dict(info.card_data or {})},ensure_ascii=False)[:5000],flush=True)
 folder=Path(snapshot_download(repo,revision=info.sha,local_dir=root/'model',allow_patterns=['*.json','*.safetensors','*.bin','README.md']))
 model=VitsModel.from_pretrained(folder).eval();tokenizer=AutoTokenizer.from_pretrained(folder)
 text='Nyob zoo, kuv yog Hmoob Dawb. Hnub no peb zoo siab tau ntsib koj.'
 inputs=tokenizer(text,return_tensors='pt')
 torch.set_num_threads(4);torch.manual_seed(42)
 t=time.perf_counter()
 with torch.inference_mode():audio=model(**inputs).waveform[0].numpy()
 elapsed=time.perf_counter()-t
 assert len(audio)>1000 and np.isfinite(audio).all() and np.max(np.abs(audio))>0
 sf.write(root/'hmong-rpa.wav',audio,model.config.sampling_rate,subtype='PCM_16')
 report={'repo':repo,'revision':info.sha,'seconds':len(audio)/model.config.sampling_rate,'processing_seconds':elapsed,'sample_rate':model.config.sampling_rate,'text':text,'config':model.config.to_dict(),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}}
 (root/'HMONG-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('::notice title=Hmong synthesis::'+json.dumps({k:v for k,v in report.items() if k not in ['config','files']},ensure_ascii=False),flush=True)
 # Export the exact native character-token model for a lightweight CPU runtime.
 class Export(torch.nn.Module):
  def __init__(self,m):super().__init__();self.m=m
  def forward(self,ids,mask):return self.m(input_ids=ids,attention_mask=mask).waveform
 try:
  torch.onnx.export(Export(model),(inputs['input_ids'],inputs['attention_mask']),root/'model.onnx',input_names=['input_ids','attention_mask'],output_names=['waveform'],dynamic_axes={'input_ids':{0:'batch',1:'text'},'attention_mask':{0:'batch',1:'text'},'waveform':{0:'batch',1:'samples'}},opset_version=17)
  import onnxruntime as ort
  s=ort.InferenceSession(str(root/'model.onnx'),providers=['CPUExecutionProvider'])
  for txt in [text,'Nyob zoo.','Kuv zoo siab heev. Peb yog Hmoob Dawb.']:
   data=tokenizer(txt,return_tensors='np');t=time.perf_counter();a=s.run(None,{'input_ids':data['input_ids'],'attention_mask':data['attention_mask']})[0].reshape(-1)
   assert a.size>1000 and np.isfinite(a).all() and np.max(np.abs(a))>0
   print('::notice title=Hmong ONNX::'+json.dumps({'text':txt,'seconds':len(a)/model.config.sampling_rate,'elapsed':time.perf_counter()-t}),flush=True)
  report['onnx']={'sha256':hashlib.sha256((root/'model.onnx').read_bytes()).hexdigest(),'bytes':(root/'model.onnx').stat().st_size,'passed':True}
  (root/'HMONG-QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 except Exception as e:
  print('::error title=Hmong ONNX export::'+str(e)[:3000],flush=True);raise
except Exception:
 print('::error title=Native Hmong test::'+traceback.format_exc()[-6000:].replace('%','%25').replace('\n','%0A').replace('\r','%0D'),flush=True)
 raise
