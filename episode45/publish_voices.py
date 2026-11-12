import hashlib,json,shutil,subprocess,sys,wave,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
repo='seotro95/seotro';tag='food-preservation-video-45-20m42s';base=f'https://github.com/{repo}/releases/download/{tag}/';D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def upload(p):subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True);print('VOICE_ASSET_PUBLISHED',p.name,flush=True)
reports={}
for folder in Path('voice_artifacts').iterdir():
 p=folder/'render_report.json'
 if not p.exists():continue
 j=json.loads(p.read_text());locale=j['locale'];assert locale not in reports
 source=folder/j['filename'];assert source.name==f'{PREFIX}_{SLUG[locale]}.mp3' and sha(source)==j['sha256']
 assert j['status']=='passed' and j['decoded_frames_48000']==FRAMES and j['target_seconds']==TARGET
 assert j['voice_id']==PROFILES[locale]['voice_id'] and j['gender']==PROFILES[locale]['gender']
 if locale not in ['vi-VN','mww']:assert j['minimum_word_coverage_ratio']>=.97 and j['word_metadata_pieces']>0
 if locale=='en-US':assert j['word_metadata_exact_script_match'] and j['word_boundary_cue_split'] and len(j['cues'])==125
 if locale=='vi-VN':assert j['voice_id']=='Adam' and j['preset_sha256']==PROFILES[locale]['preset_sha256']
 if locale=='mww':assert j['reference_sha256']==PROFILES[locale]['reference_sha256']
 decoded=O/'verify.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(decoded)],check=True)
 with wave.open(str(decoded)) as w:assert w.getnframes()==FRAMES and w.getframerate()==48000
 decoded.unlink();shutil.copyfile(source,O/source.name);reports[locale]=j;print('DECODED_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==17
assert sum(r['gender']=='Male' for r in reports.values())==16
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text());profiles['note']='All17episode45voices complete and decoded to1242seconds. Vietnameseexplicitly changed to nativeAdam; other16savedidentities retained. Independent native listening and WhiteHmongdialect review pending.'
voices=[]
for p in profiles['profiles']:
 j=reports[p['locale']];p.update(duration_seconds=TARGET,delivery_filename=j['filename'],mp3_sha256=j['sha256'],alignment_granularity=j['timing_alignment'],narration_style_id='science-documentary-expressive-v2-grouped-English-Adam-VI')
 voices.append({'locale':p['locale'],'name':p['name'] if p['locale']!='mww' else "H'mông Trắng (nữ)",'voice_id':p['voice_id'],'gender':p['gender'],'filename':j['filename'],'seconds':TARGET,'frames_at_48000':FRAMES,'sha256':j['sha256'],'bytes':j['bytes'],'url':base+j['filename']})
