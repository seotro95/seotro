import hashlib,json,shutil,subprocess,sys,wave,zipfile
from pathlib import Path
R=Path(__file__).parent;repo='seotro95/seotro';tag='land-bridges-video-38-22m32s';D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
sys.path.insert(0,str(R));from render_episode import PROFILES,SLUG,TARGET,FRAMES,PREFIX
reports={};artifacts=Path('voice_artifacts')
for folder in artifacts.iterdir():
 p=folder/'render_report.json'
 if not p.exists():continue
 j=json.loads(p.read_text());locale=j['locale'];assert locale not in reports
 source=folder/j['filename'];assert source.name==f'{PREFIX}_{SLUG[locale]}.mp3'
 assert j['status']=='passed' and j['decoded_frames_48000']==FRAMES and j['target_seconds']==TARGET
 assert j['voice_id']==PROFILES[locale]['voice_id'] and j['gender']==PROFILES[locale]['gender']
 assert hashlib.file_digest(source.open('rb'),'sha256').hexdigest()==j['sha256']
 if locale!='mww':assert j['minimum_word_coverage_ratio']>=.97 and j['word_metadata_pieces']>0
 else:assert j['reference_sha256']==PROFILES[locale]['reference_sha256']
 decoded=O/'verify.wav';subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(decoded)],check=True)
 with wave.open(str(decoded)) as w:assert w.getnframes()==FRAMES and w.getframerate()==48000
 decoded.unlink();dest=O/source.name;shutil.copyfile(source,dest);reports[locale]=j
 reportdir=D/'REPORTS';reportdir.mkdir(exist_ok=True);(reportdir/f'{locale}.json').write_text(json.dumps(j,ensure_ascii=False,indent=2))
 print('DECODED_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==17
assert sum(r['gender']=='Male' for r in reports.values())==16
voices=[];profiles=json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text());profiles['topic_id']=38;profiles['target_seconds']=TARGET
base=f'https://github.com/{repo}/releases/download/{tag}/'
for p in profiles['profiles']:
 j=reports[p['locale']];p.update(duration_seconds=TARGET,delivery_filename=j['filename'],mp3_sha256=j['sha256'],alignment_granularity=j['timing_alignment'],narration_style_id='science-documentary-expressive-v1')
 voices.append({'locale':p['locale'],'name':p['name'] if p['locale']!='mww' else "H'mông Trắng (nữ)",'voice_id':p['voice_id'],'gender':p['gender'],'filename':j['filename'],'seconds':TARGET,'frames_at_48000':FRAMES,'sha256':j['sha256'],'bytes':j['bytes'],'url':base+j['filename']})
