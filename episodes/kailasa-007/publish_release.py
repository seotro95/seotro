"""Reassemble verified synthetic narration files and save an owner-visible draft.

Runs only in the scoped GitHub Actions workflow. No credentials are logged.
"""
import argparse,hashlib,json,os,shutil,time,urllib.error,urllib.parse,urllib.request,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--parts',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args()
manifest=json.loads(Path(a.manifest).read_text());parts=Path(a.parts);out=Path(a.out);out.mkdir(exist_ok=True,parents=True)
token=os.environ['GH_TOKEN'];repo=manifest['repository'];api='https://api.github.com/repos/'+repo
def request(url,method='GET',data=None,kind='application/json'):
 payload=json.dumps(data).encode() if data is not None and kind=='application/json' else data
 req=urllib.request.Request(url,data=payload,method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':kind,'X-GitHub-Api-Version':'2022-11-28','User-Agent':'kailasa-007-delivery'})
 for attempt in range(4):
  try:
   with urllib.request.urlopen(req,timeout=900) as r:
    b=r.read();return json.loads(b) if b else None
  except urllib.error.HTTPError as e:
   if e.code not in [429,500,502,503,504] or attempt==3:raise
   time.sleep(3*(attempt+1))
def sha(q):
 h=hashlib.sha256()
 with q.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
for file in manifest['transfer']['files']:
 q=parts/file['name'];assert q.stat().st_size==file['bytes'] and sha(q)==file['sha256'],q
v=manifest['voices_package'];joined=out/v['file']
with joined.open('wb') as f:
 for name in v['parts']:
  with (parts/name).open('rb') as src:shutil.copyfileobj(src,f)
assert joined.stat().st_size==v['bytes'] and sha(joined)==v['sha256']
with zipfile.ZipFile(joined) as z:
 assert z.testzip() is None
 for name in z.namelist():assert Path(name).name==name and not name.startswith('.'),name
 z.extractall(out)
for asset in manifest['assets']:
 if asset['source']=='transfer':shutil.copyfile(parts/asset['name'],out/asset['name'])
 elif asset['source'].startswith('text:'):shutil.copyfile(Path(a.manifest).parent/asset['source'][5:],out/asset['name'])
 q=out/asset['name'];assert q.stat().st_size==asset['bytes'] and sha(q)==asset['sha256'],asset['name']
# Locate the exact draft by its unique tag; never modify unrelated releases.
releases=request(api+'/releases?per_page=100')
matches=[r for r in releases if r['tag_name']==manifest['release_tag']]
assert len(matches)<=1
body=Path(a.manifest).with_name('RELEASE_BODY.md').read_text()
if matches:
 release=matches[0];assert release['draft'], 'This job only manages its own draft release.'
else:
 release=request(api+'/releases','POST',{'tag_name':manifest['release_tag'],'target_commitish':os.environ['GITHUB_SHA'],'name':'Kailasa 001 — 22:32 | 136 prompts | 16 male voices','draft':True,'prerelease':False,'body':body})
release_id=release['id'];upload=release['upload_url'].split('{')[0]
for asset in manifest['assets']:
 current=request(api+f'/releases/{release_id}/assets?per_page=100')
 existing=next((x for x in current if x['name']==asset['name']),None)
 expected='sha256:'+asset['sha256']
 if existing and existing.get('digest')==expected and existing['size']==asset['bytes']:
  print('Verified existing',asset['name'],flush=True);continue
 if existing:request(api+f"/releases/assets/{existing['id']}",'DELETE')
 with (out/asset['name']).open('rb') as f:data=f.read()
 try:
  result=request(upload+'?'+urllib.parse.urlencode({'name':asset['name']}),'POST',data,'application/octet-stream')
 except urllib.error.HTTPError as e:
  if e.code!=422:raise
  check=request(api+f'/releases/{release_id}/assets?per_page=100')
  result=next((x for x in check if x['name']==asset['name']),None)
  assert result and result.get('digest')==expected and result['size']==asset['bytes']
 del data
 assert result['state']=='uploaded' and result['size']==asset['bytes'] and result.get('digest')==expected,result.get('name')
 print('Uploaded and SHA256 verified',asset['name'],flush=True)
current=request(api+f'/releases/{release_id}/assets?per_page=100')
verified=[]
for asset in manifest['assets']:
 r=next(x for x in current if x['name']==asset['name'])
 assert r['state']=='uploaded' and r['size']==asset['bytes'] and r['digest']=='sha256:'+asset['sha256']
 verified.append({'name':r['name'],'asset_id':r['id'],'bytes':r['size'],'sha256':asset['sha256'],'download_url':r['browser_download_url'],'kind':asset['kind']})
assert len([x for x in verified if x['kind']=='voice_mp3'])==16
verification={'status':'all_expected_assets_uploaded_and_server_digests_verified','release_id':release_id,'draft':True,'html_url':release['html_url'],'tag_name':manifest['release_tag'],'source_commit':os.environ['GITHUB_SHA'],'target_seconds':1352,'voice_count':16,'assets':verified}
report=out/'GITHUB_DELIVERY_VERIFIED.json';report.write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
old=next((x for x in current if x['name']==report.name),None)
if old:request(api+f"/releases/assets/{old['id']}",'DELETE')
request(upload+'?name='+report.name,'POST',report.read_bytes(),'application/octet-stream')
# Only remove this job's own temporary binary-transfer branch, after verification.
ref='git/ref/heads/'+manifest['transfer']['branch']
try:
 r=request(api+'/'+ref)
 assert r['object']['sha']==manifest['transfer']['commit'], 'Transfer branch changed; leave it untouched.'
 request(api+'/git/refs/heads/'+manifest['transfer']['branch'],'DELETE')
 print('Removed own temporary transfer branch',flush=True)
except urllib.error.HTTPError as e:
 if e.code!=404:raise
summary=Path(os.environ['GITHUB_STEP_SUMMARY'])
with summary.open('a') as f:
 f.write('## Kailasa 001 delivery verified\n\n'+release['html_url']+'\n\n')
 for r in verified:f.write(f"- [{r['name']}]({r['download_url']}) — SHA-256 verified\n")
print(json.dumps({'release_id':release_id,'html_url':release['html_url'],'verified_assets':len(verified)}),flush=True)
