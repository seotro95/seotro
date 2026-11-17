"""Revise visual documents only; retain every previously generated voice byte."""
import hashlib,io,json,os,re,shutil,subprocess,sys,time,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';REPO='seotro95/seotro';TAG='roman-concrete-moi-022-21m22s';BASE=f'https://github.com/{REPO}/releases/download/{TAG}/';REV='historical-context-v2-no-scientists'
def ghjson(route):return json.loads(subprocess.check_output(['gh','api',route]))
def release():return ghjson(f'repos/{REPO}/releases/tags/{TAG}')
def sha(b):return hashlib.sha256(b).hexdigest()
def upload(p):
    subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
    print('HISTORICAL_ASSET_PUBLISHED',p.name,flush=True)
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for attempt in range(118):
    run=ghjson('repos/seotro95/seotro/actions/runs/44036830939')
    if run['status']=='completed':
        assert run['conclusion']=='success','Original audio publication failed; preserve successful artifacts and fix only failed publication or voice jobs'
        break
    print('WAIT_FOR_ORIGINAL_VOICE_PUBLICATION',attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('Original voice run not complete; historical source changes retained')
before=release();assets={a['name']:a for a in before['assets']}
frozen={n:a['digest'] for n,a in assets.items() if n.endswith('.mp3') or n=='ROMAN_MOI022_16_VOICES_21m22s.zip'}
assert len([n for n in frozen if n.endswith('.mp3')])==16
name='ROMAN_MOI022_TAI_LIEU_21m22s.zip'
with urllib.request.urlopen(BASE+name+'?v='+assets[name]['digest'].split(':')[1],timeout=60) as response:data=response.read();assert response.status==200
assert len(data)==assets[name]['size'] and 'sha256:'+sha(data)==assets[name]['digest']
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert z.testzip() is None
    for x in z.infolist():
        assert not Path(x.filename).is_absolute() and '..' not in Path(x.filename).parts
        out=D/x.filename;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(x))
old_readme=(D/'README.md').read_text();old_guide=(D/'HUONG_DAN_SU_DUNG.txt').read_text()
old_script=(D/'KICH_BAN_EN_21m22s.txt').read_bytes();old_srt=(D/'en-US.srt').read_bytes()
voiceqa=json.loads((D/'VOICE_RELEASE_QA.json').read_text());assert voiceqa['status']=='passed' and voiceqa['voices']==16 and voiceqa['all_decoded_frames_48000']==61536000
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
assert (D/'KICH_BAN_EN_21m22s.txt').read_bytes()==old_script and (D/'en-US.srt').read_bytes()==old_srt
inputqa=json.loads((R/'VOICE_INPUT_QA.json').read_text())
for locale,expected in inputqa['script_sha256'].items():
    assert sha((R/'voice/scripts'/f'{locale}.json').read_bytes())==expected
