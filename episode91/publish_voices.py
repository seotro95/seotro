import hashlib,json,shutil,subprocess,sys,wave,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
repo='seotro95/seotro';tag='saqqaq-hair-video-91-22m12s';base=f'https://github.com/{repo}/releases/download/{tag}/';D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
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
 if locale=='en-US':assert j['word_metadata_exact_script_match'] and j['word_boundary_cue_split'] and len(j['cues'])==134
 if locale=='vi-VN':assert j['voice_id']=='vi-VN-NamMinhNeural' and j['gender']=='Male'
 if locale=='mww':assert j['reference_sha256']==PROFILES[locale]['reference_sha256']
 decoded=O/'verify.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(decoded)],check=True)
 with wave.open(str(decoded)) as w:assert w.getnframes()==FRAMES and w.getframerate()==48000
 decoded.unlink();shutil.copyfile(source,O/source.name);reports[locale]=j;print('DECODED_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==17
assert sum(r['gender']=='Male' for r in reports.values())==16
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text());profiles['note']='All17 episode91 voices complete, each decoded to1332seconds. All17 identities retained from topic71, including actual male NamMinhNeural and native Hmong female-3. Independent native listening and WhiteHmongdialect review pending.'
voices=[]
for p in profiles['profiles']:
 j=reports[p['locale']];p.update(duration_seconds=TARGET,delivery_filename=j['filename'],mp3_sha256=j['sha256'],alignment_granularity=j['timing_alignment'],narration_style_id='science-documentary-expressive-v3-grouped-English-NamMinh-VI')
 voices.append({'locale':p['locale'],'name':p['name'] if p['locale']!='mww' else "H'mông Trắng (nữ)",'voice_id':p['voice_id'],'gender':p['gender'],'filename':j['filename'],'seconds':TARGET,'frames_at_48000':FRAMES,'sha256':j['sha256'],'bytes':j['bytes'],'url':base+j['filename']})
