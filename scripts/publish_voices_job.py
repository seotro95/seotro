import hashlib,json,os,re,shutil,subprocess,time,urllib.error,urllib.request,zipfile
from pathlib import Path
REPO=os.environ['GITHUB_REPOSITORY'];BRANCH='codex/baishiya-voice-build-20261110';TAG='baishiya-video-08-22m20s';O=Path('delivery');O.mkdir(exist_ok=True)
doc=json.load(open('input/DOCUMENT_DELIVERY_STATE.json'));DOCS=doc['production_head'];assert doc['target_seconds']==1340
profiles=json.load(open('input/BASELINE_VOICE_PROFILES.json'));expected={x['locale']:x for x in profiles['profiles']};names={x['locale']:x for x in json.load(open('input/VOICE_FILE_NAMING.json'))['voices']}
reports={}
for p in Path('artifacts').rglob('render_report.json'):
 j=json.loads(p.read_text());locale=j['locale'];assert locale not in reports
 assert j['audio_seconds']==1340 and j['duration_verified'] and j['mp3_decoded_duration']['verified']
 assert j['mp3_decoded_duration']['sample_frames']==64320000 and j['voice_id']==expected[locale]['voice_id'] and j['gender']=='Male'
 assert j['narration_style_id']=='science-documentary-expressive-v1' and j['voice_identity_preserved'] and not j['pitch_shift_applied']
 audio=p.parent/j['mp3_file'];assert hashlib.sha256(audio.read_bytes()).hexdigest()==j['mp3_sha256'];reports[locale]={'report':j,'audio':audio,'srt':p.parent/'subtitles.srt'}
assert len(reports)==16,list(reports)
native=None
for attempt in range(120):
 sha=subprocess.check_output(['gh','api',f'repos/{REPO}/git/ref/heads/{BRANCH}','--jq','.object.sha'],text=True).strip();assert re.fullmatch('[a-f0-9]{40}',sha)
 base=f'https://raw.githubusercontent.com/{REPO}/{sha}/native-baishiya08/'
 try:native=json.load(urllib.request.urlopen(base+'manifest.json',timeout=45));break
 except urllib.error.HTTPError as e:
  if e.code!=404:raise
  print('Waiting for verified native Hmong',attempt+1,flush=True);time.sleep(30)
assert native,'Retain all completed online artifacts; native Hmong not ready.'
assert native['voice_id']=='hmong-female-3' and native['reference_sha256']==expected['mww']['reference_sha256'] and native['seconds']==1340
N=Path('native-download');N.mkdir(exist_ok=True)
for name in ['BAISHIYA_08_mww_female.mp3','render_report.json','subtitles.srt']:
 with urllib.request.urlopen(base+name,timeout=60) as r:(N/name).write_bytes(r.read())
