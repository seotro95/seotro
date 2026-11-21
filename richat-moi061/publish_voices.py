import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
C=json.loads((R/'EPISODE.json').read_text());REPO='seotro95/seotro';TAG=C['release_tag'];BASE=f'https://github.com/{REPO}/releases/download/{TAG}/'
D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
FFMPEG=shutil.which('ffmpeg') or __import__('imageio_ffmpeg').get_ffmpeg_exe()
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def upload(p):
 subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True);print('ASSET_PUBLISHED',p.name,flush=True)
def decode(p):
 process=subprocess.Popen([FFMPEG,'-v','error','-nostdin','-i',str(p),'-ar','48000','-ac','1','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE);n=0
 while block:=process.stdout.read(1024*1024):n+=len(block)
 error=process.stderr.read().decode('utf-8','replace');assert process.wait()==0,error[-1000:];assert n==FRAMES*2,(p.name,n);return n//2
assert TARGET==C['target_seconds'] and FRAMES==C['frames'] and PREFIX==C['prefix']
reports={}
for folder in Path('voice_artifacts').iterdir():
 p=folder/'render_report.json'
 if not p.exists():continue
 report=json.loads(p.read_text());locale=report['locale'];assert locale in PROFILES and locale not in reports
 source=folder/report['filename'];profile=PROFILES[locale]
 assert source.name==f'{PREFIX}_{SLUG[locale]}.mp3'
 assert report['status']=='passed' and report['target_seconds']==TARGET and report['decoded_frames_48000']==FRAMES
 assert report['voice_id']==profile['voice_id'] and report['gender']=='Male'
 assert report['minimum_word_coverage_ratio']>=.97 and report['word_metadata_pieces']>0
 assert report['script_sha256']==sha(R/'voice/scripts'/f'{locale}.json')
 assert sha(source)==report['sha256'] and source.stat().st_size==report['bytes']
 assert len(report['cues'])==(C['english_cues'] if locale=='en-US' else C['translated_sections'])
 if locale=='en-US':assert report['word_metadata_exact_script_match'] and report['word_boundary_cue_split']
 assert all(.55<=c['tempo']<=1.65 for c in report['cues'])
 assert decode(source)==FRAMES
 shutil.copyfile(source,O/source.name);reports[locale]=report;print('FULL_MP3_DECODE_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==16
profile_set=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
profile_set.update(topic_id=C['topic_id'],target_seconds=TARGET,note='All sixteen saved male IDs retained, including Andrew and Nam Minh. Every MP3 fully decoded to the configured duration. Independent native editorial and listening review pending.')
voices=[]
for p in profile_set['profiles']:
 report=reports[p['locale']];p.update(duration_seconds=TARGET,delivery_filename=report['filename'],mp3_sha256=report['sha256'],alignment_granularity=report['timing_alignment'],narration_style_id=report['narration_style_id'])
 voices.append(dict(locale=p['locale'],name=p['name'],voice_id=p['voice_id'],gender='Male',filename=report['filename'],seconds=TARGET,frames_at_48000=FRAMES,sha256=report['sha256'],bytes=report['bytes'],url=BASE+report['filename']))
manifest=dict(topic_id=C['topic_id'],catalogue_id='new-100-topics-20261116',target_seconds=TARGET,main_video_locale='en-US',voices=voices)
qa=dict(status='passed',topic_id=C['topic_id'],voices=16,male_voices=16,all_decoded_seconds=TARGET,all_decoded_frames_48000=FRAMES,all_current_episode_ids_locked=True,previous_voice_ids_retained=16,voice_changes=[],vietnamese_voice_id='vi-VN-NamMinhNeural',unique_audio_hashes=16,english_cue_count=C['english_cues'],other_language_chapter_count=C['translated_sections'],word_metadata_checked=True,english_word_boundary_split_checked=True,pitch_shift_applied=False,independent_native_editorial_review=False,independent_native_listening_review=False,translated_voice_alignment='Ten shared section boundaries; localized retellings, not word-by-word synchronization',reports={k:dict(voice_id=v['voice_id'],filename=v['filename'],decoded_seconds=v['decoded_seconds'],min_tempo=min(c['tempo'] for c in v['cues']),max_tempo=max(c['tempo'] for c in v['cues']),word_accents=v['word_accents']) for k,v in reports.items()})
for name,j in [('AUDIO_MANIFEST.json',manifest),('VOICE_PROFILES_LOCKED.json',profile_set),('VOICE_RELEASE_QA.json',qa)]:dump(O/name,j)
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True);(D/'REPORTS').mkdir(exist_ok=True)
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
for locale,report in reports.items():
 dump(D/'REPORTS'/f'{locale}.json',report)
 if locale=='en-US':continue
 rows=json.loads((R/'voice/scripts'/f'{locale}.json').read_text())
 (D/f'{locale}.txt').write_text('\n\n'.join(r['voice'] for r in rows)+'\n',encoding='utf-8')
 (D/f'{locale}_chapters.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
for name in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:shutil.copyfile(O/name,D/name)
for name in ['TRANSLATION_REVIEW.json','VOICE_INPUT_QA.json','LOCALIZATION_SOURCE_CHAPTERS.json','LOCALIZATION_PATCHES.json','LOCALIZATION_OVERRIDES.json','VI_EXPANSION_REVIEW.json']:shutil.copyfile(R/name,D/name)
style=dict(id=C['style_id'],profile_set_id=profile_set['profile_set_id'],main_voice='en-US-AndrewNeural',vietnamese_voice='vi-VN-NamMinhNeural',native_word_accents_db=1.2,max_word_accents_per_english_cue=2,max_word_accents_per_localized_request=2,pitch_shift_applied=False,english='Native grouped requests split at genuine word boundaries; variable three-to-ten-second blocks, pitch-preserving timing fit',other_languages='Saved male voices; localized retelling, native phrase/question pacing and pitch-preserving section fit',loudness_target_lufs=-19,true_peak_target_db=-2,target_seconds=TARGET,native_listening_review=False,native_english_request_rate='+2%',main_english_wpm=json.loads((D/'DOCUMENT_QA.json').read_text())['english_wpm'])
dump(D/'NARRATION_STYLE_LOCKED.json',style)
docqa=json.loads((D/'DOCUMENT_QA.json').read_text());docqa.update(voices_generated=True,voice_count_verified=16,audio_sample_frames_verified=FRAMES,translated_chapter_alignment_verified=True,independent_native_listening_review=False,native_english_request_rate='+2%');dump(D/'DOCUMENT_QA.json',docqa)
note=f'\nKẾT QUẢ: Đã tạo đủ 16 MP3 nam, mỗi tệp giải mã đúng {C["display_duration"]}; giữ nguyên 16 ID đã lưu. Việt, Nhật, Hàn được trợ lý viết lại toàn bộ; các bản còn lại chuyển thể theo mười phần và sửa có mục tiêu các thuật ngữ địa chất, tuổi, ngữ nghĩa đa nghĩa. Các bản nước ngoài không dịch từng câu hoặc đồng bộ từng từ với bản Anh. Chưa kiểm nghe/biên tập bản ngữ độc lập.\n'
(D/'HUONG_DAN_SU_DUNG.txt').write_text((D/'HUONG_DAN_SU_DUNG.txt').read_text()+note,encoding='utf-8')
readme=(D/'README.md').read_text()+note+f'\n[Tải đủ 16 voice ZIP]({BASE}{PREFIX}_16_VOICES_{C["duration_label"]}.zip) · [Link từng quốc gia]({BASE}LINK_TAI_VOICE.txt)\n\n| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |\n|---|---|---|\n'
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | {C['display_duration']} |\n"
for name in ['README.md','DOWNLOAD_LINKS.md']:(D/name).write_text(readme,encoding='utf-8')
(D/'LINK_TAI_VOICE.txt').write_text(f'{C["topic_id"]} — RICHAT — 16 VOICE NAM — {C["display_duration"]}\n\n'+'\n\n'.join(v['name']+'\n'+v['url'] for v in voices)+'\n',encoding='utf-8')
audiozip=O/f'{PREFIX}_16_VOICES_{C["duration_label"]}.zip';doczip=R/f'{PREFIX}_TAI_LIEU_{C["duration_label"]}.zip'
with zipfile.ZipFile(audiozip,'w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(doczip,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
files=sorted(O.glob('*.mp3'))+[audiozip,doczip]
files += [O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']]
files += [D/n for n in ['README.md','DOWNLOAD_LINKS.md','LINK_TAI_VOICE.txt','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','5_TIEU_DE_VA_THUMBNAIL.txt','VOICE_PROFILES_LOCKED_BASELINE.json']]
for p in files:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
record=dict(topic_id=C['topic_id'],stage='all16voices_and_documents_published',target_seconds=TARGET,assets=[dict(name=a['name'],bytes=a['size'],sha256=a['digest'].removeprefix('sha256:')) for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']])
p=O/'DOCUMENT_ASSET_MANIFEST.json';dump(p,record);upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda x:x['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--title',f'MỚI-061 Richat — {C["prompt_count"]} prompt và 16 voice nam — {C["display_duration"]}','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('RICHAT_FULL16VOICE_DELIVERY_COMPLETE',flush=True)