manifest={'topic_id':91,'target_seconds':TARGET,'main_video_locale':'en-US','voices':voices}
qa={'status':'passed','topic_id':91,'voices':17,'male_voices':16,'female_voice':'hmong-female-3','native_voices':1,'online_voices':16,'vietnamese_voice_id':'vi-VN-NamMinhNeural','all_decoded_seconds':TARGET,'all_decoded_frames_48000':FRAMES,'all_ids_match_episode91_profile':True,'all17saved_voice_ids_retained':True,'native_hmong_reference_matches':True,'unique_audio_hashes':17,'pitch_shift_applied':False,'english_cue_count':134,'other_language_chapter_count':14,'online_word_metadata_checked':True,'english_word_boundary_cue_split_checked':True,'independent_native_listening_review':False,'white_hmong_dialect_independently_verified':False,'reports':{k:{'voice_id':v['voice_id'],'filename':v['filename'],'decoded_seconds':v['decoded_seconds'],'min_tempo':min(x['tempo'] for x in v['cues']),'max_tempo':max(x['tempo'] for x in v['cues']),'word_accents':v['word_accents']} for k,v in reports.items()}}
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
style={'id':'science-documentary-expressive-v3-grouped-English-NamMinh-VI','english':'Saved male Andrew 0% grouped requests; exact word-boundary cue cuts; at most two 1.2dB accents per cue; pitch-preserving cue fit','other_online':'Saved male IDs; small phrase/question rate variations; bounded word accents; pitch-preserving chapter fit','vietnamese':'Actual male vi-VN-NamMinhNeural through pinned Melo1.3.1 online backend; live catalogue identity and audio preflight verified; no identity relabel','hmong':'Native female-3 reference clear-v1, speed0.98–1.02, no pitch shift','output_loudness_target_lufs':-19,'output_true_peak_target_db':-2,'target_seconds':1332,'english_cues':134,'other_language_chapters':14}
(D/'NARRATION_STYLE_LOCKED.json').write_text(json.dumps(style,ensure_ascii=False,indent=2)+'\n')
dq=json.loads((D/'DOCUMENT_QA.json').read_text());dq.update(voices_generated=True,voice_count_verified=17,audio_sample_frames_verified=FRAMES);(D/'DOCUMENT_QA.json').write_text(json.dumps(dq,indent=2)+'\n')
readme=f'''# Chủ đề 91 — Tóc Saqqaq và ADN Bắc Cực — 22:12

[Tải kịch bản và12TXTprompt]({base}{PREFIX}_TAI_LIEU_22m12s.zip) · [Tải đủ17voice]({base}{PREFIX}_17_VOICES_22m12s.zip) · [5tiêu đề và5promptthumbnail]({base}5_TIEU_DE_VA_THUMBNAIL.txt)

**The Hair That Changed Arctic History** có3.703từ Anh,134mốc:133mốc10giây và2giây cuối.120prompt mới trong12TXT,đúng10prompt/TXT;14mốc dùng lại đã đánh dấu. Mỗi prompt cấm trẻ em,thiếu niên,lời nói và âm thanh. Tóc,mô hình và cảnh là minh họa,không mẫu thật,dữ liệu đo,tuyến di cư hoặc chân dung người sở hữu tóc đã xác nhận.

Đã có17MP3riêng:16nam vànữH’môngfemale-3. Mỗi bản được giải mã đúng1.332giây=63.936.000mẫu48kHz. Giữ17ID từ tập71,gồm NamMinhNeural nam qua backendonlineMelo+ViệtStudio1.3.1 và H’môngnativefemale-3 qua công cụ riêng1.6.6. Anh căn134mốc;bản dịch14chương:13×100giây+32giây cuối. Cùng thời lượng không có nghĩa từng từ đồng thời. SRT dịch theo chương cần chia nhỏ trước khi hiển thị.

Việt vàH’mông viết lại đủ14chương;14bản khác được địa phương hóa từ phần nội dung chính của từng chương,bỏ chuyển ý lặp để giữ nhịp nói tự nhiên. Đã rà ngày tháng,đơn vị và thuật ngữ. Chưa có kiểm nghe/biên tập bản ngữ độc lập hoặc xác minh phương ngữ H’mông Trắng độc lập.

Câu chuyện theo tócSaqqaq từQeqertasussuk qua bảo tồn,định tuổi,xác thực ADN và lịch sử dân cư. Phân biệt ty thể2008,genome nhân2010,khung2014/2019 và hướng epigenome2014. Không đồng nhất văn hóa với gen,tuổi mẫu với tuổi di cư,dự đoán tính trạng với ảnh,hoặc nói mọi nguồn tổ tiên đã biến mất.

Chưa có footage hoặcMP4tập91. Khi có clip,10cảnh trong30giây đầu nằm trong22:12;phim chính chỉ voiceAnh,xóa âmclip,không nhạc/SFX. Cảnh thiếu dùng video chuyển động liên quan,không ảnh tĩnh/thẻ chữ.

| Quốc gia /ngôn ngữ | TảiMP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 22:12 |\n"
(D/'README.md').write_text(readme)
g=D/'HUONG_DAN_SU_DUNG.txt';text=g.read_text(encoding='utf-8-sig').replace('SRT hiện là kế hoạch theo lời.','SRT Anh đã căn134mốc vàkiểm tổng thời lượng.').replace('Tài liệu giai đoạn này chưa chứa audio, footage hoặc MP4.','Đã phát hành17MP3riêng vàZIPvoice;gói tài liệu không chứa footage hoặcMP4.');g.write_text(text,encoding='utf-8-sig')
for n in ['PRODUCTION_STEPS_APPLIED.md']:
 if (R/n).exists():shutil.copyfile(R/n,D/n)
with zipfile.ZipFile(O/f'{PREFIX}_17_VOICES_22m12s.zip','w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_22m12s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
assets=[*sorted(O.glob('*.mp3')),O/f'{PREFIX}_17_VOICES_22m12s.zip',*[O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']],R/f'{PREFIX}_TAI_LIEU_22m12s.zip',*[D/n for n in ['README.md','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','5_TIEU_DE_VA_THUMBNAIL.txt']]]
if (D/'PRODUCTION_STEPS_APPLIED.md').exists():assets.append(D/'PRODUCTION_STEPS_APPLIED.md')
for p in assets:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']))
man={'topic_id':91,'target_seconds':TARGET,'stage':'all17voices_and_documents_published','self_and_checksum_file_excluded':True,'assets':[{'name':a['name'],'bytes':a['size'],'sha256':a['digest'].removeprefix('sha256:')} for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt'] and not a['name'].endswith('.mp3')]}
p=O/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(man,ensure_ascii=False,indent=2));upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']));p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda a:a['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Chủ đề 91 — Tóc Saqqaq — Kịch bản,120 prompt và17 voice22:12','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('FULL17VOICE_DELIVERY_COMPLETE',flush=True)
