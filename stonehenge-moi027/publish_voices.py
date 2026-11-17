import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
from render_common import R,PROFILES,SLUG,TARGET,FRAMES,PREFIX
REPO='seotro95/seotro';TAG='stonehenge-moi-027-21m32s';BASE=f'https://github.com/{REPO}/releases/download/{TAG}/'
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
    assert report['status']=='passed' and report['target_seconds']==TARGET==1292 and report['decoded_frames_48000']==FRAMES==62016000
    assert report['voice_id']==profile['voice_id'] and report['gender']=='Male'
    assert report['minimum_word_coverage_ratio']>=.97 and report['word_metadata_pieces']>0
    assert report['script_sha256']==sha(R/'voice/scripts'/f'{locale}.json') and sha(source)==report['sha256'] and source.stat().st_size==report['bytes']
    assert len(report['cues'])==(130 if locale=='en-US' else 13)
    if locale=='en-US':assert report['word_metadata_exact_script_match'] and report['word_boundary_cue_split']
    assert decode(source)==FRAMES
    shutil.copyfile(source,O/source.name);reports[locale]=report;print('FULL_MP3_DECODE_VERIFIED',locale,FRAMES,flush=True)
assert set(reports)==set(PROFILES) and len({r['sha256'] for r in reports.values()})==16
profile_set=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
profile_set.update(topic_id='MOI-027',target_seconds=TARGET,note='All 16 previously saved male voice IDs retained, including Andrew, Nam Minh and Christoph. Every MP3 decoded to 1292 seconds. Independent native listening review pending.')
voices=[]
for profile in profile_set['profiles']:
    report=reports[profile['locale']]
    profile.update(duration_seconds=TARGET,delivery_filename=report['filename'],mp3_sha256=report['sha256'],alignment_granularity=report['timing_alignment'],narration_style_id=report['narration_style_id'])
    voices.append(dict(locale=profile['locale'],name=profile['name'],voice_id=profile['voice_id'],gender='Male',filename=report['filename'],seconds=TARGET,frames_at_48000=FRAMES,sha256=report['sha256'],bytes=report['bytes'],url=BASE+report['filename']))