h=json.load(open(N/'render_report.json'));audio=N/h['mp3_file'];assert hashlib.sha256(audio.read_bytes()).hexdigest()==h['mp3_sha256']==native['mp3_sha256']
assert h['audio_seconds']==1340 and h['mp3_decoded_duration']['verified'] and h['mp3_decoded_duration']['sample_frames']==64320000 and h['gender']=='Female'
assert h['narration_style_id']=='science-documentary-expressive-v1';reports['mww']={'report':h,'audio':audio,'srt':N/'subtitles.srt'}
for name in ['SCRIPTS','TIMING','REPORTS']:(O/name).mkdir(exist_ok=True)
manifest=[];locked=[]
for locale,p in expected.items():
 rec=reports[locale];r=rec['report'];n=names[locale];filename='BAISHIYA_08_'+n['delivery_slug']+'.mp3';dst=O/filename;shutil.copy(rec['audio'],dst)
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==r['mp3_sha256']
 shutil.copy(rec['srt'],O/'TIMING'/f'{locale}.srt')
 rows=json.load(open(f'input/scripts/{locale}.json'));(O/'SCRIPTS'/f'{locale}.txt').write_text('\n\n'.join(x['voice'] for x in rows))
 if locale=='en-US':
  raw=(O/'TIMING/en-US.srt').read_text();assert raw.count(' --> ')==134 and '00:22:20,000' in raw
  text=' '.join(' '.join(b.splitlines()[2:]) for b in re.split(r'\n\s*\n',raw.strip()));assert text==' '.join(x['voice'] for x in rows)
  assert len(text.split())==3162
 r['source_filename']=r['mp3_file'];r['mp3_file']=filename;r['delivery_country_vi']=n['country_vi'];r['delivery_display_name']=n['display_name'];(O/'REPORTS'/f'{locale}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
 profile={k:v for k,v in p.items() if k not in ['duration_seconds','max_used_post_tempo','mp3_reference_sha256','translation_review_status','alignment_granularity']};profile.update(narration_style_id='science-documentary-expressive-v1',base_rate=p['rate'],rate='phrase-dependent; see narration style and reports',duration_seconds=1340,mp3_sha256=r['mp3_sha256'],alignment_granularity=r['alignment_granularity'],translation_review_status=r['translation_review_status'],delivery_filename=filename);locked.append(profile)
 manifest.append({'locale':locale,'name':n['display_name'],'country_vi':n['country_vi'],'language_vi':n['language_vi'],'gender':p['gender'],'voice_id':p['voice_id'],'filename':filename,'bytes':dst.stat().st_size,'sha256':r['mp3_sha256'],'seconds':1340})
assert len(manifest)==17 and len({m['sha256'] for m in manifest})==17 and sum(m['gender']=='Male' for m in manifest)==16
(O/'AUDIO_MANIFEST.json').write_text(json.dumps({'topic':8,'seconds_per_voice':1340,'sample_frames_at_48000':64320000,'voice_count':17,'voices':manifest,'native_review_pending':True,'no_children_in_video_prompts':True},ensure_ascii=False,indent=2))
(O/'VOICE_PROFILES_LOCKED.json').write_text(json.dumps({'profile_set_id':profiles['profile_set_id'],'topic_id':8,'target_seconds':1340,'profiles':locked,'note':'Original17 voice IDs and female-3 native reference retained. Timing recalculated for22m20s. Backend provider models may evolve; native language/listening review remains pending.'},ensure_ascii=False,indent=2))
for name in ['NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copy('input/'+name,O/name)
baseurl=f'https://github.com/{REPO}/releases/download/{TAG}/'
readme='# Baishiya — chủ đề8,17voice riêng, mỗi bản22:20\n\nVideo chính chỉ dùng voice tiếng Anh. Giữ16giọng nam và H’Mông nữ3, đúngengine/mẫu tham chiếu đã khóa. Tất cả dùng science-documentary-expressive-v1.\n\n| Quốc gia/ngôn ngữ | Giọng | Tải MP3 |\n|---|---|---|\n'
for m in manifest:readme+=f'| {m["name"]} | {m["voice_id"]} | [Tải MP3]({baseurl}{m["filename"]}) |\n'
readme+=f'\n[ZIP đủ17voice theo tên quốc gia]({baseurl}BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip) · [Kịch bản/prompt22phút20giây]({baseurl}BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip)\n\n'
readme+='Mỗi MP3 đã giải mã đúng64.320.000mẫu tại48kHz=1340giây. Anh căn134ô10s; bản dịch căn12chương theo ranh thật: hai chương120s và mười chương110s. Không phải căn từng từ giữa mọi ngôn ngữ. Giữ cao độ/bản sắc giọng; tốc độ hậu kỳ được tính lại cho tập này, không dùng tốc độ cũ như hằng số.\n\n'
readme+='Bộ hình có120prompt mới trong12TXT và14ôREUSE. Không có trẻ em trong bất kỳ prompt nào, kể cả nền, bóng, ảnh, phản chiếu và màn hình; chỉ người trưởng thành rõ25–60tuổi. Chưa dựng video tập8 vì chưa có clip của tập này.\n\n'
readme+='Bản dịch đã điều chỉnh thuật ngữ và cách dùng theo locale, nhưng vẫn cần người bản ngữ đọc/nghe rà soát. Phương ngữ H’Mông Trắng chưa được xác nhận độc lập. Kiểm tra file phát được/đủ phút không thay cho kiểm định ngôn ngữ. Hồ sơ trong REPORTS lưu engine, ID, thời lượng, tốc độ và nhấn nhá.\n'
(O/'README.md').write_text(readme)
with zipfile.ZipFile(O/'BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip','w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.rglob('*')):
  if p.is_file() and p.suffix!='.zip':z.write(p,p.relative_to(O))
with zipfile.ZipFile(O/'BAISHIYA_08_HO_SO_GIONG_TEN_QUOC_GIA.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(O.rglob('*')):
  if p.is_file() and p.suffix not in ['.mp3','.zip']:z.write(p,p.relative_to(O))
u=f'https://raw.githubusercontent.com/{REPO}/{DOCS}/productions/video-08-baishiya/BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip'
with urllib.request.urlopen(u,timeout=60) as f:data=f.read()
assert hashlib.sha256(data).hexdigest()==doc['zip_sha256'];(O/'BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip').write_bytes(data)
(O/'RELEASE_NOTES.md').write_text(readme)
check=subprocess.run(['gh','release','view',TAG,'--repo',REPO],capture_output=True)
if check.returncode:subprocess.run(['gh','release','create',TAG,'--repo',REPO,'--target',DOCS,'--title','Baishiya Video08 —17 locked expressive voices,22m20s','--draft','--notes-file',str(O/'RELEASE_NOTES.md')],check=True)
for m in manifest:subprocess.run(['gh','release','upload',TAG,str(O/m['filename']),'--repo',REPO,'--clobber'],check=True)
for name in ['BAISHIYA_08_17_VOICES_TEN_QUOC_GIA.zip','BAISHIYA_08_HO_SO_GIONG_TEN_QUOC_GIA.zip','VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json','AUDIO_MANIFEST.json','README.md','BAISHIYA_VIDEO_08_TAI_LIEU_22m20s.zip']:
 subprocess.run(['gh','release','upload',TAG,str(O/name),'--repo',REPO,'--clobber'],check=True)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--draft=false','--latest=false'],check=True)
print('All17 verified Baishiya voices published',flush=True)
