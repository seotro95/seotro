import hashlib,json,time,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent;release=json.loads((R/'RELEASE_METADATA.json').read_text());name='BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip';asset=next(x for x in release['assets'] if x['name']==name);p=R/'verified-release'/name;h=hashlib.sha256();n=0;milestone=0
with urllib.request.urlopen(asset['browser_download_url'],timeout=45) as f,p.open('wb') as out:
 while True:
  b=f.read(1048576)
  if not b:break
  out.write(b);h.update(b);n+=len(b)
  if n//(32*1048576)>milestone:milestone=n//(32*1048576);print('ArchiveMB',n//1048576,flush=True)
assert n==asset['size'] and 'sha256:'+h.hexdigest()==asset['digest']
manifest=json.loads((R/'verified-release/details/AUDIO_MANIFEST.json').read_text());expected={x['filename']:x for x in manifest['voices']};verified=[]
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 assert len([i for i in z.namelist() if i.endswith('.mp3')])==17
 for info in z.infolist():assert not info.filename.startswith('/') and '..' not in Path(info.filename).parts
 for filename,m in expected.items():
  d=hashlib.sha256();size=0
  with z.open(filename) as f:
   while True:
    b=f.read(1048576)
    if not b:break
    d.update(b);size+=len(b)
  assert size==m['bytes'] and d.hexdigest()==m['sha256'];verified.append(filename)
qa=dict(status='passed',archive=name,bytes=n,sha256=h.hexdigest(),public_server_digest_matches=True,zip_crc_all_entries_passed=True,mp3_count=17,all17_members_match_individual_voice_manifest=True,verified_filenames=verified,derived_download_cache_deleted_after_verification=True)
(R/'VOICE_ARCHIVE_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));p.unlink();print(json.dumps(qa),flush=True)
