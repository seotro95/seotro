import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
REPO='seotro95/seotro';TAG='qanat-moi-030-22m42s';BASE=f'https://github.com/{REPO}/releases/download/{TAG}/'
D=R/'documents';O=R/'voice_delivery';O.mkdir(exist_ok=True)
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def decode(p):
    process=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(p),'-ar','48000','-ac','1','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    n=0
    while block:=process.stdout.read(1024*1024):n+=len(block)
    error=process.stderr.read().decode('utf-8','replace');assert process.wait()==0,error[-1000:]
    assert n==FRAMES*2,(p.name,n);return n//2
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def upload(p):
    subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
    print('ASSET_PUBLISHED',p.name,flush=True)
reports={}
for folder in Path('voice_artifacts').iterdir():
    p=folder/'render_report.json'
    if not p.exists():continue
    report=json.loads(p.read_text());locale=report['locale'];assert locale in PROFILES and locale not in reports
    source=folder/report['filename'];profile=PROFILES[locale]
    assert source.name==f'{PREFIX}_{SLUG[locale]}.mp3'
    assert report['status']=='passed' and report['target_seconds']==TARGET==1362 and report['decoded_frames_48000']==FRAMES==65376000
    assert report['voice_id']==profile['voice_id'] and report['gender']=='Male'
    assert report['minimum_word_coverage_ratio']>=.97 and report['word_metadata_pieces']>0
    assert report['script_sha256']==sha(R/'voice/scripts'/f'{locale}.json') and sha(source)==report['sha256'] and source.stat().st_size==report['bytes']
    assert len(report['cues'])==(137 if locale=='en-US' else 14)
    if locale=='en-US':assert report['word_metadata_exact_script_match'] and report['word_boundary_cue_split']
    assert decode(source)==FRAMES
    shutil.copyfile(source,O/source.name);reports[locale]=report;print('FULL_MP3_DECODE_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==16
profile_set=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
profile_set.update(topic_id='MOI-030',target_seconds=TARGET,note='All 16 previously saved male voice IDs retained, including Andrew, Nam Minh and Christoph. Every MP3 decoded to 1362 seconds. Independent native listening review pending.')
voices=[]
for profile in profile_set['profiles']:
    report=reports[profile['locale']]
    profile.update(duration_seconds=TARGET,delivery_filename=report['filename'],mp3_sha256=report['sha256'],alignment_granularity=report['timing_alignment'],narration_style_id=report['narration_style_id'])
    voices.append(dict(locale=profile['locale'],name=profile['name'],voice_id=profile['voice_id'],gender='Male',filename=report['filename'],seconds=TARGET,frames_at_48000=FRAMES,sha256=report['sha256'],bytes=report['bytes'],url=BASE+report['filename']))
manifest=dict(topic_id='MOI-030',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,main_video_locale='en-US',voices=voices)
qa=dict(status='passed',topic_id='MOI-030',voices=16,male_voices=16,all_decoded_seconds=TARGET,all_decoded_frames_48000=FRAMES,
        all_current_episode_ids_locked=True,previous_voice_ids_retained=16,voice_changes=[],vietnamese_voice_id='vi-VN-NamMinhNeural',unique_audio_hashes=16,
        english_cue_count=137,other_language_chapter_count=14,word_metadata_checked=True,english_word_boundary_split_checked=True,
        pitch_shift_applied=False,independent_native_listening_review=False,translated_voice_alignment='14 shared chapter boundaries, not word-by-word synchronization',
        reports={k:dict(voice_id=v['voice_id'],filename=v['filename'],decoded_seconds=v['decoded_seconds'],min_tempo=min(c['tempo'] for c in v['cues']),max_tempo=max(c['tempo'] for c in v['cues']),word_accents=v['word_accents']) for k,v in reports.items()})
for name,j in [('AUDIO_MANIFEST.json',manifest),('VOICE_PROFILES_LOCKED.json',profile_set),('VOICE_RELEASE_QA.json',qa)]:dump(O/name,j)
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
(D/'REPORTS').mkdir(exist_ok=True)
def stamp(t):return f'{t//3600:02}:{t%3600//60:02}:{t%60:02},000'
for locale,report in reports.items():
    dump(D/'REPORTS'/f'{locale}.json',report)
    if locale=='en-US':continue
    rows=json.loads((R/'voice/scripts'/f'{locale}.json').read_text())
    (D/f'{locale}.txt').write_text('\n\n'.join(r['voice'] for r in rows)+'\n',encoding='utf-8')
    (D/f'{locale}_chapters.srt').write_text('\n\n'.join(f"{r['id']}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['voice']}" for r in rows)+'\n',encoding='utf-8')
for name in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:shutil.copyfile(O/name,D/name)
for name in ['TRANSLATION_REVIEW.json','VOICE_INPUT_QA.json','LOCALIZATION_SOURCE_CHAPTERS.json']:shutil.copyfile(R/name,D/name)
style=dict(id='science-documentary-brisk-v4-Qanat-NamMinh',profile_set_id=profile_set['profile_set_id'],main_voice='en-US-AndrewNeural',vietnamese_voice='vi-VN-NamMinhNeural',native_word_accents_db=1.2,max_word_accents_per_request=2,pitch_shift_applied=False,english='Grouped native requests with real word-boundary cue splits and pitch-preserving timing fit',other_languages='Saved male IDs, modest phrase/question rate changes, pitch-preserving chapter fit',loudness_target_lufs=-19,true_peak_target_db=-2,target_seconds=TARGET,native_listening_review=False,native_english_request_rate='+2%',main_english_wpm=179.339,main_english_density_faster_percent=8.23)
dump(D/'NARRATION_STYLE_LOCKED.json',style)
docqa=json.loads((D/'DOCUMENT_QA.json').read_text());docqa.update(voices_generated=True,voice_count_verified=16,audio_sample_frames_verified=FRAMES,translated_chapter_alignment_verified=True,independent_native_listening_review=False,native_english_request_rate='+2%',main_english_wpm=179.339,main_english_density_faster_percent=8.23);dump(D/'DOCUMENT_QA.json',docqa)
guide=(D/'HUONG_DAN_SU_DUNG.txt').read_text()+'\nKẾT QUẢ: Đã tạo và kiểm giải mã đủ 16 voice nam, cùng 22:42. Giữ nguyên cả 16 ID đã lưu. Bản Việt được viết lại toàn bộ; các bản khác chuyển ngữ từ nguồn tiếng Anh đã làm rõ thuật ngữ và rà các đoạn quan trọng. Phạm vi rà ghi tại TRANSLATION_REVIEW.json; chưa có biên tập/kiểm nghe bản ngữ độc lập.\n'
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8')
readme=f'''# MỚI-030 — Qanat — 150 prompt và 16 voice nam — 22:42

[Tải 16 voice ZIP]({BASE}{PREFIX}_16_VOICES_22m42s.zip) · [Tài liệu]({BASE}{PREFIX}_TAI_LIEU_22m42s.zip) · [15 TXT prompt]({BASE}{PREFIX}_PROMPT_15_TXT.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_22m42s.txt) · [5 tiêu đề/thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản Anh nguyên bản 4.071 từ, 137 mốc, khoảng 179 từ/phút, nhanh hơn khoảng 8% mật độ từ/phút của Stonehenge trước. Giữ đúng 22:42 bằng lượng lời, nhịp và khoảng nghỉ phù hợp; không tăng tốc rồi lấp im lặng. Giữ pitch và nhấn từ vừa phải.

150 prompt trong 15 TXT × 10, mỗi clip 10 giây. Timeline 144 cảnh: 10 × 3 giây mở đầu, 133 × 10 giây thân, 2 giây cuối. Prompt 145–150 là 6 cảnh dự phòng. 146 cảnh ngoài trời, 4 gallery ngầm, không lab hoặc trẻ em; mọi prompt ghi không âm thanh, không lời nói.

Đã tạo 16 MP3 nam riêng, mỗi tệp giải mã đúng 65.376.000 mẫu mono 48 kHz = 22:42. Giữ nguyên 16 ID đã lưu: Anh Andrew, Việt Nam Nam Minh, Đức Christoph. Dùng backend online đã khóa của Melo-Viet-Studio 1.3.1; không phải UI Windows hay model Melo đa ngôn ngữ cục bộ.

Anh căn 137 mốc; bản dịch căn 14 chương: 13 × 100 giây + 62 giây. Bản Việt viết lại toàn bộ, bản khác chuyển ngữ từ nguồn làm rõ thuật ngữ và rà các đoạn quan trọng. Phạm vi tại TRANSLATION_REVIEW.json. Chưa kiểm nghe hoặc biên tập bản ngữ độc lập. Cùng thời lượng không có nghĩa từng từ đồng bộ; SRT dịch theo chương cần chia nhỏ trước khi hiển thị.

Cơ chế được kể theo nguồn–độ dốc–cửa ra–ruộng–người dùng. Không đồng nhất niên đại/nguồn gốc mọi qanat; không hứa nước vô hạn, miễn bảo trì hay an toàn uống chỉ từ hình nước trong. Nguồn và phạm vi đọc tại NGUON_KIEM_CHUNG.md. Mặt cắt, mô hình và phục dựng chỉ minh họa, không dữ liệu khảo sát thật.

Chưa tạo footage, ảnh thumbnail hoặc MP4. Khi dựng phim chính chỉ voice Anh, xóa âm clip, không nhạc/SFX.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 22:42 |\n"
for name in ['README.md','DOWNLOAD_LINKS.md']:(D/name).write_text(readme,encoding='utf-8')
(D/'LINK_TAI_VOICE.txt').write_text('MỚI-022 — 16 VOICE NAM — 22:42\n\n'+'\n\n'.join(v['name']+'\n'+v['url'] for v in voices)+'\n',encoding='utf-8')
with zipfile.ZipFile(O/f'{PREFIX}_16_VOICES_22m42s.zip','w',zipfile.ZIP_STORED) as z:
    for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
    for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_22m42s.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
files=sorted(O.glob('*.mp3'))+[O/f'{PREFIX}_16_VOICES_22m42s.zip',R/f'{PREFIX}_TAI_LIEU_22m42s.zip']
files += [O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']]
files += [D/n for n in ['README.md','DOWNLOAD_LINKS.md','LINK_TAI_VOICE.txt','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','5_TIEU_DE_VA_THUMBNAIL.txt','VOICE_PROFILES_LOCKED_BASELINE.json']]
for p in files:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
record=dict(topic_id='MOI-030',stage='all16voices_and_documents_published',target_seconds=TARGET,assets=[dict(name=a['name'],bytes=a['size'],sha256=a['digest'].removeprefix('sha256:')) for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']])
p=O/'DOCUMENT_ASSET_MANIFEST.json';dump(p,record);upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda x:x['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--title','MỚI-022 Qanat — 140 prompt và 16 voice nam — 22:42','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('ROMAN_FULL16VOICE_DELIVERY_COMPLETE',flush=True)

