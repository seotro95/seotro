import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];sha=os.environ['GITHUB_SHA'];base=f'https://raw.githubusercontent.com/{repo}/{sha}/'
m=json.load(urllib.request.urlopen(base+'transfer/manifest.json'));assert m['raw_source_clips_included'] is False
out=Path('delivery');out.mkdir(exist_ok=True)
if subprocess.run(['gh','release','view',m['release_tag'],'--repo',repo],capture_output=True).returncode:
 subprocess.run(['gh','release','create',m['release_tag'],'--repo',repo,'--target','codex/beringia-video-01','--draft','--title','Baishiya — Video08 — English final edit22:20','--notes','Completed22minute20second720p24fps edit. Original English narration only, all clip audio removed, twelve shots in the first30seconds. No raw source clips are included.'],check=True)
for a in m['assets']:
 p=out/a['name'];digest=hashlib.sha256();size=0
 with p.open('wb') as f:
  for part in a['parts']:
   hh=hashlib.sha256();count=0
   with urllib.request.urlopen(base+part['path'],timeout=90) as response:
    while True:
     block=response.read(1048576)
     if not block:break
     f.write(block);digest.update(block);hh.update(block);size+=len(block);count+=len(block)
   assert hh.hexdigest()==part['sha256'] and count==part['bytes']
 assert digest.hexdigest()==a['sha256'] and size==a['bytes']
 subprocess.run(['gh','release','upload',m['release_tag'],str(p),'--repo',repo,'--clobber'],check=True)
 print(json.dumps({'uploaded_final_output':a['name'],'bytes':size,'sha256':digest.hexdigest()}),flush=True)
 if a['name']=='README.md':subprocess.run(['gh','release','edit',m['release_tag'],'--repo',repo,'--notes-file',str(p)],check=True)
 p.unlink()
subprocess.run(['gh','release','edit',m['release_tag'],'--repo',repo,'--draft=false','--latest=false'],check=True)
print('Verified final Baishiya release published',flush=True)
