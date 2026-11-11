import concurrent.futures,hashlib,json,sys,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parent;W=R.parent
revision='061430d958b8d5fc14d04209c6f0cd20492382c2'
tree=json.load(urllib.request.urlopen(f'https://api.github.com/repos/seotro95/seotro/git/trees/{revision}?recursive=1'))
def code(item):
    p=item['path'];dest=W/'hmong166'/p;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():dest.write_bytes(urllib.request.urlopen(f'https://raw.githubusercontent.com/seotro95/seotro/{revision}/{p}').read())
files=[x for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith('voice-studio/hmong_') or x['path']=='voice-studio/assets/hmong/female-3.wav')]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(code,files))
sys.path.insert(0,str(W/'hmong166/voice-studio'))
from hmong_native_models import MODEL_RECORDS
root=W/'hmong-models';root.mkdir(exist_ok=True)
def model(item):
    p,r=item;dest=root/p;dest.parent.mkdir(exist_ok=True,parents=True)
    if not dest.exists():urllib.request.urlretrieve(r['url'],dest)
    assert dest.stat().st_size==r['size'] and hashlib.sha256(dest.read_bytes()).hexdigest()==r['sha256']
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(model,MODEL_RECORDS.items()))
(root/'verified-native-models.json').write_text(json.dumps(dict(version=1,backend='hmong_native',files=MODEL_RECORDS)))
tool=W/'melo';tool.mkdir(exist_ok=True)
(tool/'online_backend.py').write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/seotro95/seotro/4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043/melo-viet-local/online_backend.py').read())
print('Pinned tool code, native weights and female-3 reference ready.')
