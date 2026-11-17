import csv,datetime,hashlib,io,json,os,shutil,subprocess,tempfile,time,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent;TAG='stonehenge-moi-027-21m32s';REPO='seotro95/seotro';BASE=f'https://github.com/{REPO}/releases/download/{TAG}/';FRAMES=62016000;RUN=44104664174
FFMPEG=shutil.which('ffmpeg') or __import__('imageio_ffmpeg').get_ffmpeg_exe()
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def fetch(url,out):
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Stonehenge-public-delivery-check'}),timeout=90) as response,out.open('wb') as f:shutil.copyfileobj(response,f)
   return
  except Exception:
   if attempt==2:raise
   time.sleep(3)
def ghapi(path):return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/'+path]))
for attempt in range(118):
 run=ghapi(f'actions/runs/{RUN}')
 if run['conclusion']=='success':break
 if run['status']=='completed':raise RuntimeError('Country delivery is incomplete; preserve checkpoints and recover failed jobs before archiving')
 print('WAITING_FOR_VERIFIED_VOICE_DELIVERY',attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('Voice delivery not ready')
release=ghapi(f'releases/tags/{TAG}');assets={x['name']:x for x in release['assets']}
D=R/'verified-public-documents';D.mkdir(exist_ok=True)
reports=[]
with tempfile.TemporaryDirectory(prefix='stonehenge-public-') as td:
 tmp=Path(td);doc=tmp/'documents.zip';audio=tmp/'voices.zip';prompts=tmp/'prompts.zip'
 for name,dest in [('STONEHENGE_MOI027_TAI_LIEU_21m32s.zip',doc),('STONEHENGE_MOI027_16_VOICES_21m32s.zip',audio),('STONEHENGE_MOI027_PROMPT_NGOAI_TROI_14_TXT.zip',prompts)]:
  fetch(BASE+name,dest);assert sha(dest)==assets[name]['digest'].removeprefix('sha256:'),(name,'public SHA mismatch')
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None
  print('PUBLIC_ZIP_VERIFIED',name,dest.stat().st_size,flush=True)
 with zipfile.ZipFile(doc) as z:
  for item in z.infolist():
   assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
  z.extractall(D)
 q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['voices_generated'] and q['target_seconds']==1292 and q['english_cues']==130
 assert q['unique_prompts']==140 and q['prompt_txt_files']==14 and q['timeline_shots']==137 and q['outdoor_scenes']==140 and q['laboratory_scenes']==0
 allshots=json.loads((D/'ALL_PROMPTS.json').read_text());assert len(allshots)==140
 assert all(x['generation_seconds']==10 and x['prompt'].endswith('Video không có âm thanh, không có lời nói.') and 'No children' in x['prompt'] and 'All scenes are outdoors.' in x['prompt'] for x in allshots)
 assert sum(x['use_seconds'] for x in allshots)==1292 and sum(x['used'] for x in allshots)==137
 assert [x['id'] for x in allshots if not x['used']]==[138,139,140]
 assert len({x['prompt'] for x in allshots})==140
 promptfiles=sorted((D/'PROMPTS').glob('*.txt'));assert len(promptfiles)==14
 for i,p in enumerate(promptfiles):
  ids=__import__('re').findall(r'^(\d{3})\. ',p.read_text(),flags=__import__('re').M)
  assert list(map(int,ids))==list(range(i*10+1,i*10+11))
 with zipfile.ZipFile(prompts) as z:
  assert len(z.namelist())==14
  for p in promptfiles:assert z.read(p.name)==p.read_bytes()
 manifest=json.loads((D/'AUDIO_MANIFEST.json').read_text());profile=json.loads((D/'VOICE_PROFILES_LOCKED.json').read_text());baseline=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
 locked={p['locale']:p['voice_id'] for p in baseline['profiles']}
 assert len(manifest['voices'])==16 and all(p['gender']=='Male' for p in profile['profiles'])
 assert {p['locale']:p['voice_id'] for p in profile['profiles']}==locked
 with zipfile.ZipFile(audio) as z:
  assert len([x for x in z.namelist() if x.endswith('.mp3')])==16
  for v in manifest['voices']:
   assert v['voice_id']==locked[v['locale']] and v['seconds']==1292 and v['frames_at_48000']==FRAMES
   content=z.read(v['filename']);assert hashlib.sha256(content).hexdigest()==v['sha256']==assets[v['filename']]['digest'].removeprefix('sha256:')
   out=tmp/'one.mp3';out.write_bytes(content)
   proc=subprocess.Popen([FFMPEG,'-v','error','-nostdin','-i',str(out),'-ar','48000','-ac','1','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);count=0
   while block:=proc.stdout.read(1024*1024):count+=len(block)
   error=proc.stderr.read().decode('utf-8','replace');assert proc.wait()==0,error;assert count==FRAMES*2,(v['locale'],count)
   with urllib.request.urlopen(urllib.request.Request(v['url'],method='HEAD',headers={'User-Agent':'Stonehenge-public-delivery-check'}),timeout=60) as response:assert response.status==200
   report=json.loads((D/'REPORTS'/f"{v['locale']}.json").read_text())
   source=R/'voice/scripts'/f"{v['locale']}.json"
   assert report['script_sha256']==sha(source)
   reports.append(dict(locale=v['locale'],filename=v['filename'],voice_id=v['voice_id'],decoded_frames_48000=FRAMES,seconds=1292,sha256=v['sha256'],public_url_status=200))
   print('PUBLIC_MP3_FULL_DECODE_PASSED',v['locale'],FRAMES,flush=True)
 qa=dict(status='passed',topic_id='MOI-027',verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target_seconds=1292,voices=16,all_decoded_frames_48000=FRAMES,all_16_ids_retained=True,public_mp3_urls_checked=16,zip_crc_and_public_github_sha_verified=True,english_script_words=q['english_words'],prompt_txt_files=14,unique_prompts=140,timeline_shots=137,outdoor_scenes=140,laboratory_scenes=0,backup_prompt_ids=[138,139,140],audio_zip_sha256=sha(audio),documents_zip_sha256=sha(doc),prompts_zip_sha256=sha(prompts),independent_native_listening_review=False,footage_generated=False,thumbnail_generated=False,video_edited=False,reports=reports)
 dump(R/'PUBLIC_DELIVERY_QA.json',qa)
# Final delivery-state asset and readable archive, without changing audio or the verified ZIPs.
state_asset=dict(documents_published=True,target_seconds=1292,full_voices_published=True,public_delivery_verified=True,voices=16)
dump(R/'DOCUMENT_DELIVERY_STATE.json',state_asset)
for p in [R/'PUBLIC_DELIVERY_QA.json',R/'DOCUMENT_DELIVERY_STATE.json']:subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
release=ghapi(f'releases/tags/{TAG}');byname={x['name']:x for x in release['assets']}
for name in ['PUBLIC_DELIVERY_QA.json','DOCUMENT_DELIVERY_STATE.json','KICH_BAN_EN_21m32s.txt','5_TIEU_DE_VA_THUMBNAIL.txt']:
 with urllib.request.urlopen(urllib.request.Request(BASE+name,headers={'User-Agent':'Stonehenge-final-text-check'}),timeout=60) as response:body=response.read();assert response.status==200
 assert hashlib.sha256(body).hexdigest()==byname[name]['digest'].removeprefix('sha256:'),name
 if name=='DOCUMENT_DELIVERY_STATE.json':assert json.loads(body)['full_voices_published'] is True
 if name=='5_TIEU_DE_VA_THUMBNAIL.txt':assert len(body)>4000
print('PUBLIC_TEXT_DOWNLOADS_VERIFIED',flush=True)
record=dict(topic_id='MOI-027',stage='all16voices_documents_and_public_downloads_verified',target_seconds=1292,assets=[dict(name=x['name'],bytes=x['size'],sha256=x['digest'].removeprefix('sha256:')) for x in release['assets'] if x['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']])
p=R/'DOCUMENT_ASSET_MANIFEST.json';dump(p,record);subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
release=ghapi(f'releases/tags/{TAG}')
p=R/'SHA256SUMS.txt';p.write_text(''.join(x['digest'].removeprefix('sha256:')+'  '+x['name']+'\n' for x in sorted(release['assets'],key=lambda x:x['name']) if x['name']!='SHA256SUMS.txt'))
subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
release=ghapi(f'releases/tags/{TAG}');byname={x['name']:x for x in release['assets']}
for name in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']:
 with urllib.request.urlopen(urllib.request.Request(BASE+name,headers={'User-Agent':'Stonehenge-final-hash-check'}),timeout=60) as response:body=response.read()
 assert hashlib.sha256(body).hexdigest()==byname[name]['digest'].removeprefix('sha256:'),name
print('FINAL_PUBLIC_MANIFESTS_VERIFIED',flush=True)
audit=dict(status='passed',topic_id='MOI-027',checked_at_utc=qa['verified_at_utc'],assets=[dict(name=a['name'],bytes=a['size'],digest=a['digest'],url=a['browser_download_url']) for a in release['assets']])
dump(R/'GITHUB_ASSET_AUDIT.json',audit)
dest=Path('productions/video-moi027-stonehenge');dest.mkdir(parents=True,exist_ok=True)
shutil.copytree(D,dest,dirs_exist_ok=True)
for name in ['PUBLIC_DELIVERY_QA.json','GITHUB_ASSET_AUDIT.json','DOCUMENT_DELIVERY_STATE.json','LOCALIZATION_SOURCE_CHAPTERS.json','DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']:shutil.copyfile(R/name,dest/name)
(dest/'SCRIPTS').mkdir(exist_ok=True)
for locale in locked:shutil.copyfile(R/'voice/scripts'/f'{locale}.json',dest/'SCRIPTS'/f'{locale}.json')
shared=Path('research/channel-analysis-20261116');previous=json.loads((shared/'PRODUCTION_STATE.json').read_text());completed=list(previous.get('completed_topics',[]))
assert {'MOI-011','MOI-022'}<={x['topic_id'] for x in completed}
entry=dict(topic_id='MOI-027',title='Stonehenge: lần theo hành trình của những khối đá lớn',directory=str(dest),release_url=f'https://github.com/{REPO}/releases/tag/{TAG}',target_seconds=1292)
completed=[x for x in completed if x['topic_id']!='MOI-027']+[entry]
state=dict(topic_id='MOI-027',catalogue_id='new-100-topics-20261116',title=entry['title'],phase='completed_documents_and_16_voices_publicly_verified',completed_at_utc=qa['verified_at_utc'],target_seconds=1292,english_words=q['english_words'],english_cues=130,prompts=140,prompt_txt_files=14,prompts_per_txt=10,timeline_shots=137,backup_prompt_ids=[138,139,140],opening_shots=10,opening_seconds=30,visual_revision=q['visual_revision'],outdoor_scenes=140,laboratory_scenes=0,voice_count=16,male_voices=16,main_voice_locale='en-US',vietnamese_voice_id='vi-VN-NamMinhNeural',profile_set_id=profile['profile_set_id'],previous_voice_ids_retained=16,voice_changes=[],seconds_each=1292,decoded_frames_48000_each=FRAMES,translated_alignment='13 shared chapters: twelve 100-second chapters and final 92-second chapter; not word synchronization',independent_native_listening_review=False,branch='codex/stonehenge-moi027-production-20261117',canonical_branch='codex/beringia-video-01',release_tag=TAG,release_url=entry['release_url'],document_directory=str(dest),public_delivery_qa=str(dest/'PUBLIC_DELIVERY_QA.json'),voice_profile=str(shared/'VOICE_PROFILES_LOCKED.json'),workflow_runs=dict(documents_and_english=44096963783,localization=44098128161,country_voice_generation=44099494167,final_voice_delivery=RUN,verification_and_archive=int(os.environ['GITHUB_RUN_ID'])),source_backend='Pinned Melo-Viet-Studio 1.3.1 online backend / Microsoft Edge via edge-tts; not Windows UI or native multilingual Melo model',source_backend_commit='4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043',public_delivery_qa_status='passed',audio_zip_sha256=qa['audio_zip_sha256'],documents_zip_sha256=qa['documents_zip_sha256'],footage_generated=False,thumbnail_generated=False,video_edited=False,old_series_topics_and_state_unchanged=True,no_auto_start_next_topic=True,next_topic_id=None,completed_topics=completed)
dump(shared/'PRODUCTION_STATE.json',state);dump(dest/'PRODUCTION_STATE.json',state);shutil.copyfile(D/'VOICE_PROFILES_LOCKED.json',shared/'VOICE_PROFILES_LOCKED.json')
(dest/'CONTINUE_THIS_PROJECT.md').write_text('# Tiếp tục dự án\n\nĐã hoàn tất MỚI-027 Stonehenge 21:32. Đọc PRODUCTION_STATE.json, PUBLIC_DELIVERY_QA.json, VOICE_PROFILES_LOCKED.json và NGUON_KIEM_CHUNG.md. Giữ nguyên danh mục cũ và các tập MOI-011, MOI-022; không tự chạy chủ đề tiếp theo. Giữ Nam Minh cho Việt Nam và 16 ID giọng đã khóa. Tài liệu/prompt/voice tại release Stonehenge; chưa có footage, thumbnail hoặc MP4. Các bản dịch chưa được kiểm nghe bản ngữ độc lập.\n',encoding='utf-8')
subprocess.run(['git','config','user.name','seotro95'],check=True);subprocess.run(['git','config','user.email','212990612+seotro95@users.noreply.github.com'],check=True)
subprocess.run(['git','add',str(dest),str(shared/'PRODUCTION_STATE.json'),str(shared/'VOICE_PROFILES_LOCKED.json')],check=True)
changed=subprocess.check_output(['git','diff','--cached','--name-only']).decode().splitlines()
assert all(p.startswith(str(dest)+'/') or p in [str(shared/'PRODUCTION_STATE.json'),str(shared/'VOICE_PROFILES_LOCKED.json')] for p in changed)
subprocess.run(['git','commit','-m','Complete MOI-027 Stonehenge: outdoor prompts, 16 verified 21:32 voices and preserved series state'],check=True)
subprocess.run(['git','push','origin','HEAD:codex/stonehenge-moi027-production-20261117'],check=True)
print('STONEHENGE_PUBLIC_DELIVERY_AND_READABLE_ARCHIVE_PASSED',subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),flush=True)
