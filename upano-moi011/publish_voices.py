import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from render_common import R, PROFILES, SLUG, TARGET, FRAMES, PREFIX

REPO = 'seotro95/seotro'
TAG = 'upano-moi-011-20m22s'
BASE = f'https://github.com/{REPO}/releases/download/{TAG}/'
D = R / 'documents'
O = R / 'voice_delivery'
O.mkdir(exist_ok=True)

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def decode_samples(path):
    process = subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(path),
                                '-ar','48000','-ac','1','-f','s16le','-'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    size = 0
    while True:
        chunk = process.stdout.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
    error = process.stderr.read().decode('utf-8','replace')
    assert process.wait() == 0, error[-1000:]
    assert size % 2 == 0
    return size // 2

def upload(path):
    subprocess.run(['gh','release','upload',TAG,str(path),'--repo',REPO,'--clobber'],check=True)
    print('ASSET_PUBLISHED',path.name,flush=True)

reports = {}
for folder in Path('voice_artifacts').iterdir():
    report = folder / 'render_report.json'
    if not report.exists():
        continue
    data = json.loads(report.read_text())
    locale = data['locale']
    assert locale in PROFILES and locale not in reports
    profile = PROFILES[locale]
    source = folder / data['filename']
    assert source.name == f'{PREFIX}_{SLUG[locale]}.mp3'
    assert data['status'] == 'passed' and data['target_seconds'] == TARGET == 1222
    assert data['decoded_frames_48000'] == FRAMES == 58656000
    assert data['voice_id'] == profile['voice_id'] and data['gender'] == 'Male'
    assert data['minimum_word_coverage_ratio'] >= .97 and data['word_metadata_pieces'] > 0
    assert data['script_sha256'] == sha(R / 'voice/scripts' / (locale + '.json'))
    assert sha(source) == data['sha256'] and source.stat().st_size == data['bytes']
    if locale == 'en-US':
        assert data['word_metadata_exact_script_match'] and data['word_boundary_cue_split']
        assert len(data['cues']) == 123
    else:
        assert len(data['cues']) == 13
    assert decode_samples(source) == FRAMES
    shutil.copyfile(source,O/source.name)
    reports[locale] = data
    print('FULL_MP3_DECODE_VERIFIED',locale,FRAMES,flush=True)
assert set(reports) == set(PROFILES)
assert len({r['sha256'] for r in reports.values()}) == 16

