import hashlib,json,shutil,subprocess,sys,wave,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
repo='seotro95/seotro';tag='homo-luzonensis-video-85-21m22s';base=f'https://github.com/{repo}/releases/download/{tag}/';D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
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
 if locale=='en-US':assert j['word_metadata_exact_script_match'] and j['word_boundary_cue_split'] and len(j['cues'])==129
 if locale=='vi-VN':assert j['voice_id']=='vi-VN-NamMinhNeural' and j['gender']=='Male'
 if locale=='mww':assert j['reference_sha256']==PROFILES[locale]['reference_sha256']
 decoded=O/'verify.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(decoded)],check=True)
 with wave.open(str(decoded)) as w:assert w.getnframes()==FRAMES and w.getframerate()==48000
 decoded.unlink();shutil.copyfile(source,O/source.name);reports[locale]=j;print('DECODED_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==17
assert sum(r['gender']=='Male' for r in reports.values())==16
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text());profiles['note']='All17 episode85 voices complete, each decoded to1282seconds. All17 identities retained from topic71, including actual male NamMinhNeural and native Hmong female-3. Independent native listening and WhiteHmongdialect review pending.'
voices=[]
for p in profiles['profiles']:
 j=reports[p['locale']];p.update(duration_seconds=TARGET,delivery_filename=j['filename'],mp3_sha256=j['sha256'],alignment_granularity=j['timing_alignment'],narration_style_id='science-documentary-expressive-v3-grouped-English-NamMinh-VI')
 voices.append({'locale':p['locale'],'name':p['name'] if p['locale']!='mww' else "H'mông Trắng (nữ)",'voice_id':p['voice_id'],'gender':p['gender'],'filename':j['filename'],'seconds':TARGET,'frames_at_48000':FRAMES,'sha256':j['sha256'],'bytes':j['bytes'],'url':base+j['filename']})