shots=json.loads((D/'ALL_PROMPTS.json').read_text());assert len(shots)==140
assert all(s['visual_revision']==REV and s['prompt'].endswith('Video không có âm thanh, không có lời nói.') for s in shots)
assert all('No scientists, researchers, technicians, modern laboratory interiors' in s['prompt'] for s in shots)
assert len(list((D/'PROMPTS').glob('*.txt')))==14
for p in (D/'PROMPTS').glob('*.txt'):assert len(re.findall(r'^\d{3}\. ',p.read_text(),re.M))==10
q=json.loads((D/'DOCUMENT_QA.json').read_text());q.update(voices_generated=True,voice_count_verified=16,audio_sample_frames_verified=61536000,translated_chapter_alignment_verified=True,independent_native_listening_review=False,visual_revision=REV,scientist_scenes=False,modern_laboratory_scenes=False,voice_bytes_changed=False);dump(D/'DOCUMENT_QA.json',q)
note='''

## Bản hình lịch sử theo yêu cầu mới nhất

Toàn bộ 140 prompt đã thay theo bản historical-context-v2-no-scientists: ưu tiên công trường, thợ xây trưởng thành, tường, lò vôi, bể chứa, cầu dẫn nước và bến cảng La Mã. Bỏ nhà khoa học, phòng thí nghiệm và thiết bị đo hiện đại. Các đoạn giải thích dùng mặt cắt vật liệu trung tính, chỉ là minh họa. Không gán thí nghiệm hiện đại cho người La Mã. Thumbnail 3 cũng thay bộ thử hiện đại bằng hình vật liệu và bể chứa minh họa.

Giữ nguyên kịch bản, 16 MP3 và ZIP voice; không tạo lại audio. Mốc 21:22, 136 cảnh và 4 dự phòng giữ nguyên. Tệp prompt lịch sử riêng: [ROMAN_MOI022_PROMPT_LICH_SU_14_TXT.zip]('''+BASE+'''ROMAN_MOI022_PROMPT_LICH_SU_14_TXT.zip).
'''
for n in ['README.md','DOWNLOAD_LINKS.md']:(D/n).write_text(old_readme+note,encoding='utf-8')
(D/'HUONG_DAN_SU_DUNG.txt').write_text((D/'HUONG_DAN_SU_DUNG.txt').read_text()+'\nĐã tạo và kiểm đủ 16 voice, cùng 21:22. Đây là bản hình lịch sử mới; audio và các mốc giữ nguyên. Bản dịch chưa được kiểm nghe/biên tập bản ngữ độc lập.\n',encoding='utf-8')
revision=dict(status='passed',visual_revision=REV,topic_id='MOI-022',prompts=140,prompt_txt_files=14,prompts_per_txt=10,timeline_shots=136,backup_prompt_ids=[137,138,139,140],seconds=1282,scientist_scenes=False,modern_laboratory_scenes=False,english_text_unchanged=True,english_srt_unchanged=True,voice_bytes_changed=False,voices_retained=16,frozen_voice_digests=frozen)
dump(D/'HISTORICAL_VISUAL_REVISION_QA.json',revision)
shutil.copyfile(R/'HISTORICAL_CUE_VISUALS.tsv',D/'HISTORICAL_CUE_VISUALS.tsv')
guide='BẢN PROMPT LỊCH SỬ — MỚI-022 — 21:22\n\n14 TXT, mỗi tệp 10 prompt. 001–136 dùng theo timeline; 137–140 dự phòng. Mọi clip nguồn tạo 10 giây. 10 cảnh đầu lấy 3 giây/cảnh; 011–135 lấy 10 giây; 136 lấy 2 giây. Không trẻ em, không nhà khoa học/phòng thí nghiệm hiện đại, không âm thanh/lời nói. Hình là phục dựng/minh họa, không dữ liệu đo thật. Giữ kịch bản và 16 voice đã tạo.\n'
promptzip=R/'ROMAN_MOI022_PROMPT_LICH_SU_14_TXT.zip'
with zipfile.ZipFile(promptzip,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted((D/'PROMPTS').glob('*.txt')):z.write(p,p.name)
    z.writestr('DOC_TRUOC.txt',guide)
with zipfile.ZipFile(R/name,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
files=sorted((D/'PROMPTS').glob('*.txt'))+[R/name,promptzip]
files += [D/n for n in ['DOCUMENT_QA.json','HISTORICAL_VISUAL_REVISION_QA.json','PHAN_TICH_VA_KE_HOACH_DUNG.md','5_TIEU_DE_VA_THUMBNAIL.txt','TIMELINE_136_CANH.csv','OPENING_10_SHOTS_30s.json','BACKUP_137_140.json','HUONG_DAN_SU_DUNG.txt','PRODUCTION_STEPS_APPLIED.md','README.md','DOWNLOAD_LINKS.md']]
for p in files:upload(p)
after=release();after_by={a['name']:a for a in after['assets']}
assert all(after_by[n]['digest']==h for n,h in frozen.items())
record=dict(topic_id='MOI-022',stage='all16voices_and_documents_published',visual_revision=REV,target_seconds=1282,assets=[dict(name=a['name'],bytes=a['size'],sha256=a['digest'].removeprefix('sha256:')) for a in after['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt']])
p=R/'DOCUMENT_ASSET_MANIFEST.json';dump(p,record);upload(p)
after=release();p=R/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(after['assets'],key=lambda x:x['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--title','MỚI-022 Bê tông La Mã — prompt bối cảnh lịch sử, 16 voice — 21:22','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
print('ROMAN_HISTORICAL_VISUAL_REVISION_COMPLETE_VOICES_UNCHANGED',flush=True)