manifest=dict(topic_id='MOI-027',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,main_video_locale='en-US',voices=voices)
qa=dict(status='passed',topic_id='MOI-027',voices=16,male_voices=16,all_decoded_seconds=TARGET,all_decoded_frames_48000=FRAMES,
        all_current_episode_ids_locked=True,previous_voice_ids_retained=16,voice_changes=[],vietnamese_voice_id='vi-VN-NamMinhNeural',unique_audio_hashes=16,
        english_cue_count=130,other_language_chapter_count=13,word_metadata_checked=True,english_word_boundary_split_checked=True,
        pitch_shift_applied=False,independent_native_listening_review=False,translated_voice_alignment='13 shared chapter boundaries, not word-by-word synchronization',
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
style=dict(id='science-documentary-expressive-v3-grouped-English-NamMinh-VI',profile_set_id=profile_set['profile_set_id'],main_voice='en-US-AndrewNeural',vietnamese_voice='vi-VN-NamMinhNeural',native_word_accents_db=1.2,max_word_accents_per_request=2,pitch_shift_applied=False,english='Grouped native requests with real word-boundary cue splits and pitch-preserving timing fit',other_languages='Saved male IDs, modest phrase/question rate changes, pitch-preserving chapter fit',loudness_target_lufs=-19,true_peak_target_db=-2,target_seconds=TARGET,native_listening_review=False)
dump(D/'NARRATION_STYLE_LOCKED.json',style)
docqa=json.loads((D/'DOCUMENT_QA.json').read_text());docqa.update(voices_generated=True,voice_count_verified=16,audio_sample_frames_verified=FRAMES,translated_chapter_alignment_verified=True,independent_native_listening_review=False);dump(D/'DOCUMENT_QA.json',docqa)
guide=(D/'HUONG_DAN_SU_DUNG.txt').read_text()+'\nKẾT QUẢ: Đã tạo và kiểm giải mã đủ 16 voice nam, cùng 21:32. Giữ nguyên cả 16 ID tập Upano. Bản Việt được viết lại toàn bộ; các bản khác chuyển ngữ từ nguồn tiếng Anh đã làm rõ thuật ngữ và rà các đoạn quan trọng. Phạm vi rà ghi tại TRANSLATION_REVIEW.json; chưa có biên tập/kiểm nghe bản ngữ độc lập.\n'
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8')
readme=f'''# MỚI-027 — Stonehenge — 140 prompt và 16 voice nam — 21:32

[Tải 16 voice ZIP]({BASE}{PREFIX}_16_VOICES_21m32s.zip) · [Tài liệu]({BASE}{PREFIX}_TAI_LIEU_21m32s.zip) · [14 TXT prompt ngoài trời]({BASE}{PREFIX}_PROMPT_NGOAI_TROI_14_TXT.zip) · [Kịch bản Anh]({BASE}KICH_BAN_EN_21m32s.txt) · [5 tiêu đề và thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Kịch bản nguyên bản 3.568 từ Anh, 130 mốc. Ba cuộc điều tra: nguồn đá, tuyến vận chuyển, kỹ thuật dựng. 140 prompt clip 10 giây chia 14 TXT × 10. Timeline dùng 137 cảnh: mở đầu 10 × 3 giây, thân 126 × 10 giây, cuối 2 giây. Prompt 138–140 dự phòng.

Đã tạo 16 MP3 nam riêng, mỗi tệp giải mã đúng 62.016.000 mẫu mono 48 kHz = 21:32. Giữ nguyên 16 ID đã lưu: Anh Andrew, Việt Nam Nam Minh, Đức Christoph. Dùng backend online đã khóa của Melo-Viet-Studio 1.3.1 qua GitHub Actions, không phải UI Windows hay model Melo đa ngôn ngữ cục bộ.

Anh căn 130 mốc; bản dịch căn 13 chương chung: 12 × 100 giây + 92 giây. Bản Việt được viết lại toàn bộ. Các bản khác dùng nguồn làm rõ thuật ngữ và được rà các đoạn quan trọng; bản Pháp sửa đoạn bị sót tiếng Anh. Phạm vi ghi trong TRANSLATION_REVIEW.json. Chưa có kiểm nghe hoặc biên tập bản ngữ độc lập. Cùng thời lượng không có nghĩa từng từ đồng bộ; SRT dịch theo chương cần chia nhỏ trước khi hiển thị.

140 cảnh ngoài trời: cảnh quan, khảo cổ, phục dựng thời Đá mới và mô hình minh họa. Không phòng thí nghiệm, trẻ em, lời nói hoặc âm thanh trong prompt. Nguồn đá không tự xác định tuyến đi; thử nghiệm không chứng minh một phương án dựng duy nhất. Nguồn và phạm vi đã đọc tại NGUON_KIEM_CHUNG.md. Hình tạo sinh không phải dữ liệu khảo sát thật hay bản ghi hành trình cổ.

Chưa tạo footage, thumbnail hoặc MP4. Phim chính khi dựng chỉ voice Anh, xóa âm clip, không nhạc/SFX.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
for v in voices:readme+=f"| {v['name']} | [{v['filename']}]({v['url']}) | 21:32 |\n"
for name in ['README.md','DOWNLOAD_LINKS.md']:(D/name).write_text(readme,encoding='utf-8')
(D/'LINK_TAI_VOICE.txt').write_text('MỚI-022 — 16 VOICE NAM — 21:32\n\n'+'\n\n'.join(v['name']+'\n'+v['url'] for v in voices)+'\n',encoding='utf-8')
with zipfile.ZipFile(O/f'{PREFIX}_16_VOICES_21m32s.zip','w',zipfile.ZIP_STORED) as z:
    for p in sorted(O.glob('*.mp3')):z.write(p,p.name)
    for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:z.write(O/n,n)
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_21m32s.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
files=sorted(O.glob('*.mp3'))+[O/f'{PREFIX}_16_VOICES_21m32s.zip',R/f'{PREFIX}_TAI_LIEU_21m32s.zip']
files += [O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']]
files += [D/n for n in ['README.md','DOWNLOAD_LINKS.md','LINK_TAI_VOICE.txt','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json','TRANSLATION_REVIEW.json','5_TIEU_DE_VA_THUMBNAIL.txt','VOICE_PROFILES_LOCKED_BASELINE.json']]
for p in files:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
record=dict(topic_id='MOI-027',stage='all16voices_and_documents_published',target_seconds=TARGET,assets=[dict(name=a['name'],bytes=a['size'],sha256=a['digest'].removeprefix('sha256:')) for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']])
p=O/'DOCUMENT_ASSET_MANIFEST.json';dump(p,record);upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
p=O/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda x:x['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--title','MỚI-022 Stonehenge — 140 prompt và 16 voice nam — 21:32','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('ROMAN_FULL16VOICE_DELIVERY_COMPLETE',flush=True)
