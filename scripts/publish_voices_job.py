import hashlib,json,os,re,shutil,subprocess,time,urllib.error,urllib.request,zipfile
from pathlib import Path
REPO=os.environ['GITHUB_REPOSITORY'];BRANCH='codex/malta-voice-build-20261110'
TAG='malta-video-03-20min';DOCS='ca4e72ec2d5e0db299a203d8e4ce6f52c939dc73'
OUT=Path('delivery');OUT.mkdir(exist_ok=True)
profiles=json.loads(Path('input/BASELINE_VOICE_PROFILES.json').read_text());expected={p['locale']:p for p in profiles['profiles']}
reports={}
for p in Path('artifacts').rglob('render_report.json'):
    j=json.loads(p.read_text());locale=j['locale'];assert locale not in reports
    assert j['audio_seconds']==1200 and j['duration_verified'] and j['mp3_decoded_duration']['verified']
    assert j['voice_id']==expected[locale]['voice_id'] and j['gender']=='Male'
    audio=p.parent/j['mp3_file'];assert hashlib.sha256(audio.read_bytes()).hexdigest()==j['mp3_sha256']
    reports[locale]={'report':j,'audio':audio,'srt':p.parent/'subtitles.srt'}
assert len(reports)==16,list(reports)

# The native Hmong engine is run in the original prepared cloud workspace.
# Resolve the latest isolated build branch to an immutable commit before reading it.
native=None
for attempt in range(120):
    sha=subprocess.check_output(['gh','api',f'repos/{REPO}/git/ref/heads/{BRANCH}','--jq','.object.sha'],text=True).strip()
    assert re.fullmatch('[a-f0-9]{40}',sha)
    base=f'https://raw.githubusercontent.com/{REPO}/{sha}/native/'
    try:
        native=json.load(urllib.request.urlopen(base+'manifest.json',timeout=60));break
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        print('Waiting for the verified native Hmong output',attempt+1,flush=True);time.sleep(30)
assert native,'Native Hmong output not ready; retain all completed online artifacts.'
assert native['voice_id']=='hmong-female-3' and native['reference_sha256']==expected['mww']['reference_sha256']
for name in ['MALTA_03_mww_female.mp3','render_report.json','subtitles.srt']:
    data=urllib.request.urlopen(base+name,timeout=120).read();(OUT/name).write_bytes(data)
hmong=json.loads((OUT/'render_report.json').read_text());audio=OUT/hmong['mp3_file']
assert hashlib.sha256(audio.read_bytes()).hexdigest()==hmong['mp3_sha256']==native['mp3_sha256']
assert hmong['audio_seconds']==1200 and hmong['mp3_decoded_duration']['verified'] and hmong['gender']=='Female'
reports['mww']={'report':hmong,'audio':audio,'srt':OUT/'subtitles.srt'}

