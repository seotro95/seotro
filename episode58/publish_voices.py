import hashlib,json,shutil,subprocess,sys,wave,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
repo='seotro95/seotro';tag='bone-traces-video-58-22m42s';base=f'https://github.com/{repo}/releases/download/{tag}/';D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
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
 if locale=='en-US':assert j['word_metadata_exact_script_match'] and j['word_boundary_cue_split'] and len(j['cues'])==137
 if locale=='vi-VN':assert j['voice_id']=='Adam' and j['preset_sha256']==PROFILES[locale]['preset_sha256']
 if locale=='mww':assert j['reference_sha256']==PROFILES[locale]['reference_sha256']
 decoded=O/'verify.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(decoded)],check=True)
 with wave.open(str(decoded)) as w:assert w.getnframes()==FRAMES and w.getframerate()==48000
 decoded.unlink();shutil.copyfile(source,O/source.name);reports[locale]=j;print('DECODED_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==17
assert sum(r['gender']=='Male' for r in reports.values())==16
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text());profiles['note']='All17episode58voices complete and decoded to1362seconds. Vietnameseexplicitly changed to nativeAdam; other16savedidentities retained. Independent native listening and WhiteHmongdialect review pending.'
voices=[]
for p in profiles['profiles']:
 j=reports[p['locale']];p.update(duration_seconds=TARGET,delivery_filename=j['filename'],mp3_sha256=j['sha256'],alignment_granularity=j['timing_alignment'],narration_style_id='science-documentary-expressive-v2-grouped-English-Adam-VI')
 voices.append({'locale':p['locale'],'name':p['name'] if p['locale']!='mww' else "H'mông Trắng (nữ)",'voice_id':p['voice_id'],'gender':p['gender'],'filename':j['filename'],'seconds':TARGET,'frames_at_48000':FRAMES,'sha256':j['sha256'],'bytes':j['bytes'],'url':base+j['filename']})