manifest={'topic_id':38,'target_seconds':TARGET,'main_video_locale':'en-US','voices':voices}
(O/'AUDIO_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(O/'VOICE_PROFILES_LOCKED.json').write_text(json.dumps(profiles,ensure_ascii=False,indent=2))
qa={'status':'passed','topic_id':38,'voices':17,'male_voices':16,'female_voice':'hmong-female-3','all_decoded_seconds':TARGET,'all_decoded_frames_48000':FRAMES,'all_voice_ids_match_locked_profiles':True,'native_hmong_reference_matches':True,'unique_audio_hashes':17,'pitch_shift_applied':False,'english_cue_count':136,'other_language_chapter_count':14,'online_complete_word_metadata_checked':True,'independent_native_listening_review':False,'white_hmong_dialect_independently_verified':False,'reports':{k:{'voice_id':v['voice_id'],'filename':v['filename'],'decoded_seconds':v['decoded_seconds'],'min_tempo':min(x['tempo'] for x in v['cues']),'max_tempo':max(x['tempo'] for x in v['cues']),'word_accents':v['word_accents']} for k,v in reports.items()}}
(O/'VOICE_RELEASE_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
# Recreate localized country texts and chapter markers from the actual recorded scripts.
for locale in PROFILES:
 if locale=='en-US':continue
 rows=json.loads((R/'voice/scripts'/f'{locale}.json').read_text());(D/f'{locale}.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n')
 def ts(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
 (D/f'{locale}_chapters.srt').write_text('\n\n'.join(f"{x['id']}\n{ts(x['start'])} --> {ts(x['end'])}\n{x['voice']}" for x in rows)+'\n')
for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:shutil.copyfile(O/n,D/n)
style={'narration_style_id':'science-documentary-expressive-v1','voice_ids_unchanged':True,'native_pitch_unchanged':True,'online_phrase_rate':'English -8% base, localized -1% base; small question/reflective variations; exact final duration fit with pitch-preserving atempo','online_word_accents':'At most2 perrequest;1.2dB with30ms ramps','native_hmong':'female3reference,clear-v1,speed0.98–1.02,no pitch shift','output_loudness_target_lufs':-19,'output_true_peak_target_db':-2,'timing_policy':'136Englishcues;14sharedchapters in translations; all exactly1352seconds when decoded'}
(D/'NARRATION_STYLE_LOCKED.json').write_text(json.dumps(style,ensure_ascii=False,indent=2))
docqa=json.loads((D/'DOCUMENT_QA.json').read_text());docqa.update(voices_generated=True,voice_count_verified=17,audio_sample_frames_verified=FRAMES);(D/'DOCUMENT_QA.json').write_text(json.dumps(docqa,indent=2))
readme=f'''# Chủ đề 38 — Cầu đất qua các chu kỳ băng hà — 22:32

[Kịch bản,12TXTprompt vàtimeline]({base}LAND_BRIDGES_38_TAI_LIEU_22m32s.zip) · [17voice trong mộtZIP]({base}LAND_BRIDGES_38_17_VOICES_22m32s.zip)

Kịch bản Anh gốc When the Sea Was Land: Earth's Vanishing Bridges,3.581từ.136mốc lời =135×10giây+2giây.120prompt mới trong12TXT,10prompt/TXT.16mốc dùng lại có đánh dấu trong timeline. Prompt tạo clip10giây, im lặng, không có trẻ em hoặc thiếu niên, kể cả nền, ảnh, màn hình vàphản chiếu. Bộ này chưa tạofootage hoặcMP4hoàn chỉnh.

Đã tạo17voice riêng:16nam vàH'môngnữfemale-3. Tênfiletheoquốc gia; tiếng Anh làbản chính. Mọi fileđãgiải mã kiểm tra đúng1.352giây,64.896.000mẫu ở48kHz. Tiếng Anh có136mốc; các bản dịch giữ14mốc chương, không đồng nghĩa từng từ hoặc từng10giây trùng nhau. Không đổi voiceIDhoặc pitch. Nhấn nhá bằng nhịp đọc, câu hỏi, khoảng nghỉ vànhấn từ nhẹ; báo cáo ghi tempođã dùng.

Các bản dịch đãsửa thuật ngữ địa khoa học vàcác ý chính từ bản nguồn rõnghĩa hơn; phần mở/kết Việt vàtoàn bộ14chươngHmongđược viết lại. Đây không phải chứng nhận biên tập/nghe bản ngữ. Riêng H'môngdùngtoolnative1.6.6 vàtham chiếu nữđãkhóa, nhưng phương ngữH'môngTrắng chưađược người bản ngữxác nhận độc lập.

| Giọng | TảiMP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 22:32 |\n"
readme+='\nKhông thêm nhạc hoặc tiếng hiệu ứng vào voice. Khi có clip, dùng timelineđểdựngkhớp bản Anh; đoạn cuối chỉ lấy2giây. Bản đồvànhãn khoa học cầnkiểm trước khi thêm trong edit.\n'
(D/'README.md').write_text(readme)
with zipfile.ZipFile(O/'LAND_BRIDGES_38_17_VOICES_22m32s.zip','w',zipfile.ZIP_STORED) as z:
 for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
 for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/'LAND_BRIDGES_38_TAI_LIEU_22m32s.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
for source in Path('preflight_artifact').rglob('LAND_BRIDGES_38_EN_PREVIEW_30s.mp3'):shutil.copyfile(source,O/source.name)
assets=[*sorted(O.glob('*.mp3')),O/'LAND_BRIDGES_38_17_VOICES_22m32s.zip',O/'AUDIO_MANIFEST.json',O/'VOICE_PROFILES_LOCKED.json',O/'VOICE_RELEASE_QA.json',R/'LAND_BRIDGES_38_TAI_LIEU_22m32s.zip',D/'README.md',D/'DOCUMENT_QA.json',D/'NARRATION_STYLE_LOCKED.json',D/'TRANSLATION_REVIEW.json']
(O/'SHA256SUMS.txt').write_text(''.join(hashlib.file_digest(p.open('rb'),'sha256').hexdigest()+'  '+p.name+'\n' for p in assets));assets.append(O/'SHA256SUMS.txt')
for p in assets:
 subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True);print('VOICE_ASSET_PUBLISHED',p.name,flush=True)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--title','Chủ đề38 — Cầu đất — Kịch bản,120prompt và17voice22:32','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print(json.dumps({'VOICE_RELEASE_COMPLETE':True,'target_seconds':TARGET,'voice_count':17,'release_tag':tag}),flush=True)