manifest={'topic_id':45,'target_seconds':TARGET,'main_video_locale':'en-US','voices':voices}
qa={'status':'passed','topic_id':45,'voices':17,'male_voices':16,'female_voice':'hmong-female-3','native_voices':2,'online_voices':15,'vietnamese_voice_id':'Adam','all_decoded_seconds':TARGET,'all_decoded_frames_48000':FRAMES,'all_ids_match_episode45_profile':True,'other16saved_voice_ids_retained':True,'native_hmong_reference_matches':True,'native_adam_preset_matches':True,'unique_audio_hashes':17,'pitch_shift_applied':False,'english_cue_count':125,'other_language_chapter_count':13,'online_word_metadata_checked':True,'english_word_boundary_cue_split_checked':True,'independent_native_listening_review':False,'white_hmong_dialect_independently_verified':False,'reports':{k:{'voice_id':v['voice_id'],'filename':v['filename'],'decoded_seconds':v['decoded_seconds'],'min_tempo':min(x['tempo'] for x in v['cues']),'max_tempo':max(x['tempo'] for x in v['cues']),'word_accents':v['word_accents']} for k,v in reports.items()}}
for n,v in [('AUDIO_MANIFEST.json',manifest),('VOICE_PROFILES_LOCKED.json',profiles),('VOICE_RELEASE_QA.json',qa)]:(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2))
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
reportdir=D/'REPORTS';reportdir.mkdir(exist_ok=True)
for locale,j in reports.items():(reportdir/f'{locale}.json').write_text(json.dumps(j,ensure_ascii=False,indent=2))
for locale in PROFILES:
 if locale=='en-US':continue
 rows=json.loads((R/'voice/scripts'/f'{locale}.json').read_text());(D/f'{locale}.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
 def ts(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
 (D/f'{locale}_chapters.srt').write_text('\n\n'.join(f"{x['id']}\n{ts(x['start'])} --> {ts(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:shutil.copyfile(O/n,D/n)
style={'id':'science-documentary-expressive-v2-grouped-English-Adam-VI','english':'NativeAndrew0% groupedrequests; exactwordboundarycuecuts; atmosttwo1.2dBaccentspercue; pitchpreservingcuefit','other_online':'SavedmaleIDs; smallphrase/questionratevariations; boundedwordaccents; pitchpreservingchapterfit','vietnamese':'ActualnativeAdam preset inVieNeu3.8.3 throughMelo1.3.1worker, punctuation andsmallpauses,FP32ONNX, modelandpresethasheslocked','hmong':'Nativefemale3reference clear-v1,speed0.98–1.02,no pitchshift','output_loudness_target_lufs':-19,'output_true_peak_target_db':-2,'target_seconds':1242,'english_cues':125,'other_language_chapters':13}
(D/'NARRATION_STYLE_LOCKED.json').write_text(json.dumps(style,ensure_ascii=False,indent=2))
dq=json.loads((D/'DOCUMENT_QA.json').read_text());dq.update(voices_generated=True,voice_count_verified=17,audio_sample_frames_verified=FRAMES);(D/'DOCUMENT_QA.json').write_text(json.dumps(dq,indent=2))
readme=f'''# Chủ đề 45 — Bảo quản thức ăn thời tiền sử — 20:42

[Tải kịch bản, 11 TXT prompt và timeline]({base}FOOD_PRESERVATION_45_TAI_LIEU_20m42s.zip) · [Tải đủ 17 voice]({base}FOOD_PRESERVATION_45_17_VOICES_20m42s.zip)

**The Meal That Had to Survive Tomorrow** có 3.134 từ Anh và 125 mốc lời: 124 mốc 10 giây và mốc cuối 2 giây. Có 110 prompt mới trong 11 TXT, đúng 10 prompt/TXT; 15 mốc dùng lại được đánh dấu. Mọi prompt cấm trẻ em và thiếu niên, kể cả nền, ảnh, màn hình và phản chiếu; không có lời nói hoặc âm thanh.

Đã có **17 MP3 riêng: 16 nam và nữ H'mông female-3**. Mỗi tệp đã được giải mã kiểm tra đúng **1.242 giây = 59.616.000 mẫu ở 48 kHz**. Bản Việt dùng đúng **Adam, nam miền Nam**, preset native của VieNeu 3.8.3 qua backend Melo + Việt 1.3.1. Mười sáu nhận diện giọng khác giữ nguyên. Tiếng Anh là bản chính, căn 125 mốc; các bản dịch giữ 13 ranh giới chương. Cùng thời lượng không đồng nghĩa từng từ ở mọi ngôn ngữ trùng thời điểm.

Bản Việt và H'mông đều được viết lại đủ 13 chương. Mười bốn bản dịch còn lại đã làm rõ nguồn, kiểm niên đại và sửa thuật ngữ. Kiểm kỹ thuật không thay thế việc nghe và biên tập bản ngữ. Phương ngữ H'mông Trắng chưa được xác nhận độc lập.

Chưa có footage hoặc MP4 hoàn chỉnh của tập 45. Khi có clip, đoạn mở đầu gồm 10 cảnh trong 30 giây nằm trong tổng 20:42; chỉ dùng voice Anh, không nhạc/SFX. Cảnh thiếu dùng video chuyển động liên quan, không dùng ảnh tĩnh hoặc thẻ chữ.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 20:42 |\n"
(D/'README.md').write_text(readme)
guide=D/'HUONG_DAN_SU_DUNG.txt';s=guide.read_text(encoding='utf-8-sig').replace('SRT hiện là kế hoạch theo lời.','SRT Anh đã được căn theo125mốc voice và kiểm tra thời lượng.').replace('Bộ tài liệu chưa chứa audio đã tạo, footage hoặc MP4 hoàn chỉnh.','17voice đã phát hành thành tệp riêng vàgóiZIPâmthanh; gói tài liệu không chứafootage hoặcMP4.').replace('Chỉ bàn giao audio sau khi tạo và giải mã kiểm tra đủ','Đã tạo và giải mã kiểm tra đủ');guide.write_text(s,encoding='utf-8-sig')
for n in ['ADAM_MODEL_RECORDS.json','PRODUCTION_STEPS_APPLIED.md']:
 if (R/n).exists():shutil.copyfile(R/n,D/n)
with zipfile.ZipFile(O/'FOOD_PRESERVATION_45_17_VOICES_20m42s.zip','w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/'FOOD_PRESERVATION_45_TAI_LIEU_20m42s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
assets=[*sorted(O.glob('*.mp3')),O/'FOOD_PRESERVATION_45_17_VOICES_20m42s.zip',*[O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']],R/'FOOD_PRESERVATION_45_TAI_LIEU_20m42s.zip',*[D/n for n in ['README.md','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','ADAM_MODEL_RECORDS.json']]]
if (D/'PRODUCTION_STEPS_APPLIED.md').exists():assets.append(D/'PRODUCTION_STEPS_APPLIED.md')
for p in assets:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']))
man={'topic_id':45,'target_seconds':TARGET,'stage':'all17voices_and_documents_published','self_and_checksum_file_excluded':True,'assets':[{'name':a['name'],'bytes':a['size'],'sha256':a['digest'].removeprefix('sha256:')} for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt'] and not a['name'].endswith('.mp3')]}
p=O/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(man,ensure_ascii=False,indent=2));upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']));p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda a:a['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Chủ đề45 — Bảo quản thức ăn — Kịch bản,110prompt và17voice20:42','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('FULL17VOICE_DELIVERY_COMPLETE',flush=True)
