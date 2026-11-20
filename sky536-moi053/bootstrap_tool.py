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
if mode=='online':
 lock=json.loads((R/'MELO_SOURCE_LOCK.json').read_text())
 fetch(f'https://raw.githubusercontent.com/seotro95/seotro/{lock["source_commit"]}/melo-viet-local/online_backend.py',W/'melo-sky536053/online_backend.py',lock['files']['online_backend.py'])
 print('PinnedMelo online backend ready',flush=True)
else:raise ValueError('Only the online backend is required for these16 voices')