(OUT/'SCRIPTS').mkdir(exist_ok=True);(OUT/'TIMING').mkdir(exist_ok=True);(OUT/'REPORTS').mkdir(exist_ok=True)
locked=[];manifest=[]
for locale,p in expected.items():
    record=reports[locale];r=record['report'];dest=OUT/r['mp3_file']
    if record['audio'].resolve()!=dest.resolve():shutil.copy(record['audio'],dest)
    shutil.copy(record['srt'],OUT/'TIMING'/f'{locale}.srt')
    (OUT/'REPORTS'/f'{locale}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    rows=json.loads(Path(f'input/scripts/{locale}.json').read_text())
    (OUT/'SCRIPTS'/f'{locale}.txt').write_text('\n\n'.join(x['voice'] for x in rows))
    profile={k:v for k,v in p.items() if k not in ['duration_seconds','max_used_post_tempo','mp3_reference_sha256','translation_review_status','alignment_granularity']}
    profile.update(narration_style_id='science-documentary-expressive-v1',base_rate=p['rate'],rate='phrase-dependent; see NARRATION_STYLE_LOCKED.json',duration_seconds=1200,mp3_sha256=r['mp3_sha256'],max_used_post_tempo=r['max_used_post_tempo'],
                   alignment_granularity=r['alignment_granularity'],translation_review_status=r['translation_review_status'])
    locked.append(profile);manifest.append({'locale':locale,'name':p['name'],'gender':p['gender'],'voice_id':p['voice_id'],
                                          'filename':r['mp3_file'],'bytes':r['mp3_bytes'],'sha256':r['mp3_sha256'],'seconds':1200})
assert len(manifest)==17 and len({x['sha256'] for x in manifest})==17
assert sum(x['gender']=='Male' for x in manifest)==16
(OUT/'VOICE_PROFILES_LOCKED.json').write_text(json.dumps({'profile_set_id':profiles['profile_set_id'],'topic_id':3,'target_seconds':1200,'profiles':locked,'note':'Same IDs and native female-3 reference as topic 1; timing is newly measured. Provider models may evolve. White Hmong dialect independently unverified.'},ensure_ascii=False,indent=2))
(OUT/'AUDIO_MANIFEST.json').write_text(json.dumps({'topic':3,'seconds_per_voice':1200,'sample_frames_at_48000':57600000,'voice_count':17,'voices':manifest,'native_review_pending':True},ensure_ascii=False,indent=2))
base_url=f'https://github.com/{REPO}/releases/download/{TAG}/'
readme='# Malta — 17 giọng đọc, mỗi bản 20 phút\n\nVideo chính chỉ dùng voice tiếng Anh. Các ngôn ngữ khác là audio riêng.\n\n| Ngôn ngữ | Giọng | Tải MP3 |\n|---|---|---|\n'
for row in manifest:readme+=f"| {row['name']} | {row['voice_id']} | [Tải MP3]({base_url}{row['filename']}) |\n"
readme+=f'\n[Tải một ZIP đủ 17 giọng]({base_url}MALTA_03_17_VOICES_20m.zip)\n\n'
readme+='Mỗi bản đã được đo đúng 1.200 giây sau giải mã, tương ứng 57.600.000 mẫu ở 48 kHz. Tiếng Anh căn 120 ô 10 giây; bản dịch căn 12 chương 100 giây. Đây không phải căn từng từ giữa các ngôn ngữ. Giữ 16 giọng nam và Hmong nữ 3, không đổi ID của tập 1.\n\n'
readme+='Bản dịch là bản nháp đã kiểm tra thuật ngữ và mốc quan trọng, vẫn cần người bản ngữ nghe/đọc rà soát. Hmong đã sửa các lỗi thuật ngữ được phát hiện; phương ngữ Hmong Trắng chưa được xác nhận độc lập. Không coi việc file phát được là chứng nhận bản dịch hoặc phát âm.\n'
readme+='\nTất cả17 bản dùng phong cách science-documentary-expressive-v1 theo yêu cầu mới: ngắt nghỉ, thay đổi nhịp nhẹ và nhấn từ/cụm từ trong khả năng engine. Giữ nguyên ID và mẫu giọng, không đổi cao độ. Melo dùng adapter prosody có lưu mã; Hmong dùng điều khiển theo cụm, không có căn từng từ. Chất lượng tự nhiên cần nghe rà soát.\n'
(OUT/'README.md').write_text(readme)
shutil.copy('input/NARRATION_STYLE_LOCKED.json',OUT/'NARRATION_STYLE_LOCKED.json')
with zipfile.ZipFile(OUT/'MALTA_03_17_VOICES_20m.zip','w',compression=zipfile.ZIP_STORED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.suffix!='.zip' and p.name not in ['render_report.json','subtitles.srt']:z.write(p,p.relative_to(OUT))
details=OUT/'MALTA_03_VOICE_DETAILS.zip'
with zipfile.ZipFile(details,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.suffix not in ['.mp3','.zip'] and p.name not in ['render_report.json','subtitles.srt']:z.write(p,p.relative_to(OUT))
doc_url=f'https://raw.githubusercontent.com/{REPO}/{DOCS}/productions/video-03-malta/MALTA_VIDEO_03_TAI_LIEU_20_PHUT.zip'
data=urllib.request.urlopen(doc_url,timeout=60).read();assert hashlib.sha256(data).hexdigest()=='e8406c627595cda691bf1859a57739da0d996639f0fcc67fb3cf48676a9ef6ec'
doc=OUT/'MALTA_VIDEO_03_TAI_LIEU_20_PHUT.zip';doc.write_bytes(data)
notes='Malta, chủ đề 3: kịch bản tiếng Anh 20 phút, 100 prompt riêng và 20 cảnh dùng lại có đánh dấu.\n\n'+readme
(OUT/'RELEASE_NOTES.md').write_text(notes)
existing=subprocess.run(['gh','release','view',TAG,'--repo',REPO],capture_output=True)
if existing.returncode:
    subprocess.run(['gh','release','create',TAG,'--repo',REPO,'--target',DOCS,'--title','Malta Video 03 — 17 voices, 20 minutes','--draft','--notes-file',str(OUT/'RELEASE_NOTES.md')],check=True)
for row in manifest:subprocess.run(['gh','release','upload',TAG,str(OUT/row['filename']),'--repo',REPO,'--clobber'],check=True)
for name in ['MALTA_03_17_VOICES_20m.zip','MALTA_03_VOICE_DETAILS.zip','VOICE_PROFILES_LOCKED.json','NARRATION_STYLE_LOCKED.json','AUDIO_MANIFEST.json','README.md','MALTA_VIDEO_03_TAI_LIEU_20_PHUT.zip']:
    subprocess.run(['gh','release','upload',TAG,str(OUT/name),'--repo',REPO,'--clobber'],check=True)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--draft=false','--latest=false'],check=True)
print('All 17 verified Malta voices published',flush=True)
