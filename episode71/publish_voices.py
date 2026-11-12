import hashlib,json,shutil,subprocess,sys,wave,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
repo='seotro95/seotro';tag='neanderthal-fire-video-71-22m38s';base=f'https://github.com/{repo}/releases/download/{tag}/';D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def upload(p):
 subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True);print('VOICE_ASSET_PUBLISHED',p.name,flush=True)
reports={}
for folder in Path('voice_artifacts').iterdir():
 p=folder/'render_report.json'
 if not p.exists():continue
 j=json.loads(p.read_text());locale=j['locale'];assert locale not in reports
 source=folder/j['filename'];assert source.name==f'{PREFIX}_{SLUG[locale]}.mp3' and sha(source)==j['sha256']
 assert j['status']=='passed' and j['decoded_frames_48000']==FRAMES and j['target_seconds']==TARGET
 assert j['voice_id']==PROFILES[locale]['voice_id'] and j['gender']==PROFILES[locale]['gender']
 if locale!='mww':assert j['minimum_word_coverage_ratio']>=.97 and j['word_metadata_pieces']>0
 if locale=='en-US':assert j['word_metadata_exact_script_match'] and j['word_boundary_cue_split'] and len(j['cues'])==136
 if locale=='vi-VN':assert j['voice_id']=='vi-VN-NamMinhNeural' and j['gender']=='Male'
 if locale=='mww':assert j['reference_sha256']==PROFILES[locale]['reference_sha256']
 decoded=O/'verify.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(decoded)],check=True)
 with wave.open(str(decoded)) as w:assert w.getnframes()==FRAMES and w.getframerate()==48000
 decoded.unlink();shutil.copyfile(source,O/source.name);reports[locale]=j;print('DECODED_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==17
assert sum(r['gender']=='Male' for r in reports.values())==16
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text());profiles['note']='All 17 episode71 voices complete, each decoded to 1358 seconds. Vietnamese explicitly uses actual male NamMinhNeural. Other 16 saved identities retained. Independent native listening and White Hmong dialect review pending.'
voices=[]
for p in profiles['profiles']:
 j=reports[p['locale']];p.update(duration_seconds=TARGET,delivery_filename=j['filename'],mp3_sha256=j['sha256'],alignment_granularity=j['timing_alignment'],narration_style_id='science-documentary-expressive-v3-grouped-English-NamMinh-VI')
 voices.append({'locale':p['locale'],'name':p['name'] if p['locale']!='mww' else "H'mông Trắng (nữ)",'voice_id':p['voice_id'],'gender':p['gender'],'filename':j['filename'],'seconds':TARGET,'frames_at_48000':FRAMES,'sha256':j['sha256'],'bytes':j['bytes'],'url':base+j['filename']})
