import datetime,hashlib,json,os,re,shutil,subprocess,tempfile,time,urllib.error,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent;C=json.loads((R/'EPISODE.json').read_text())
REPO='seotro95/seotro';TAG=C['release_tag'];PREFIX=C['prefix'];BASE=f'https://github.com/{REPO}/releases/download/{TAG}/'
TARGET=C['target_seconds'];FRAMES=C['frames'];RUN=int(os.environ['GITHUB_RUN_ID'])
FFMPEG=shutil.which('ffmpeg') or __import__('imageio_ffmpeg').get_ffmpeg_exe()
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def fetch(url,out):
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Richat-public-delivery-check'}),timeout=90) as response,out.open('wb') as f:shutil.copyfileobj(response,f)
   return
  except urllib.error.HTTPError as exc:
   if exc.code in (401,403,429):raise
   if attempt==2:raise
   time.sleep(3)
  except (TimeoutError,urllib.error.URLError):
   if attempt==2:raise
   time.sleep(3)
def ghapi(path):return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/'+path]))
def upload(p):subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
def public_text(name,assets):
 with urllib.request.urlopen(urllib.request.Request(BASE+name,headers={'User-Agent':'Richat-public-text-check'}),timeout=60) as response:body=response.read();assert response.status==200
 assert hashlib.sha256(body).hexdigest()==assets[name]['digest'].removeprefix('sha256:'),name
 return body
