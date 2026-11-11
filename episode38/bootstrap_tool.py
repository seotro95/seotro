import concurrent.futures,hashlib,json,sys,urllib.request
from pathlib import Path
R=Path(__file__).parent;W=R.parent
mode=sys.argv[1] if len(sys.argv)>1 else 'online'
def fetch(url,path,sha=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists():path.write_bytes(urllib.request.urlopen(url,timeout=90).read())
 if sha:assert hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==sha,str(path)
if mode=='online':
 fetch('https://raw.githubusercontent.com/seotro95/seotro/4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043/melo-viet-local/online_backend.py',W/'melo/online_backend.py','bd21a00f93124a4dcc27850c42817bd4823445d4d44882d26cd1503fe2ab568b')
 print('Pinned Melo1.3.1 online_backend ready',flush=True)
elif mode=='native':
 revision='061430d958b8d5fc14d04209c6f0cd20492382c2'
 tree=json.load(urllib.request.urlopen(f'https://api.github.com/repos/seotro95/seotro/git/trees/{revision}?recursive=1'))
 files=[x for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith('voice-studio/hmong_') or x['path']=='voice-studio/assets/hmong/female-3.wav')]
 def code(x):
  p=x['path'];fetch(f'https://raw.githubusercontent.com/seotro95/seotro/{revision}/{p}',W/'hmong166'/p)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(code,files))
 sys.path.insert(0,str(W/'hmong166/voice-studio'));from hmong_native_models import MODEL_RECORDS
 root=W/'hmong-models';root.mkdir(exist_ok=True)
 def model(item):
  p,v=item;fetch(v['url'],root/p,v['sha256']);assert (root/p).stat().st_size==v['size']
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(model,MODEL_RECORDS.items()))
 (root/'verified-native-models.json').write_text(json.dumps({'version':1,'backend':'hmong_native','files':MODEL_RECORDS}))
 assert hashlib.file_digest((W/'hmong166/voice-studio/assets/hmong/female-3.wav').open('rb'),'sha256').hexdigest()=='ffa26422055a9da069ba8d7a9d780405b6504c27ce70fa5ad3ffed84f5b2dc17'
 print('Pinned Hmong1.6.6, models and female-3 reference ready',flush=True)
else:raise ValueError(mode)
