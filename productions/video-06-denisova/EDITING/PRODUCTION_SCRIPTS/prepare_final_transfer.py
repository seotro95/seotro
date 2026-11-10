import base64,hashlib,json,re,subprocess,time,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';REPO='seotro95/seotro';P=R/'FINAL_TRANSFER_STATE.json';state=json.load(open(P)) if P.exists() else {'blobs':{},'branch':'codex/denisova-final-transfer-20261110'}
q=json.load(open(O/'FINAL_VIDEO_QA.json'));assert q['status']=='passed' and q['video_duration_seconds']==1260;assert json.load(open(R/'VISUAL_REVIEW_APPROVED.json'))['status']=='passed'
with zipfile.ZipFile(O/'DENISOVA_06_EDIT_PROJECT.zip') as z:assert not any(n.lower().endswith('.mp4') or 'SOURCE_BLOB_STATE' in n for n in z.namelist())
source=json.load(open(R/'SOURCE_MANIFEST.json'));assert all('git_blob_sha' not in x and 'immutable_raw_url' not in x for x in source['clips'])
assets=json.load(open(O/'RELEASE_ASSET_MANIFEST.json'))['assets'];names=[x['name'] for x in assets]+['SHA256SUMS.txt','RELEASE_ASSET_MANIFEST.json'];entries=[];small=[];manifest={'topic':6,'repository':REPO,'release_tag':'denisova-video-06-final-21min','contents':'Only the completed edited video, opening, approved delivery project, subtitles, titles/thumbnail prompts and technical metadata. No raw source video clips or raw-source Git blob references.','raw_source_clips_included':False,'assets':[]}
for name in names:
 assert Path(name).name==name;p=O/name;data=p.read_bytes();h=hashlib.sha256(data).hexdigest();parts=[]
 if p.suffix in ['.txt','.md','.csv','.json','.srt']:
  path='transfer/parts/'+name+'.000.part';entries.append({'path':path,'mode':'100644','type':'blob','content':data.decode('utf-8')});parts=[{'path':path,'bytes':len(data),'sha256':h}]
 elif len(data)<600000:
  path='transfer/parts/'+name+'.000.part';small.append({'path':path,'filename':name,'encoding':'base64','content':base64.b64encode(data).decode()});parts=[{'path':path,'bytes':len(data),'sha256':h}]
 else:
  for n in range((len(data)+16777215)//16777216):
   block=data[n*16777216:(n+1)*16777216];digest=hashlib.sha256(block).hexdigest();key=name+':'+str(n)+':'+digest
   if key not in state['blobs']:
    payload=R/'final-blob-input.json';payload.write_text(json.dumps({'content':base64.b64encode(block).decode(),'encoding':'base64'}))
    expected=hashlib.sha1(b'blob '+str(len(block)).encode()+b'\0'+block).hexdigest()
    for attempt in range(4):
     z=subprocess.run(['gh','api','--include','-X','POST',f'repos/{REPO}/git/blobs','--input',str(payload)],capture_output=True,text=True)
     if z.returncode==0:
      j=json.loads(z.stdout[z.stdout.find('{'):]);assert j['sha']==expected;state['blobs'][key]=j['sha'];P.write_text(json.dumps(state,indent=2));break
     m=re.search(r'(?im)^retry-after:\s*(\d+)',z.stdout)
     if attempt==3 or not (m or any(s in z.stderr for s in ['HTTP 429','HTTP 502','HTTP 503','HTTP 504'])):raise RuntimeError(z.stderr[-1500:])
     time.sleep(int(m[1]) if m else 12*(attempt+1))
    payload.unlink(missing_ok=True)
   path=f'transfer/parts/{name}.{n:03d}.part';entries.append({'path':path,'mode':'100644','type':'blob','sha':state['blobs'][key]});parts.append({'path':path,'bytes':len(block),'sha256':digest});print(json.dumps({'final_output_blob':name,'part':n,'bytes':len(block)}),flush=True)
 manifest['assets'].append({'name':name,'bytes':len(data),'sha256':h,'parts':parts})
publisher='''import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];sha=os.environ['GITHUB_SHA'];base=f'https://raw.githubusercontent.com/{repo}/{sha}/'
m=json.load(urllib.request.urlopen(base+'transfer/manifest.json'));assert m['raw_source_clips_included'] is False
out=Path('delivery');out.mkdir(exist_ok=True)
if subprocess.run(['gh','release','view',m['release_tag'],'--repo',repo],capture_output=True).returncode:
 subprocess.run(['gh','release','create',m['release_tag'],'--repo',repo,'--target','codex/beringia-video-01','--draft','--title','Denisova — Video06 — English final edit21:00','--notes','Completed21minute720p24fps edit. Original English narration only, all clip audio removed, twelve shots in the first30seconds. No raw source clips are included.'],check=True)
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
print('Verified final Denisova release published',flush=True)
'''
workflow='''name: Publish completed Denisova6 final outputs only
on:
  workflow_dispatch:
permissions:
  contents: write
jobs:
  publish:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Verify and publish the finished edit; no raw source clips
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          curl --fail --silent --show-error --location "https://raw.githubusercontent.com/$GITHUB_REPOSITORY/$GITHUB_SHA/transfer/publish.py" -o publish.py
          python -u publish.py
'''
entries.extend([{'path':'transfer/manifest.json','mode':'100644','type':'blob','content':json.dumps(manifest,indent=2)},{'path':'transfer/publish.py','mode':'100644','type':'blob','content':publisher},{'path':'.github/workflows/siberia-final-video.yml','mode':'100644','type':'blob','content':workflow}])
(R/'FINAL_MEDIA_TREE_ENTRIES.json').write_text(json.dumps(entries,ensure_ascii=False));(R/'FINAL_MEDIA_MANIFEST.json').write_text(json.dumps(manifest,indent=2));(R/'FINAL_SMALL_BINARIES.json').write_text(json.dumps(small));print(json.dumps({'completed_output_tree_entries':len(entries),'small_binaries':len(small),'tree_characters':len((R/'FINAL_MEDIA_TREE_ENTRIES.json').read_text())}),flush=True)