jobs=ghapi(f'actions/runs/{RUN}/jobs?per_page=100&filter=all')['jobs']
assert any(j['name']=='publish' and j['conclusion']=='success' for j in jobs),'Same-workflow publisher must have succeeded'
release=ghapi(f'releases/tags/{TAG}');assets={x['name']:x for x in release['assets']}
D=R/'verified-public-documents';D.mkdir(exist_ok=True);reports=[]
docname=f'{PREFIX}_TAI_LIEU_{C["duration_label"]}.zip'
audioname=f'{PREFIX}_16_VOICES_{C["duration_label"]}.zip'
promptname=f'{PREFIX}_PROMPT_{C["prompt_txt_files"]}_TXT.zip'
with tempfile.TemporaryDirectory(prefix='richat-public-') as td:
 tmp=Path(td);doc=tmp/'documents.zip';audio=tmp/'voices.zip';prompts=tmp/'prompts.zip'
 for name,dest in [(docname,doc),(audioname,audio),(promptname,prompts)]:
  fetch(BASE+name,dest);assert sha(dest)==assets[name]['digest'].removeprefix('sha256:'),(name,'public SHA mismatch')
  with zipfile.ZipFile(dest) as z:assert z.testzip() is None
  print('PUBLIC_ZIP_VERIFIED',name,dest.stat().st_size,flush=True)
 with zipfile.ZipFile(doc) as z:
  assert all(not Path(x.filename).is_absolute() and '..' not in Path(x.filename).parts for x in z.infolist())
  z.extractall(D)
 q=json.loads((D/'DOCUMENT_QA.json').read_text())
 assert q['status']=='passed' and q['voices_generated'] and q['target_seconds']==TARGET
 for key,cfg in [('english_cues','english_cues'),('unique_prompts','prompt_count'),('prompt_txt_files','prompt_txt_files'),('timeline_shots','timeline_shots')]:assert q[key]==C[cfg]
 assert q['outdoor_scenes']==C['prompt_count'] and q['laboratory_scenes']==0
 allshots=json.loads((D/'ALL_PROMPTS.json').read_text());assert len(allshots)==C['prompt_count']
 assert all(x['generation_seconds']==10 and x['prompt'].endswith('Video không có âm thanh, không có lời nói.') and 'No children' in x['prompt'] and 'No laboratory' in x['prompt'] for x in allshots)
 assert sum(x['use_seconds'] for x in allshots)==TARGET and sum(x['used'] for x in allshots)==C['timeline_shots']
 assert [x['id'] for x in allshots if not x['used']]==C['backup_ids']
 assert len({x['prompt'] for x in allshots})==C['prompt_count']
 assert [x['use_seconds'] for x in allshots[:C['opening_shots']]]==[10,4,4,4,4,4]
 promptfiles=sorted((D/'PROMPTS').glob('*.txt'));assert len(promptfiles)==C['prompt_txt_files']
 for i,p in enumerate(promptfiles):assert list(map(int,re.findall(r'^(\d{3})\. ',p.read_text(),flags=re.M)))==list(range(i*10+1,i*10+11))
 with zipfile.ZipFile(prompts) as z:
  assert len(z.namelist())==C['prompt_txt_files']
  for p in promptfiles:assert z.read(p.name)==p.read_bytes()
 ret=json.loads((D/'RETENTION_QA.json').read_text());assert ret['status']=='passed' and ret['first_shot_seconds']==10 and ret['promise_completed_seconds']<30 and ret['first_payoff_start_seconds']<120
 assert max(ret['rehook_gaps_seconds'])<=90 and min(ret['rehook_gaps_seconds'])>=60 and min(ret['caveat_start_gaps_seconds'])>=120
 assert ret['voice_cue_duration_values']==list(range(3,11)) and ret['all_english_numbers_spelled_out']
 source=json.loads((D/'SOURCE_ASSET_MANIFEST.json').read_text());assert sha(D/'REFERENCE_ASSETS'/source['filename'])==source['sha256']
 assert hashlib.sha256(public_text(source['filename'],assets)).hexdigest()==source['sha256']
 manifest=json.loads((D/'AUDIO_MANIFEST.json').read_text());profile=json.loads((D/'VOICE_PROFILES_LOCKED.json').read_text());baseline=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
 locked={p['locale']:p['voice_id'] for p in baseline['profiles']}
 assert len(manifest['voices'])==16 and all(p['gender']=='Male' for p in profile['profiles'])
 assert {p['locale']:p['voice_id'] for p in profile['profiles']}==locked
 with zipfile.ZipFile(audio) as z:
  assert len([x for x in z.namelist() if x.endswith('.mp3')])==16
  for v in manifest['voices']:
   assert v['voice_id']==locked[v['locale']] and v['seconds']==TARGET and v['frames_at_48000']==FRAMES
   content=z.read(v['filename']);assert hashlib.sha256(content).hexdigest()==v['sha256']==assets[v['filename']]['digest'].removeprefix('sha256:')
   out=tmp/'one.mp3';out.write_bytes(content)
   proc=subprocess.Popen([FFMPEG,'-v','error','-nostdin','-i',str(out),'-ar','48000','-ac','1','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);count=0
   while block:=proc.stdout.read(1024*1024):count+=len(block)
   error=proc.stderr.read().decode('utf-8','replace');assert proc.wait()==0,error;assert count==FRAMES*2,(v['locale'],count)
   with urllib.request.urlopen(urllib.request.Request(v['url'],method='HEAD',headers={'User-Agent':'Richat-public-delivery-check'}),timeout=60) as response:assert response.status==200
   report=json.loads((D/'REPORTS'/f"{v['locale']}.json").read_text());script=R/'voice/scripts'/f"{v['locale']}.json"
   assert report['script_sha256']==sha(script)
   reports.append(dict(locale=v['locale'],filename=v['filename'],voice_id=v['voice_id'],decoded_frames_48000=FRAMES,seconds=TARGET,sha256=v['sha256'],public_url_status=200))
   print('PUBLIC_MP3_FULL_DECODE_PASSED',v['locale'],FRAMES,flush=True)
 qa=dict(status='passed',topic_id=C['topic_id'],verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target_seconds=TARGET,voices=16,all_decoded_frames_48000=FRAMES,all_16_ids_retained=True,public_mp3_urls_checked=16,zip_crc_and_public_github_sha_verified=True,english_script_words=q['english_words'],prompt_txt_files=C['prompt_txt_files'],unique_prompts=C['prompt_count'],timeline_shots=C['timeline_shots'],outdoor_scenes=C['prompt_count'],laboratory_scenes=0,backup_prompt_ids=C['backup_ids'],retention_qa_status='passed',source_image_sha256=source['sha256'],audio_zip_sha256=sha(audio),documents_zip_sha256=sha(doc),prompts_zip_sha256=sha(prompts),independent_native_listening_review=False,footage_generated=False,thumbnail_generated=False,video_edited=False,reports=reports)
 dump(R/'PUBLIC_DELIVERY_QA.json',qa)
dump(R/'DOCUMENT_DELIVERY_STATE.json',dict(documents_published=True,target_seconds=TARGET,full_voices_published=True,public_delivery_verified=True,voices=16))
for name in ['PUBLIC_DELIVERY_QA.json','DOCUMENT_DELIVERY_STATE.json']:upload(R/name)
release=ghapi(f'releases/tags/{TAG}');byname={x['name']:x for x in release['assets']}
for name in ['PUBLIC_DELIVERY_QA.json','DOCUMENT_DELIVERY_STATE.json',f'KICH_BAN_EN_{C["duration_label"]}.txt','5_TIEU_DE_VA_THUMBNAIL.txt','LINK_TAI_VOICE.txt']:
 body=public_text(name,byname)
 if name=='DOCUMENT_DELIVERY_STATE.json':assert json.loads(body)['full_voices_published'] is True
 if name=='5_TIEU_DE_VA_THUMBNAIL.txt':assert len(body)>4000
print('PUBLIC_TEXT_DOWNLOADS_VERIFIED',flush=True)
record=dict(topic_id=C['topic_id'],stage='all16voices_documents_and_public_downloads_verified',target_seconds=TARGET,assets=[dict(name=x['name'],bytes=x['size'],sha256=x['digest'].removeprefix('sha256:')) for x in release['assets'] if x['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']])
dump(R/'DOCUMENT_ASSET_MANIFEST.json',record);upload(R/'DOCUMENT_ASSET_MANIFEST.json')
release=ghapi(f'releases/tags/{TAG}');p=R/'SHA256SUMS.txt';p.write_text(''.join(x['digest'].removeprefix('sha256:')+'  '+x['name']+'\n' for x in sorted(release['assets'],key=lambda x:x['name']) if x['name']!='SHA256SUMS.txt'));upload(p)
release=ghapi(f'releases/tags/{TAG}');byname={x['name']:x for x in release['assets']}
for name in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']:public_text(name,byname)
print('FINAL_PUBLIC_MANIFESTS_VERIFIED',flush=True)
dump(R/'GITHUB_ASSET_AUDIT.json',dict(status='passed',topic_id=C['topic_id'],checked_at_utc=qa['verified_at_utc'],assets=[dict(name=a['name'],bytes=a['size'],digest=a['digest'],url=a['browser_download_url']) for a in release['assets']]))
dest=Path(C['directory']);dest.mkdir(parents=True,exist_ok=True);shutil.copytree(D,dest,dirs_exist_ok=True)
for name in ['PUBLIC_DELIVERY_QA.json','GITHUB_ASSET_AUDIT.json','DOCUMENT_DELIVERY_STATE.json','DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt','LOCALIZATION_ADAPTATION_EN.txt','VI_NARRATION.txt','LOCALIZATION_SOURCE_CHAPTERS.json','LOCALIZATION_PATCHES.json','LOCALIZATION_OVERRIDES.json','VI_EXPANSION_REVIEW.json']:shutil.copyfile(R/name,dest/name)
(dest/'SCRIPTS').mkdir(exist_ok=True)
for locale in locked:shutil.copyfile(R/'voice/scripts'/f'{locale}.json',dest/'SCRIPTS'/f'{locale}.json')
shared=Path('research/channel-analysis-20261116');previous=json.loads((shared/'PRODUCTION_STATE.json').read_text());completed=list(previous.get('completed_topics',[]))
assert {'MOI-011','MOI-022','MOI-027','MOI-030','MOI-048','MOI-053'}<={x['topic_id'] for x in completed}
prior_profiles=json.loads((shared/'VOICE_PROFILES_LOCKED.json').read_text());assert {p['locale']:p['voice_id'] for p in prior_profiles['profiles']}==locked
entry=dict(topic_id=C['topic_id'],title=C['title'],directory=str(dest),release_url=f'https://github.com/{REPO}/releases/tag/{TAG}',target_seconds=TARGET)
completed=[x for x in completed if x['topic_id']!=C['topic_id']]+[entry]
state=dict(topic_id=C['topic_id'],catalogue_id='new-100-topics-20261116',title=C['title'],phase='completed_documents_and_16_voices_publicly_verified',completed_at_utc=qa['verified_at_utc'],target_seconds=TARGET,english_words=q['english_words'],english_wpm=q['english_wpm'],narration_style_id=C['style_id'],english_cues=C['english_cues'],prompts=C['prompt_count'],prompt_txt_files=C['prompt_txt_files'],prompts_per_txt=10,timeline_shots=C['timeline_shots'],backup_prompt_ids=C['backup_ids'],opening_shots=C['opening_shots'],opening_seconds=30,first_shot_seconds=C['first_shot_seconds'],visual_revision=q['visual_revision'],outdoor_scenes=C['prompt_count'],laboratory_scenes=0,voice_count=16,male_voices=16,main_voice_locale='en-US',vietnamese_voice_id='vi-VN-NamMinhNeural',profile_set_id=profile['profile_set_id'],previous_voice_ids_retained=16,voice_changes=[],seconds_each=TARGET,decoded_frames_48000_each=FRAMES,translated_alignment='Ten shared sections: nine at 130 seconds and final 132 seconds; localized retellings, not word synchronization',independent_native_editorial_review=False,independent_native_listening_review=False,branch=C['branch'],canonical_branch=C['canonical_branch'],release_tag=TAG,release_url=entry['release_url'],document_directory=str(dest),public_delivery_qa=str(dest/'PUBLIC_DELIVERY_QA.json'),voice_profile=str(shared/'VOICE_PROFILES_LOCKED.json'),workflow_runs=dict(documents_and_english=44819270070,country_voice_generation=44854560788,final_voice_delivery_and_archive=RUN),source_backend='Pinned Melo-Viet-Studio 1.3.1 online backend / Microsoft Edge via edge-tts; not Windows UI or native multilingual Melo model',source_backend_commit='4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043',public_delivery_qa_status='passed',audio_zip_sha256=qa['audio_zip_sha256'],documents_zip_sha256=qa['documents_zip_sha256'],footage_generated=False,thumbnail_generated=False,video_edited=False,old_series_topics_and_state_unchanged=True,no_auto_start_next_topic=True,next_topic_id=None,completed_topics=completed)
dump(shared/'PRODUCTION_STATE.json',state);dump(dest/'PRODUCTION_STATE.json',state);shutil.copyfile(D/'VOICE_PROFILES_LOCKED.json',shared/'VOICE_PROFILES_LOCKED.json')
(dest/'CONTINUE_THIS_PROJECT.md').write_text('''# Tiếp tục dự án

Đã hoàn tất MỚI-061 Richat, 21:42: kịch bản Anh 3930 từ/200 block lời 3–10 giây; 140 prompt/14 TXT; timeline 134 cảnh, 6 dự phòng; 16 MP3 nam kiểm giải mã và tải công khai. Đọc PRODUCTION_STATE.json, PUBLIC_DELIVERY_QA.json, VOICE_PROFILES_LOCKED.json, TRANSLATION_REVIEW.json, RETENTION_RULES_LOCKED.json và NGUON_KIEM_CHUNG.md. Giữ các tập trước và danh mục cũ; không tự chạy tập tiếp theo. Giữ 16 ID, gồm Andrew/Nam Minh. Bản nước ngoài chuyển thể 10 phần, chưa kiểm nghe/biên tập bản ngữ độc lập. Chưa tạo footage/thumbnail/MP4. Giữ rõ tuổi gabro phụ thuộc mô hình và hình học ngầm chưa xác định hoàn toàn. Không coi hình tròn là chứng cứ thành phố hoặc va chạm. Ưu tiên cảnh ngoài trời, không trẻ em, không lab; hình vệ tinh bám JPEG NASA/USGS kèm credit, không giả dữ liệu. Hook mới giữ MỘT lớp đá trong 10 giây đầu, rồi 5 cảnh × 4 giây; không quay lại công thức 10 cảnh trong 30 giây của tập cũ. Prompt nào cũng kết bằng câu không âm thanh, không lời nói.
''',encoding='utf-8')
subprocess.run(['git','config','user.name','seotro95'],check=True);subprocess.run(['git','config','user.email','212990612+seotro95@users.noreply.github.com'],check=True)
subprocess.run(['git','add',str(dest),str(shared/'PRODUCTION_STATE.json'),str(shared/'VOICE_PROFILES_LOCKED.json')],check=True)
changed=subprocess.check_output(['git','diff','--cached','--name-only']).decode().splitlines()
assert all(p.startswith(str(dest)+'/') or p in [str(shared/'PRODUCTION_STATE.json'),str(shared/'VOICE_PROFILES_LOCKED.json')] for p in changed)
subprocess.run(['git','commit','-m',f'Complete {C["topic_id"]} Richat: 140 outdoor prompts and 16 verified 21:42 voices; preserve earlier episodes'],check=True)
subprocess.run(['git','push','origin','HEAD:'+C['branch']],check=True)
print('RICHAT_PUBLIC_DELIVERY_AND_READABLE_ARCHIVE_PASSED',subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),flush=True)
