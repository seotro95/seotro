import concurrent.futures,hashlib,json,sys,urllib.request
from pathlib import Path
R=Path(__file__).parent;W=R.parent;mode=sys.argv[1]
def fetch(url,path,sha=None,size=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists():
  part=path.with_suffix(path.suffix+'.partial')
  with urllib.request.urlopen(url,timeout=120) as response,part.open('wb') as f:
   while block:=response.read(1024*1024):f.write(block)
  part.replace(path)
 if sha:assert hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==sha,str(path)
 if size is not None:assert path.stat().st_size==size,str(path)
if mode in ['online','adam']:
 lock=json.loads((R/'MELO_SOURCE_LOCK.json').read_text());names=['online_backend.py'] if mode=='online' else ['worker.py','voice_catalog.py']
 for name in names:fetch(f'https://raw.githubusercontent.com/seotro95/seotro/{lock["source_commit"]}/melo-viet-local/{name}',W/'melo45'/name,lock['files'][name])
 if mode=='adam':
  records=json.loads((R/'ADAM_MODEL_RECORDS.json').read_text())
  def model(v):fetch(v['url'],W/'adam-models45'/v['path'],v['sha256'],v['bytes'])
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(model,records))
  print('NativeAdam model and codec pins verified',flush=True)
 print('PinnedMelo backend ready',mode,flush=True)
elif mode=='hmong':
 revision='061430d958b8d5fc14d04209c6f0cd20492382c2';tree=json.load(urllib.request.urlopen(f'https://api.github.com/repos/seotro95/seotro/git/trees/{revision}?recursive=1'))
 files=[x for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith('voice-studio/hmong_') or x['path']=='voice-studio/assets/hmong/female-3.wav')]
 def code(x):fetch(f'https://raw.githubusercontent.com/seotro95/seotro/{revision}/{x["path"]}',W/'hmong166'/x['path'])
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(code,files))
 sys.path.insert(0,str(W/'hmong166/voice-studio'));from hmong_native_models import MODEL_RECORDS
 def model(item):p,v=item;fetch(v['url'],W/'hmong-models'/p,v['sha256'],v['size'])
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(model,MODEL_RECORDS.items()))
 (W/'hmong-models/verified-native-models.json').write_text(json.dumps({'version':1,'backend':'hmong_native','files':MODEL_RECORDS}))
 assert hashlib.file_digest((W/'hmong166/voice-studio/assets/hmong/female-3.wav').open('rb'),'sha256').hexdigest()=='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17'
 print('NativeHmong models and female3reference verified',flush=True)
else:raise ValueError(mode)