manifest={'topic_id':85,'target_seconds':TARGET,'main_video_locale':'en-US','voices':voices}
qa={'status':'passed','topic_id':85,'voices':17,'male_voices':16,'female_voice':'hmong-female-3','native_voices':1,'online_voices':16,'vietnamese_voice_id':'vi-VN-NamMinhNeural','all_decoded_seconds':TARGET,'all_decoded_frames_48000':FRAMES,'all_ids_match_episode85_profile':True,'all17saved_voice_ids_retained':True,'native_hmong_reference_matches':True,'unique_audio_hashes':17,'pitch_shift_applied':False,'english_cue_count':129,'other_language_chapter_count':13,'online_word_metadata_checked':True,'english_word_boundary_cue_split_checked':True,'independent_native_listening_review':False,'white_hmong_dialect_independently_verified':False,'reports':{k:{'voice_id':v['voice_id'],'filename':v['filename'],'decoded_seconds':v['decoded_seconds'],'min_tempo':min(x['tempo'] for x in v['cues']),'max_tempo':max(x['tempo'] for x in v['cues']),'word_accents':v['word_accents']} for k,v in reports.items()}}
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
style={'id':'science-documentary-expressive-v3-grouped-English-NamMinh-VI','english':'Saved male Andrew 0% grouped requests; exact word-boundary cue cuts; at most two 1.2dB accents per cue; pitch-preserving cue fit','other_online':'Saved male IDs; small phrase/question rate variations; bounded word accents; pitch-preserving chapter fit','vietnamese':'Actual male vi-VN-NamMinhNeural through pinned Melo1.3.1 online backend; live catalogue identity and audio preflight verified; no identity relabel','hmong':'Native female-3 reference clear-v1, speed0.98–1.02, no pitch shift','output_loudness_target_lufs':-19,'output_true_peak_target_db':-2,'target_seconds':1282,'english_cues':129,'other_language_chapters':13}
(D/'NARRATION_STYLE_LOCKED.json').write_text(json.dumps(style,ensure_ascii=False,indent=2)+'\n')
dq=json.loads((D/'DOCUMENT_QA.json').read_text());dq.update(voices_generated=True,voice_count_verified=17,audio_sample_frames_verified=FRAMES);(D/'DOCUMENT_QA.json').write_text(json.dumps(dq,indent=2)+'\n')
readme=f'''# Chủ đề 85 — Homo luzonensis — 21:22

[Tải kịch bản, 12 TXT prompt và timeline]({base}{PREFIX}_TAI_LIEU_21m22s.zip) · [Tải đủ 17 voice]({base}{PREFIX}_17_VOICES_21m22s.zip) · [5 tiêu đề và 5 prompt thumbnail]({base}5_TIEU_DE_VA_THUMBNAIL.txt)

**The Island Humans We Still Can’t Place** có 3.501 từ Anh, 129 mốc: 128 mốc 10 giây và mốc cuối 2 giây. Có 120 prompt mới trong 12 TXT, đúng 10 prompt/TXT, và 9 mốc dùng lại được đánh dấu. Mọi prompt cấm trẻ em, thiếu niên, mẫu chưa trưởng thành, lời nói và âm thanh. Mẫu xương/răng là giáo cụ trưởng thành có dấu chế tạo rõ; không di cốt người thật. Không phục dựng sọ, khuôn mặt, chiều cao hoặc cơ thể hoàn chỉnh của H. luzonensis. Các mô hình địa hình và nhánh là ví dụ, không dữ liệu đo, cây phát sinh xác thực hoặc tuyến vượt biển đã biết.

Đã có **17 MP3 riêng, 16 nam và nữ H’mông female-3**. Mỗi tệp đã giải mã kiểm đúng **1.282 giây = 61.536.000 mẫu ở 48 kHz**. Giữ đủ 17 nhận diện từ tập 71: Việt dùng đúng **Nam Minh — vi-VN-NamMinhNeural**, qua backend online Melo + Việt 1.3.1; H’mông dùng backend riêng Voice-Studio-Hmong 1.6.6 với mẫu nữ female-3 cố định. Không đổi audio của các tập cũ. Bản Anh căn 129 mốc; bản dịch căn 13 chương chung: 12 chương 100 giây và 82 giây cuối. Cùng thời lượng không có nghĩa từng từ đồng thời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị.

Bản Việt và H’mông được viết lại đủ 13 chương; 14 bản dịch khác dùng nguồn diễn đạt rõ, rà niên đại và thuật ngữ chính. Đã sửa nghĩa đặc điểm giải phẫu, tuổi tối thiểu và ảnh hưởng uranium trong các câu then chốt. Chưa có biên tập/nghe bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.

Câu chuyện đi từ Callao đến giải phẫu, phép định tuổi, rào cản biển, Kalinga và giả thuyết họ hàng. Phân biệt mốc tối thiểu ban đầu 50/67 nghìn năm với tái đánh giá 134 ± 14 nghìn năm năm 2023. Kalinga khoảng 709 ± 68 nghìn năm không tự xác định người tạo công cụ là H. luzonensis. Phân tích năm 2026 ưu tiên một giả thuyết quan hệ với H. erectus châu Á trong bối cảnh đảo, không phải kết luận tổ tiên trực tiếp hoặc phả hệ DNA chắc chắn.

Chưa có footage hoặc MP4 tập 85. Khi có clip, 10 cảnh đầu 30 giây nằm trong 21:22; phim chính chỉ voice Anh, không tiếng clip, nhạc hoặc SFX. Cảnh thiếu dùng video chuyển động liên quan, không ảnh tĩnh hoặc thẻ chữ.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 21:22 |\n"
(D/'README.md').write_text(readme)
g=D/'HUONG_DAN_SU_DUNG.txt';text=g.read_text(encoding='utf-8-sig')
text=text.replace('SRT hiện là kế hoạch theo lời.','SRT Anh đã căn theo 129 mốc và kiểm tổng thời lượng.').replace('Chỉ phát hành voice sau khi đủ lời, đúng ID và giải mã mỗi MP3 đúng 61.536.000 mẫu ở 48 kHz.','Đã phát hành đủ 17 voice, kiểm đúng ID và giải mã mỗi MP3 đúng 61.536.000 mẫu ở 48 kHz.').replace('Tài liệu giai đoạn này chưa chứa audio, footage hoặc MP4.','Đã phát hành 17 MP3 riêng và ZIP voice; gói tài liệu không chứa footage hoặc MP4.')
g.write_text(text,encoding='utf-8-sig')
for n in ['PRODUCTION_STEPS_APPLIED.md']:
 if (R/n).exists():shutil.copyfile(R/n,D/n)
with zipfile.ZipFile(O/f'{PREFIX}_17_VOICES_21m22s.zip','w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_21m22s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
assets=[*sorted(O.glob('*.mp3')),O/f'{PREFIX}_17_VOICES_21m22s.zip',*[O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']],R/f'{PREFIX}_TAI_LIEU_21m22s.zip',*[D/n for n in ['README.md','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','5_TIEU_DE_VA_THUMBNAIL.txt']]]
if (D/'PRODUCTION_STEPS_APPLIED.md').exists():assets.append(D/'PRODUCTION_STEPS_APPLIED.md')
for p in assets:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']))
man={'topic_id':85,'target_seconds':TARGET,'stage':'all17voices_and_documents_published','self_and_checksum_file_excluded':True,'assets':[{'name':a['name'],'bytes':a['size'],'sha256':a['digest'].removeprefix('sha256:')} for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt'] and not a['name'].endswith('.mp3')]}
p=O/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(man,ensure_ascii=False,indent=2));upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']));p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda a:a['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Chủ đề 85 — Homo luzonensis — Kịch bản,120 prompt và17 voice21:22','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('FULL17VOICE_DELIVERY_COMPLETE',flush=True)
