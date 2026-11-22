from pathlib import Path
import os,json,hashlib,subprocess,zipfile,concurrent.futures
P=Path(__file__).resolve().parent;D=P.parent/'nemi052_documents/documents';ready=json.loads((P/'VOICE_EXPORT_READY.json').read_text());repo=os.environ['GITHUB_REPOSITORY'];tag=ready['release_tag'];assert repo=='seotro95/seotro' and tag=='nemi-video-052-20m22s' and ready['seconds']==1222
inventory=json.loads((P.parent/'nemi052_documents/DOCUMENT_INVENTORY.json').read_text());manifest=json.loads((D/'AUDIO_MANIFEST.json').read_text());assert len(manifest)==16 and len(inventory)==58
for item in inventory:
 f=D/item['path'];assert f.is_relative_to(D) and f.stat().st_size==item['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
for m in manifest:
 f=P/m['filename'];assert f.parent==P and f.suffix=='.mp3' and f.stat().st_size==m['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==m['sha256'];assert m['decoded_seconds']==1222 and m['decoded_samples_48000']==58656000 and m['gender']=='Male'
profiles=json.loads((D/'VOICE_PROFILES_LOCKED.json').read_text())['profiles'];assert len(profiles)==16 and all(p['gender']=='Male' for p in profiles);assert {p['locale']:p['voice_id'] for p in profiles}=={m['locale']:m['voice_id'] for m in manifest}
def archive(name,items,compression):
 f=P/name
 with zipfile.ZipFile(f,'w',compression) as z:
  for path,arc in items:
   info=zipfile.ZipInfo(arc,(2026,11,22,0,0,0));info.compress_type=compression;info.external_attr=0o600<<16;z.writestr(info,path.read_bytes())
 with zipfile.ZipFile(f) as z:assert z.testzip() is None and len(z.namelist())==len(items)
 return f
zipdoc=archive('NEMI_052_TAI_LIEU_20m22s.zip',[(D/m['path'],m['path']) for m in inventory],zipfile.ZIP_DEFLATED)
zipvoice=archive('NEMI_052_16_VOICES_20m22s.zip',[(P/m['filename'],m['filename']) for m in manifest],zipfile.ZIP_STORED)
lookup={f.name:f for f in D.rglob('*') if f.is_file()};lookup.update({m['filename']:P/m['filename'] for m in manifest});lookup.update({zipdoc.name:zipdoc,zipvoice.name:zipvoice});assets=[];checks=[]
for expected in ready['assets']:
 f=lookup[expected['filename']];sha=hashlib.sha256(f.read_bytes()).hexdigest()
 if f.name not in [zipdoc.name,zipvoice.name]:assert f.stat().st_size==expected['bytes'] and sha==expected['sha256']
 assets.append(f);checks.append(dict(filename=f.name,bytes=f.stat().st_size,sha256=sha))
assert len(assets)==48
releases=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases?per_page=100'],text=True));release=next(x for x in releases if x['tag_name']==tag);assert release['draft'];rid=release['id'];old={x['name']:x for x in release['assets']}
def upload(f):
 digest=hashlib.sha256(f.read_bytes()).hexdigest()
 if f.name in old:assert old[f.name]['digest']=='sha256:'+digest;return
 subprocess.run(['gh','release','upload',tag,str(f),'--repo',repo],check=True);print('Uploaded',f.name,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(upload,assets))
qa=dict(topic='052-Nemi-Ships',duration_seconds_each=1222,decoded_samples_each_48000=58656000,voice_count=16,document_file_count=58,all_inputs_sha256_verified=True,tts_generation_executed_in_export=False,export_commit=os.environ['GITHUB_SHA'],independent_native_listening_review=False,assets=checks)
q=P/'PUBLICATION_QA.json';q.write_text(json.dumps(qa,ensure_ascii=False,indent=2));upload(q)
s=P/'NEMI_052_SHA256SUMS.txt';s.write_text(''.join(x['sha256']+'  '+x['filename']+'\n' for x in checks));upload(s)
current=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/{rid}'],text=True));actual={a['name']:a for a in current['assets']}
for x in checks:assert actual[x['filename']]['size']==x['bytes'] and actual[x['filename']]['digest']=='sha256:'+x['sha256']
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--draft=false','--latest=false','--target',os.environ['GITHUB_SHA'],'--notes-file',str(P/'RELEASE_NOTES.txt')],check=True)
print('PUBLISHED_NEMI_052_ALL_16_VOICES_AND_DOCUMENTS',flush=True)