profile_set = json.loads((R / 'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())
profile_set.update(topic_id='MOI-011',target_seconds=TARGET,
                   note='16 saved male identities retained; Vietnamese is actual NamMinhNeural; all MP3 decoded to1222seconds. Independent native listening review remains pending.')
voices = []
for profile in profile_set['profiles']:
    data = reports[profile['locale']]
    profile.update(duration_seconds=TARGET,delivery_filename=data['filename'],mp3_sha256=data['sha256'],
                   alignment_granularity=data['timing_alignment'],narration_style_id=data['narration_style_id'])
    voices.append(dict(locale=profile['locale'],name=profile['name'],voice_id=profile['voice_id'],gender='Male',
                       filename=data['filename'],seconds=TARGET,frames_at_48000=FRAMES,
                       sha256=data['sha256'],bytes=data['bytes'],url=BASE+data['filename']))
manifest = dict(topic_id='MOI-011',catalogue_id='new-100-topics-20261116',target_seconds=TARGET,
                main_video_locale='en-US',voices=voices)
qa = dict(status='passed',topic_id='MOI-011',voices=16,male_voices=16,
          all_decoded_seconds=TARGET,all_decoded_frames_48000=FRAMES,
          all_saved_voice_ids_retained=True,vietnamese_voice_id='vi-VN-NamMinhNeural',
          unique_audio_hashes=16,english_cue_count=123,other_language_chapter_count=13,
          word_metadata_checked=True,english_word_boundary_split_checked=True,
          pitch_shift_applied=False,independent_native_listening_review=False,
          translated_voice_alignment='Shared chapter boundaries, not word-by-word synchronization',
          reports={k:dict(voice_id=v['voice_id'],filename=v['filename'],decoded_seconds=v['decoded_seconds'],
                          min_tempo=min(c['tempo'] for c in v['cues']),
                          max_tempo=max(c['tempo'] for c in v['cues']),
                          word_accents=v['word_accents']) for k,v in reports.items()})
for name,value in [('AUDIO_MANIFEST.json',manifest),('VOICE_PROFILES_LOCKED.json',profile_set),('VOICE_RELEASE_QA.json',qa)]:
    (O/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
(D/'REPORTS').mkdir(exist_ok=True)
for locale,data in reports.items():
    (D/'REPORTS'/f'{locale}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for locale in PROFILES:
    if locale == 'en-US':
        continue
    rows = json.loads((R/'voice/scripts'/f'{locale}.json').read_text())
    (D/f'{locale}.txt').write_text('\n\n'.join(x['voice'] for x in rows)+'\n',encoding='utf-8')
    def timestamp(value):
        return f'{value//3600:02}:{value%3600//60:02}:{value%60:02},000'
    (D/f'{locale}_chapters.srt').write_text('\n\n'.join(
        f"{row['id']}\n{timestamp(row['start'])} --> {timestamp(row['end'])}\n{row['voice']}" for row in rows)+'\n',encoding='utf-8')
for name in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:
    shutil.copyfile(O/name,D/name)
for name in ['TRANSLATION_REVIEW.json','VOICE_INPUT_QA.json','LOCALIZATION_SOURCE_CHAPTERS.json']:
    shutil.copyfile(R/name,D/name)
style = dict(id='science-documentary-expressive-v3-grouped-English-NamMinh-VI',
             profile_set_id=profile_set['profile_set_id'],main_voice='en-US-AndrewNeural',
             vietnamese_voice='vi-VN-NamMinhNeural',native_word_accents_db=1.2,
             max_word_accents_per_request=2,pitch_shift_applied=False,
             english='Grouped native requests; real word-boundary cue splits; pitch-preserving cue timing fit',
             other_languages='Saved male voice IDs; small phrase/question rate changes; pitch-preserving chapter timing fit',
             loudness_target_lufs=-19,true_peak_target_db=-2,target_seconds=TARGET,
             native_listening_review=False)
(D/'NARRATION_STYLE_LOCKED.json').write_text(json.dumps(style,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
docqa = json.loads((D/'DOCUMENT_QA.json').read_text())
docqa.update(voices_generated=True,voice_count_verified=16,audio_sample_frames_verified=FRAMES,
             translated_chapter_alignment_verified=True,independent_native_listening_review=False)
(D/'DOCUMENT_QA.json').write_text(json.dumps(docqa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
guide = (D/'HUONG_DAN_SU_DUNG.txt').read_text()
guide += '''

KẾT QUẢ VOICE ĐÃ HOÀN THÀNH

Đã phát hành 16 MP3, toàn bộ giọng nam, mỗi bản giải mã đúng 1.222 giây. Giữ đúng ID đã lưu, tiếng Việt Nam Minh. Không có giọng H'mông trong danh sách yêu cầu của tập này.

Bản Việt được viết lại toàn bộ, sửa thuật ngữ và nhịp kể. Các bản khác được chuyển ngữ từ nguồn tiếng Anh đã làm rõ thuật ngữ, giữ ý chính, thứ tự chủ đề và giới hạn khoa học theo từng chương; chuyển ý lặp được rút gọn. Đã sửa thuật ngữ, niên đại, đoạn kết và các đoạn tiếng Anh lọt trong bản dịch. Chưa có kiểm nghe/biên tập bản ngữ độc lập.

Cùng độ dài và cùng mốc chương không có nghĩa khớp từng từ hoặc từng cảnh 10 giây ở mọi ngôn ngữ. Phim chính dùng voice tiếng Anh.
'''
(D/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8')
steps = (D/'PRODUCTION_STEPS_APPLIED.md').read_text()
steps += '\n\nCập nhật: đã tạo và giải mã kiểm đủ 16 MP3, đúng ID và cùng 20:22; chưa tạo footage/MP4. Bản dịch theo chương đã rà bối cảnh ở phạm vi ghi trong TRANSLATION_REVIEW.json, chưa kiểm nghe bản ngữ độc lập.\n'
(D/'PRODUCTION_STEPS_APPLIED.md').write_text(steps,encoding='utf-8')
readme = f'''# MỚI-011 — Upano — Kịch bản, 130 prompt và 16 voice 20:22

[Tải toàn bộ 16 voice]({BASE}{PREFIX}_16_VOICES_20m22s.zip) · [Tải tài liệu và 13 TXT prompt]({BASE}{PREFIX}_TAI_LIEU_20m22s.zip) · [5 tiêu đề và thumbnail]({BASE}5_TIEU_DE_VA_THUMBNAIL.txt)

Tập MỚI-011 của bộ đề tài mới ngày 16/11/2026, lưu riêng với danh sách cũ. Kịch bản tiếng Anh nguyên bản 3.229 từ, 123 mốc lời. Có 130 prompt clip 10 giây, chia 13 TXT × 10 prompt. Timeline có 10 cảnh × 3 giây ở mở đầu, 119 cảnh × 10 giây và cảnh cuối 2 giây, tổng 1.222 giây.

Đã tạo 16 MP3 riêng, toàn bộ nam. Từng tệp đã được giải mã đủ 58.656.000 mẫu mono 48 kHz, tức 20:22. Giữ đúng các ID giọng đã lưu; Việt Nam dùng NamMinhNeural thật. Sử dụng thành phần online đã khóa mã nguồn của Melo-Viet-Studio 1.3.1 qua GitHub Actions, không tự nhận chạy giao diện Windows.

Anh căn 123 mốc lời; 15 bản địa phương hóa căn 13 chương chung: 12 × 100 giây + 22 giây cuối. Bản Việt viết lại toàn bộ. Các bản khác dịch từ nguồn đã làm rõ thuật ngữ và rút các chuyển ý lặp, rồi sửa thuật ngữ, niên đại, đoạn kết và phần tiếng Anh lọt. Chưa có kiểm nghe/biên tập bản ngữ độc lập. Cùng thời lượng không có nghĩa từng từ trùng thời điểm. SRT dịch theo chương cần chia nhỏ trước khi hiển thị.

Hình tạo sinh, point cloud, mặt cắt và mô hình chỉ minh họa; không phải dữ liệu đo hoặc tư liệu Upano thật. Mỗi prompt cấm trẻ em, lời nói và âm thanh. Không kim tự tháp đá, thành phố vàng hoặc một vụ phun trào kết thúc đã được khẳng định. Giữ rõ giới hạn niên đại, dân số và tính đồng thời.

Chưa có footage hoặc MP4 tập Upano. Phim chính khi dựng chỉ có voice tiếng Anh, xóa âm clip, không nhạc/SFX.

| Quốc gia / ngôn ngữ | Tải MP3 | Thời lượng |
|---|---|---|
'''
for voice in voices:
    readme += f"| {voice['name']} | [{voice['filename']}]({voice['url']}) | 20:22 |\n"
(D/'README.md').write_text(readme,encoding='utf-8')
(D/'DOWNLOAD_LINKS.md').write_text(readme,encoding='utf-8')
(D/'LINK_TAI_VOICE.txt').write_text('MỚI-011 — 16 VOICE NAM — 20:22\n\n'+'\n\n'.join(
    f"{v['name']}\n{v['url']}" for v in voices)+'\n',encoding='utf-8')
with zipfile.ZipFile(O/f'{PREFIX}_16_VOICES_20m22s.zip','w',zipfile.ZIP_STORED) as archive:
    for path in sorted(O.glob('*.mp3')):
        archive.write(path,path.name)
    for name in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']:
        archive.write(O/name,name)
with zipfile.ZipFile(R/f'{PREFIX}_TAI_LIEU_20m22s.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(D.rglob('*')):
        if path.is_file():
            archive.write(path,path.relative_to(D))
assets = sorted(O.glob('*.mp3')) + [O/f'{PREFIX}_16_VOICES_20m22s.zip',R/f'{PREFIX}_TAI_LIEU_20m22s.zip']
assets += [O/n for n in ['AUDIO_MANIFEST.json','VOICE_PROFILES_LOCKED.json','VOICE_RELEASE_QA.json']]
assets += [D/n for n in ['README.md','DOCUMENT_QA.json','HUONG_DAN_SU_DUNG.txt','NARRATION_STYLE_LOCKED.json',
                         'TRANSLATION_REVIEW.json','5_TIEU_DE_VA_THUMBNAIL.txt','DOWNLOAD_LINKS.md',
                         'LINK_TAI_VOICE.txt','PRODUCTION_STEPS_APPLIED.md']]
for path in assets:
    upload(path)
release = json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
all_assets = [a for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']]
record = dict(topic_id='MOI-011',stage='all16voices_and_documents_published',target_seconds=TARGET,
              assets=[dict(name=a['name'],bytes=a['size'],sha256=a['digest'].removeprefix('sha256:')) for a in all_assets])
path = O/'DOCUMENT_ASSET_MANIFEST.json'
path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
upload(path)
release = json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
path = O/'SHA256SUMS.txt'
path.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda x:x['name']) if a['name']!='SHA256SUMS.txt'))
upload(path)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,
                '--title','MỚI-011 Upano — 130 prompt và 16 voice nam — 20:22',
                '--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('UPANO_FULL16VOICE_DELIVERY_COMPLETE',flush=True)
