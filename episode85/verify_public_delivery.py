"""Verify the public delivery, without retaining decoded PCM or exposing credentials."""
import hashlib,json,subprocess,urllib.request,wave,zipfile
from pathlib import Path
R=Path(__file__).parent
TAG='homo-luzonensis-video-85-21m22s'
BASE=f'https://github.com/seotro95/seotro/releases/download/{TAG}/'
FRAMES=61536000
release=json.loads(subprocess.check_output(['gh','api',f'repos/seotro95/seotro/releases/tags/{TAG}']))
assets={a['name']:a for a in release['assets']}
name='HOMO_LUZONENSIS_85_17_VOICES_21m22s.zip'
assert name in assets,'Full voice release not published yet'
archive=R/name
expected=assets[name].get('digest','').removeprefix('sha256:')
assert expected and assets[name]['size']<400_000_000
if not archive.exists() or archive.stat().st_size!=assets[name]['size'] or hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()!=expected:
 partial=archive.with_suffix('.partial')
 h=hashlib.sha256()
 with urllib.request.urlopen(BASE+name,timeout=90) as response,partial.open('wb') as out:
  while block:=response.read(1024*1024):out.write(block);h.update(block)
 assert h.hexdigest()==expected and partial.stat().st_size==assets[name]['size']
 partial.replace(archive)
print('PUBLIC_ZIP_SHA256_VERIFIED',expected,flush=True)
baseline=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
identities={p['locale']:p['voice_id'] for p in baseline['profiles']}
verified=[]
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 names=z.namelist();mp3s=[n for n in names if n.endswith('.mp3')]
 assert len(mp3s)==17 and len(names)==20
 manifest=json.loads(z.read('AUDIO_MANIFEST.json'))
 qa=json.loads(z.read('VOICE_RELEASE_QA.json'))
 profiles=json.loads(z.read('VOICE_PROFILES_LOCKED.json'))
 assert manifest['target_seconds']==1282 and qa['status']=='passed'
 assert {p['locale']:p['voice_id'] for p in profiles['profiles']}==identities
 assert len(manifest['voices'])==17 and len({v['sha256'] for v in manifest['voices']})==17
 assert sum(v['gender']=='Male' for v in manifest['voices'])==16
 for v in manifest['voices']:
  n=v['filename'];assert n in mp3s and n in assets
  assert v['voice_id']==identities[v['locale']]
  assert v['seconds']==1282 and v['frames_at_48000']==FRAMES
  assert assets[n]['digest']=='sha256:'+v['sha256'] and assets[n]['size']==v['bytes']
  with urllib.request.urlopen(urllib.request.Request(v['url'],method='HEAD'),timeout=60) as response:
   assert response.status==200
   if response.headers.get('Content-Length'):assert int(response.headers['Content-Length'])==v['bytes']
  p=R/'VERIFY_CURRENT_VOICE.mp3';p.write_bytes(z.read(n))
  assert p.stat().st_size==v['bytes'] and hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==v['sha256']
  process=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-threads','1','-i',str(p),'-ac','1','-ar','48000','-f','s16le','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  count=0
  while block:=process.stdout.read(1024*1024):count+=len(block)
  error=process.stderr.read().decode(errors='replace');assert process.wait()==0,error
  assert count==FRAMES*2,(n,count)
  p.unlink();verified.append({'locale':v['locale'],'filename':n,'sha256':v['sha256'],'decoded_frames_48000':count//2,'public_asset_digest_matches':True,'country_download_url_http_200':True})
  print('PUBLIC_AUDIO_VERIFIED',v['locale'],count//2,flush=True)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:(R/n).write_bytes(z.read(n))
result={'status':'passed','topic_id':85,'public_voice_archive_sha256':expected,'voice_count':17,'target_seconds':1282,'decoded_frames_per_voice_48000':FRAMES,'all_country_asset_digests_match':True,'episode85_locked_voice_ids_match':True,'vietnamese_voice_id':'vi-VN-NamMinhNeural','zip_crc_passed':True,'voices':verified,'independent_native_listening_review':False,'white_hmong_dialect_independently_verified':False}
(R/'PUBLIC_DOWNLOAD_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('ALL_17_PUBLIC_VOICES_VERIFIED',flush=True)
