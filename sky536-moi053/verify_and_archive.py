import csv,datetime,hashlib,io,json,os,shutil,subprocess,tempfile,time,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent;TAG='sky536-moi-053-22m12s';REPO='seotro95/seotro';BASE=f'https://github.com/{REPO}/releases/download/{TAG}/';FRAMES=63936000;RUN=int(os.environ['GITHUB_RUN_ID'])
FFMPEG=shutil.which('ffmpeg') or __import__('imageio_ffmpeg').get_ffmpeg_exe()
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def fetch(url,out):
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Sky 536-public-delivery-check'}),timeout=90) as response,out.open('wb') as f:shutil.copyfileobj(response,f)
   return
  except Exception:
   if attempt==2:raise
   time.sleep(3)
def ghapi(path):return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/'+path]))
jobs=ghapi(f'actions/runs/{RUN}/jobs?per_page=100&filter=all')['jobs']
assert any(j['name']=='publish' and j['conclusion']=='success' for j in jobs),'Same-workflow publisher must have succeeded before verification'
release=ghapi(f'releases/tags/{TAG}');assets={x['name']:x for x in release['assets']}
D=R/'verified-public-documents';D.mkdir(exist_ok=True)
reports=[]
with tempfile.TemporaryDirectory(prefix='maryrose-public-') as td:
 tmp=Path(td);doc=tmp/'documents.zip';audio=tmp/'voices.zip';prompts=tmp/'prompts.zip'
 for name,dest in [('SKY536_MOI053_TAI_LIEU_22m12s.zip',doc),('SKY536_MOI053_16_VOICES_22m12s.zip',audio),('SKY536_MOI053_PROMPT_15_TXT.zip',prompts)]:
  fetch(BASE+name,dest);assert sha(dest)==assets[name]['digest'].removeprefix('sha256:'),(name,'public SHA mismatch')
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None
  print('PUBLIC_ZIP_VERIFIED',name,dest.stat().st_size,flush=True)
 with zipfile.ZipFile(doc) as z:
  for item in z.infolist():
   assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
  z.extractall(D)
 q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['voices_generated'] and q['target_seconds']==1332 and q['english_cues']==134
 assert q['unique_prompts']==150 and q['prompt_txt_files']==15 and q['timeline_shots']==141 and q['outdoor_scenes']==150 and q['laboratory_scenes']==0
 allshots=json.loads((D/'ALL_PROMPTS.json').read_text());assert len(allshots)==150
 assert all(x['generation_seconds']==10 and x['prompt'].endswith('Video không có âm thanh, không có lời nói.') and 'No children' in x['prompt'] and 'Prioritize outdoor historical landscapes' in x['prompt'] for x in allshots)
 assert sum(x['use_seconds'] for x in allshots)==1332 and sum(x['used'] for x in allshots)==141
 assert [x['id'] for x in allshots if not x['used']]==list(range(142,151))
 assert len({x['prompt'] for x in allshots})==150
 promptfiles=sorted((D/'PROMPTS').glob('*.txt'));assert len(promptfiles)==15
 for i,p in enumerate(promptfiles):
  ids=__import__('re').findall(r'^(\d{3})\. ',p.read_text(),flags=__import__('re').M)
  assert list(map(int,ids))==list(range(i*10+1,i*10+11))
 with zipfile.ZipFile(prompts) as z:
  assert len(z.namelist())==15
  for p in promptfiles:assert z.read(p.name)==p.read_bytes()
 manifest=json.loads((D/'AUDIO_MANIFEST.json').read_text());profile=json.loads((D/'VOICE_PROFILES_LOCKED.json').read_text());baseline=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
 locked={p['locale']:p['voice_id'] for p in baseline['profiles']}
 assert len(manifest['voices'])==16 and all(p['gender']=='Male' for p in profile['profiles'])
 assert {p['locale']:p['voice_id'] for p in profile['profiles']}==locked
 with zipfile.ZipFile(audio) as z:
  assert len([x for x in z.namelist() if x.endswith('.mp3')])==16
  for v in manifest['voices']:
   assert v['voice_id']==locked[v['locale']] and v['seconds']==1332 and v['frames_at_48000']==FRAMES
   content=z.read(v['filename']);assert hashlib.sha256(content).hexdigest()==v['sha256']==assets[v['filename']]['digest'].removeprefix('sha256:')
   out=tmp/'one.mp3';out.write_bytes(content)
   proc=subprocess.Popen([FFMPEG,'-v','error','-nostdin','-i',str(out),'-ar','48000','-ac','1','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);count=0
   while block:=proc.stdout.read(1024*1024):count+=len(block)
   error=proc.stderr.read().decode('utf-8','replace');assert proc.wait()==0,error;assert count==FRAMES*2,(v['locale'],count)
   with urllib.request.urlopen(urllib.request.Request(v['url'],method='HEAD',headers={'User-Agent':'Sky 536-public-delivery-check'}),timeout=60) as response:assert response.status==200
   report=json.loads((D/'REPORTS'/f"{v['locale']}.json").read_text())
   source=R/'voice/scripts'/f"{v['locale']}.json"
   assert report['script_sha256']==sha(source)
   reports.append(dict(locale=v['locale'],filename=v['filename'],voice_id=v['voice_id'],decoded_frames_48000=FRAMES,seconds=1332,sha256=v['sha256'],public_url_status=200))
   print('PUBLIC_MP3_FULL_DECODE_PASSED',v['locale'],FRAMES,flush=True)
 qa=dict(status='passed',topic_id='MOI-053',verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target_seconds=1332,voices=16,all_decoded_frames_48000=FRAMES,all_16_ids_retained=True,public_mp3_urls_checked=16,zip_crc_and_public_github_sha_verified=True,english_script_words=q['english_words'],prompt_txt_files=15,unique_prompts=150,timeline_shots=141,outdoor_scenes=150,underwater_scenes=0,historical_interior_scenes=0,laboratory_scenes=0,backup_prompt_ids=list(range(142,151)),audio_zip_sha256=sha(audio),documents_zip_sha256=sha(doc),prompts_zip_sha256=sha(prompts),independent_native_listening_review=False,footage_generated=False,thumbnail_generated=False,video_edited=False,reports=reports)
 dump(R/'PUBLIC_DELIVERY_QA.json',qa)
# Final delivery-state asset and readable archive, without changing audio or the verified ZIPs.
state_asset=dict(documents_published=True,target_seconds=1332,full_voices_published=True,public_delivery_verified=True,voices=16)
dump(R/'DOCUMENT_DELIVERY_STATE.json',state_asset)
for p in [R/'PUBLIC_DELIVERY_QA.json',R/'DOCUMENT_DELIVERY_STATE.json']:subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
release=ghapi(f'releases/tags/{TAG}');byname={x['name']:x for x in release['assets']}
for name in ['PUBLIC_DELIVERY_QA.json','DOCUMENT_DELIVERY_STATE.json','KICH_BAN_EN_22m12s.txt','5_TIEU_DE_VA_THUMBNAIL.txt']:
 with urllib.request.urlopen(urllib.request.Request(BASE+name,headers={'User-Agent':'Sky 536-final-text-check'}),timeout=60) as response:body=response.read();assert response.status==200
 assert hashlib.sha256(body).hexdigest()==byname[name]['digest'].removeprefix('sha256:'),name
 if name=='DOCUMENT_DELIVERY_STATE.json':assert json.loads(body)['full_voices_published'] is True
 if name=='5_TIEU_DE_VA_THUMBNAIL.txt':assert len(body)>4000
print('PUBLIC_TEXT_DOWNLOADS_VERIFIED',flush=True)
record=dict(topic_id='MOI-053',stage='all16voices_documents_and_public_downloads_verified',target_seconds=1332,assets=[dict(name=x['name'],bytes=x['size'],sha256=x['digest'].removeprefix('sha256:')) for x in release['assets'] if x['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']])
p=R/'DOCUMENT_ASSET_MANIFEST.json';dump(p,record);subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
release=ghapi(f'releases/tags/{TAG}')
p=R/'SHA256SUMS.txt';p.write_text(''.join(x['digest'].removeprefix('sha256:')+'  '+x['name']+'\n' for x in sorted(release['assets'],key=lambda x:x['name']) if x['name']!='SHA256SUMS.txt'))
subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
release=ghapi(f'releases/tags/{TAG}');byname={x['name']:x for x in release['assets']}
for name in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']:
 with urllib.request.urlopen(urllib.request.Request(BASE+name,headers={'User-Agent':'Sky 536-final-hash-check'}),timeout=60) as response:body=response.read()
 assert hashlib.sha256(body).hexdigest()==byname[name]['digest'].removeprefix('sha256:'),name
print('FINAL_PUBLIC_MANIFESTS_VERIFIED',flush=True)
audit=dict(status='passed',topic_id='MOI-053',checked_at_utc=qa['verified_at_utc'],assets=[dict(name=a['name'],bytes=a['size'],digest=a['digest'],url=a['browser_download_url']) for a in release['assets']])
dump(R/'GITHUB_ASSET_AUDIT.json',audit)
dest=Path('productions/video-moi053-sky536');dest.mkdir(parents=True,exist_ok=True)
shutil.copytree(D,dest,dirs_exist_ok=True)
for name in ['PUBLIC_DELIVERY_QA.json','GITHUB_ASSET_AUDIT.json','DOCUMENT_DELIVERY_STATE.json','LOCALIZATION_SOURCE_CHAPTERS.json','DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']:shutil.copyfile(R/name,dest/name)
for name in ['NARRATION_REVISIONS.json','LOCALIZATION_ADAPTATION_EN.txt','VI_NARRATION.txt']:
 if (R/name).exists():shutil.copyfile(R/name,dest/name)
(dest/'SCRIPTS').mkdir(exist_ok=True)
for locale in locked:shutil.copyfile(R/'voice/scripts'/f'{locale}.json',dest/'SCRIPTS'/f'{locale}.json')
shared=Path('research/channel-analysis-20261116');previous=json.loads((shared/'PRODUCTION_STATE.json').read_text());completed=list(previous.get('completed_topics',[]))
assert {'MOI-011','MOI-022','MOI-027','MOI-030','MOI-048'}<={x['topic_id'] for x in completed}
entry=dict(topic_id='MOI-053',title='Năm 536: lần theo dấu vết một bầu trời mờ tối',directory=str(dest),release_url=f'https://github.com/{REPO}/releases/tag/{TAG}',target_seconds=1332)
completed=[x for x in completed if x['topic_id']!='MOI-053']+[entry]
state=dict(topic_id='MOI-053',catalogue_id='new-100-topics-20261116',title=entry['title'],phase='completed_documents_and_16_voices_publicly_verified',completed_at_utc=qa['verified_at_utc'],target_seconds=1332,english_words=q['english_words'],english_wpm=q['english_wpm'],narration_style_id='science-documentary-brisk-v4-Sky536-NamMinh',english_cues=134,prompts=150,prompt_txt_files=15,prompts_per_txt=10,timeline_shots=141,backup_prompt_ids=list(range(142,151)),opening_shots=10,opening_seconds=30,visual_revision=q['visual_revision'],outdoor_scenes=150,underwater_scenes=0,historical_interior_scenes=0,laboratory_scenes=0,voice_count=16,male_voices=16,main_voice_locale='en-US',vietnamese_voice_id='vi-VN-NamMinhNeural',profile_set_id=profile['profile_set_id'],previous_voice_ids_retained=16,voice_changes=[],seconds_each=1332,decoded_frames_48000_each=FRAMES,english_regenerated_cue_ids=[134],english_original_cues_retained=133,english_final_cue_native_rate='-12%',translated_alignment='Thirteen shared chapters: twelve 100-second chapters and final 132-second chapter; localized retellings, not word synchronization',independent_native_listening_review=False,branch='codex/sky536-moi053-production-20261120',canonical_branch='codex/beringia-video-01',release_tag=TAG,release_url=entry['release_url'],document_directory=str(dest),public_delivery_qa=str(dest/'PUBLIC_DELIVERY_QA.json'),voice_profile=str(shared/'VOICE_PROFILES_LOCKED.json'),workflow_runs=dict(documents_only_original_run=44761841149,english_ending_recovery=44810226775,country_voice_generation=44763939449,final_voice_delivery_and_archive=RUN),source_backend='Pinned Melo-Viet-Studio 1.3.1 online backend / Microsoft Edge via edge-tts; not Windows UI or native multilingual Melo model',source_backend_commit='4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043',public_delivery_qa_status='passed',audio_zip_sha256=qa['audio_zip_sha256'],documents_zip_sha256=qa['documents_zip_sha256'],footage_generated=False,thumbnail_generated=False,video_edited=False,old_series_topics_and_state_unchanged=True,no_auto_start_next_topic=True,next_topic_id=None,completed_topics=completed)
dump(shared/'PRODUCTION_STATE.json',state);dump(dest/'PRODUCTION_STATE.json',state);shutil.copyfile(D/'VOICE_PROFILES_LOCKED.json',shared/'VOICE_PROFILES_LOCKED.json')
(dest/'CONTINUE_THIS_PROJECT.md').write_text('# Tiếp tục dự án\n\nĐã hoàn tất MỚI-053 năm536, 22:12: kịch bản3984từ, 150prompt/15TXT, timeline141cảnh và9dự phòng, 16MP3nam đã kiểm tải công khai. Đọc PRODUCTION_STATE.json, PUBLIC_DELIVERY_QA.json, VOICE_PROFILES_LOCKED.json, TRANSLATION_REVIEW.json và NGUON_KIEM_CHUNG.md. Giữ các tập011,022,027,030,048 và danh mục cũ; không tự chạy tập kế tiếp. Giữ16ID, gồm Andrew/NamMinh. Bản nước ngoài chuyển thể13chương, chưa kiểm nghe bản ngữ độc lập. Hình AI chỉ minh họa, chưa tạo footage/thumbnail/MP4. Không gộp536và540 hoặc quy mọi khủng hoảng thế kỷVI cho một vụ phun trào.\n')
subprocess.run(['git','config','user.name','seotro95'],check=True);subprocess.run(['git','config','user.email','212990612+seotro95@users.noreply.github.com'],check=True)
subprocess.run(['git','add',str(dest),str(shared/'PRODUCTION_STATE.json'),str(shared/'VOICE_PROFILES_LOCKED.json')],check=True)
changed=subprocess.check_output(['git','diff','--cached','--name-only']).decode().splitlines()
assert all(p.startswith(str(dest)+'/') or p in [str(shared/'PRODUCTION_STATE.json'),str(shared/'VOICE_PROFILES_LOCKED.json')] for p in changed)
subprocess.run(['git','commit','-m','Complete MOI-053 Sky 536: 150 outdoor prompts, 16 verified 22:12 voices and preserved series state'],check=True)
subprocess.run(['git','push','origin','HEAD:codex/sky536-moi053-production-20261120'],check=True)
print('SKY536_PUBLIC_DELIVERY_AND_READABLE_ARCHIVE_PASSED',subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),flush=True)