manifest={'topic_id':58,'target_seconds':TARGET,'main_video_locale':'en-US','voices':voices}
qa={'status':'passed','topic_id':58,'voices':17,'male_voices':16,'female_voice':'hmong-female-3','native_voices':2,'online_voices':15,'vietnamese_voice_id':'Adam','all_decoded_seconds':TARGET,'all_decoded_frames_48000':FRAMES,'all_ids_match_episode58_profile':True,'other16saved_voice_ids_retained':True,'native_hmong_reference_matches':True,'native_adam_preset_matches':True,'unique_audio_hashes':17,'pitch_shift_applied':False,'english_cue_count':137,'other_language_chapter_count':13,'online_word_metadata_checked':True,'english_word_boundary_cue_split_checked':True,'independent_native_listening_review':False,'white_hmong_dialect_independently_verified':False,'reports':{k:{'voice_id':v['voice_id'],'filename':v['filename'],'decoded_seconds':v['decoded_seconds'],'min_tempo':min(x['tempo'] for x in v['cues']),'max_tempo':max(x['tempo'] for x in v['cues']),'word_accents':v['word_accents']} for k,v in reports.items()}}
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
style={'id':'science-documentary-expressive-v2-grouped-English-Adam-VI','english':'NativeAndrew0% groupedrequests; exactwordboundarycuecuts; atmosttwo1.2dBaccentspercue; pitchpreservingcuefit','other_online':'SavedmaleIDs; smallphrase/questionratevariations; boundedwordaccents; pitchpreservingchapterfit','vietnamese':'ActualnativeAdam preset inVieNeu3.8.3 throughMelo1.3.1worker, punctuation andsmallpauses,FP32ONNX, modelandpresethasheslocked','hmong':'Nativefemale3reference clear-v1,speed0.98–1.02,no pitchshift','output_loudness_target_lufs':-19,'output_true_peak_target_db':-2,'target_seconds':1362,'english_cues':137,'other_language_chapters':13}
(D/'NARRATION_STYLE_LOCKED.json').write_text(json.dumps(style,ensure_ascii=False,indent=2))
dq=json.loads((D/'DOCUMENT_QA.json').read_text());dq.update(voices_generated=True,voice_count_verified=17,audio_sample_frames_verified=FRAMES);(D/'DOCUMENT_QA.json').write_text(json.dumps(dq,indent=2))
readme=f'''# Chủ đề 58 — Móng, răng và xương — 22:42

[Tải kịch bản, 13 TXT prompt và timeline]({base}BONE_TRACES_58_TAI_LIEU_22m42s.zip) · [Tải đủ 17 voice]({base}BONE_TRACES_58_17_VOICES_22m42s.zip) · [5 tiêu đề và 5 prompt thumbnail]({base}5_TIEU_DE_VA_THUMBNAIL.txt)

**Before You Call It a Hunt** có 3.647 từ Anh,137 mốc:136 mốc 10 giây và mốc cuối 2 giây. Có130 prompt mới trong 13 TXT, đúng 10 prompt/TXT, và 7 mốc dùng lại được đánh dấu. Mọi prompt cấm trẻ em, thiếu niên và động vật non; không có lời nói hoặc âm thanh. Mẫu vật minh họa là động vật trưởng thành sạch hoặc bản sao nhựa; không có di cốt người, máu, cảnh săn đuổi hoặc tấn công.

Đã có **17 MP3 riêng,16 nam và nữ H’mông female-3**. Mỗi tệp đã giải mã kiểm đúng **1.362 giây =65.376.000 mẫu ở 48 kHz**. Việt dùng đúng **Adam native, nam miền Nam**, qua Melo + Việt 1.3.1 / VieNeu3.8.3 ONNXFP32. Mười sáu nhận diện khác giữ như tập 45. Bản Anh căn 137 mốc; bản dịch căn 13 chương chung: 12 chương 110 giây và 42 giây cuối. Cùng thời lượng không có nghĩa từng từ đồng thời.

Bản Việt và H’mông được viết lại đủ13 chương;14 bản dịch khác dùng nguồn diễn đạt rõ, kiểm niên đại và thuật ngữ. Chưa có biên tập/nghe bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.

Nội dung phân biệt tác nhân gây dấu, thứ tự tác động và cách kiếm con vật. Ba khay là tình huống giảng giải, không phải phát hiện mới. Chưa có footage hoặc MP4 tập 58. Khi có clip,10 cảnh đầu 30 giây nằm trong 22:42; chỉ voice Anh,không tiếng clip, nhạc hoặc SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh hoặc thẻ chữ.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 22:42 |\n"
(D/'README.md').write_text(readme)
guide=D/'HUONG_DAN_SU_DUNG.txt';g=guide.read_text(encoding='utf-8-sig')
g=g.replace('SRT hiện là kế hoạch theo lời.','SRT Anh đã được căn theo137 mốc lời và kiểm tổng thời lượng.').replace('Chỉ bàn giao audio sau khi tạo đủ lời và giải mã kiểm từng tệp đúng 65.376.000 mẫu.','Đã tạo đủ 17 voice và giải mã kiểm mỗi tệp đúng65.376.000 mẫu.').replace('Gói tài liệu ở giai đoạn này chưa có audio, footage hoặc MP4.','Đã phát hành17 MP3 riêng và gói ZIP voice; gói tài liệu không chứa footage hoặc MP4.')
guide.write_text(g,encoding='utf-8-sig')
for n in ['ADAM_MODEL_RECORDS.json','PRODUCTION_STEPS_APPLIED.md']:
 if (R/n).exists():shutil.copyfile(R/n,D/n)
with zipfile.ZipFile(O/'BONE_TRACES_58_17_VOICES_22m42s.zip','w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/'BONE_TRACES_58_TAI_LIEU_22m42s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
assets=[*sorted(O.glob('*.mp3')),O/'BONE_TRACES_58_17_VOICES_22m42s.zip',*[O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']],R/'BONE_TRACES_58_TAI_LIEU_22m42s.zip',*[D/n for n in ['README.md','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','ADAM_MODEL_RECORDS.json','5_TIEU_DE_VA_THUMBNAIL.txt']]]
if (D/'PRODUCTION_STEPS_APPLIED.md').exists():assets.append(D/'PRODUCTION_STEPS_APPLIED.md')
for p in assets:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']))
man={'topic_id':58,'target_seconds':TARGET,'stage':'all17voices_and_documents_published','self_and_checksum_file_excluded':True,'assets':[{'name':a['name'],'bytes':a['size'],'sha256':a['digest'].removeprefix('sha256:')} for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt'] and not a['name'].endswith('.mp3')]}
p=O/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(man,ensure_ascii=False,indent=2));upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']));p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda a:a['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Chủ đề 58 — Móng, răng và xương — Kịch bản,130 prompt và17 voice22:42','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('FULL17VOICE_DELIVERY_COMPLETE',flush=True)