manifest={'topic_id':71,'target_seconds':TARGET,'main_video_locale':'en-US','voices':voices}
qa={'status':'passed','topic_id':71,'voices':17,'male_voices':16,'female_voice':'hmong-female-3','native_voices':1,'online_voices':16,'vietnamese_voice_id':'vi-VN-NamMinhNeural','all_decoded_seconds':TARGET,'all_decoded_frames_48000':FRAMES,'all_ids_match_episode71_profile':True,'other16saved_voice_ids_retained':True,'native_hmong_reference_matches':True,'unique_audio_hashes':17,'pitch_shift_applied':False,'english_cue_count':136,'other_language_chapter_count':13,'online_word_metadata_checked':True,'english_word_boundary_cue_split_checked':True,'independent_native_listening_review':False,'white_hmong_dialect_independently_verified':False,'reports':{k:{'voice_id':v['voice_id'],'filename':v['filename'],'decoded_seconds':v['decoded_seconds'],'min_tempo':min(x['tempo'] for x in v['cues']),'max_tempo':max(x['tempo'] for x in v['cues']),'word_accents':v['word_accents']} for k,v in reports.items()}}
for n,v in [('AUDIO_MANIFEST.json',manifest),('VOICE_PROFILES_LOCKED.json',profiles),('VOICE_RELEASE_QA.json',qa)]:(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
reportdir=D/'REPORTS';reportdir.mkdir(exist_ok=True)
for locale,j in reports.items():(reportdir/f'{locale}.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
for locale in PROFILES:
 if locale=='en-US':continue
 rows=json.loads((R/'voice/scripts'/f'{locale}.json').read_text());(D/f'{locale}.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
 def ts(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
 (D/f'{locale}_chapters.srt').write_text('\n\n'.join(f"{x['id']}\n{ts(x['start'])} --> {ts(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:shutil.copyfile(O/n,D/n)
style={'id':'science-documentary-expressive-v3-grouped-English-NamMinh-VI','english':'Saved male Andrew 0% grouped requests; exact word-boundary cue cuts; at most two 1.2dB accents per cue; pitch-preserving cue fit','other_online':'Saved male IDs; small phrase/question rate variations; bounded word accents; pitch-preserving chapter fit','vietnamese':'Actual male vi-VN-NamMinhNeural through pinned Melo1.3.1 online backend; live catalogue identity and audio preflight verified; no identity relabel','hmong':'Native female-3 reference clear-v1, speed0.98–1.02, no pitch shift','output_loudness_target_lufs':-19,'output_true_peak_target_db':-2,'target_seconds':1358,'english_cues':136,'other_language_chapters':13}
(D/'NARRATION_STYLE_LOCKED.json').write_text(json.dumps(style,ensure_ascii=False,indent=2)+'\n')
dq=json.loads((D/'DOCUMENT_QA.json').read_text());dq.update(voices_generated=True,voice_count_verified=17,audio_sample_frames_verified=FRAMES);(D/'DOCUMENT_QA.json').write_text(json.dumps(dq,indent=2)+'\n')
readme=f'''# Chủ đề 71 — Người Neanderthal và hồ sơ lửa — 22:38

[Tải kịch bản, 13 TXT prompt và timeline]({base}{PREFIX}_TAI_LIEU_22m38s.zip) · [Tải đủ 17 voice]({base}{PREFIX}_17_VOICES_22m38s.zip) · [5 tiêu đề và 5 prompt thumbnail]({base}5_TIEU_DE_VA_THUMBNAIL.txt)

**The Missing Fires of the Neanderthals** có 3.500 từ Anh, 136 mốc: 135 mốc 10 giây và mốc cuối 8 giây. Có 130 prompt mới trong 13 TXT, đúng 10 prompt/TXT, và 6 mốc dùng lại được đánh dấu. Mọi prompt cấm trẻ em, thiếu niên và động vật non; không có lời nói hoặc âm thanh. Lửa nhỏ và được chứa; không cảnh cháy lan, tiếp xúc nguy hiểm, di cốt người, máu, săn đuổi hoặc tấn công. Cảnh nghiên cứu, vật mẫu và nhân vật đều là minh họa, không dữ liệu đo hoặc chân dung xác thực.

Đã có **17 MP3 riêng, 16 nam và nữ H’mông female-3**. Mỗi tệp đã giải mã kiểm đúng **1.358 giây = 65.184.000 mẫu ở 48 kHz**. Bản Việt dùng đúng **Nam Minh — vi-VN-NamMinhNeural**, qua backend online Melo + Việt 1.3.1, có mẫu thử và danh mục nam đã kiểm. Các tập 45/58 giữ nguyên Adam của chúng. Mười sáu nhận diện khác giữ như tập 58. H’mông dùng backend riêng Voice-Studio-Hmong1.6.6 với mẫu nữ female-3 cố định. Bản Anh căn 136 mốc; bản dịch căn 13 chương chung: 12 chương 110 giây và 38 giây cuối. Cùng thời lượng không có nghĩa từng từ đồng thời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị.

Bản Việt và H’mông được viết lại đủ 13 chương; 14 bản dịch khác dùng nguồn diễn đạt rõ, rà niên đại và các thuật ngữ chính. Chưa có biên tập/nghe bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.

Câu chuyện phân biệt có cháy, kiểm soát lửa, tạo lửa và dùng thường xuyên. Hồ sơ Pháp, El Salt, vết mòn công cụ, Lusakert, Barnham và Abric Romaní được trình bày theo giới hạn bằng chứng. Cập nhật công bố Barnham cuối2025 và nghiên cứu không gian Abric Romaní2026; mô hình mất kỹ năng là khả năng có điều kiện, không chứng minh một lớp cư trú cụ thể.

Chưa có footage hoặc MP4 tập 71. Khi có clip, 10 cảnh đầu 30 giây nằm trong 22:38; phim chính chỉ voice Anh, không tiếng clip, nhạc hoặc SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh hoặc thẻ chữ.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 22:38 |\n"
(D/'README.md').write_text(readme)
g=D/'HUONG_DAN_SU_DUNG.txt';s=g.read_text(encoding='utf-8-sig').replace('SRT hiện là kế hoạch theo lời.','SRT Anh đã căn theo 136 mốc và kiểm tổng thời lượng.').replace('Chỉ bàn giao voice sau khi tạo đủ lời và giải mã từng tệp đúng 65.184.000 mẫu ở 48 kHz.','Đã tạo đủ 17 voice và giải mã kiểm từng tệp đúng 65.184.000 mẫu ở 48 kHz.').replace('Gói tài liệu giai đoạn này chưa chứa audio, footage hoặc MP4.','Đã phát hành 17 MP3 riêng và ZIP voice; gói tài liệu không chứa footage hoặc MP4.');g.write_text(s,encoding='utf-8-sig')
for n in ['PRODUCTION_STEPS_APPLIED.md']:
 if (R/n).exists():shutil.copyfile(R/n,D/n)
with zipfile.ZipFile(O/f'{PREFIX}_17_VOICES_22m38s.zip','w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_22m38s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
assets=[*sorted(O.glob('*.mp3')),O/f'{PREFIX}_17_VOICES_22m38s.zip',*[O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']],R/f'{PREFIX}_TAI_LIEU_22m38s.zip',*[D/n for n in ['README.md','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','5_TIEU_DE_VA_THUMBNAIL.txt']]]
if (D/'PRODUCTION_STEPS_APPLIED.md').exists():assets.append(D/'PRODUCTION_STEPS_APPLIED.md')
for p in assets:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']))
man={'topic_id':71,'target_seconds':TARGET,'stage':'all17voices_and_documents_published','self_and_checksum_file_excluded':True,'assets':[{'name':a['name'],'bytes':a['size'],'sha256':a['digest'].removeprefix('sha256:')} for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt'] and not a['name'].endswith('.mp3')]}
p=O/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(man,ensure_ascii=False,indent=2));upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']));p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda a:a['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Chủ đề 71 — Người Neanderthal và lửa — Kịch bản,130 prompt và17 voice22:38','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('FULL17VOICE_DELIVERY_COMPLETE',flush=True)
