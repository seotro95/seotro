"""Refresh downloadable documents after verified audio publication; never re-encode speech."""
import hashlib,json,shutil,subprocess,urllib.request,zipfile
from pathlib import Path
R=Path(__file__).parent;repo='seotro95/seotro';tag='land-bridges-video-38-22m32s';base=f'https://github.com/{repo}/releases/download/{tag}/'
def api():return json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/releases/tags/{tag}']))
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def upload(p):subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True)
publicqa=json.loads((R/'PUBLIC_DOWNLOAD_QA.json').read_text());assert publicqa['status']=='passed' and publicqa['voice_count']==17 and publicqa['decoded_frames_per_voice_48000']==64896000
release=api();assets={a['name']:a for a in release['assets']}
voicezip=assets['LAND_BRIDGES_38_17_VOICES_22m32s.zip'];assert voicezip['digest']=='sha256:'+publicqa['public_voice_archive_sha256']
for v in publicqa['voices']:assert assets[v['filename']]['digest']=='sha256:'+v['sha256']
name='LAND_BRIDGES_38_TAI_LIEU_22m32s.zip';archive=R/name
with urllib.request.urlopen(base+name,timeout=60) as response:archive.write_bytes(response.read())
assert sha(archive)==assets[name]['digest'].removeprefix('sha256:')
doc=R/'refreshed_documents';doc.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and len(z.infolist())<1000 and sum(x.file_size for x in z.infolist())<20_000_000
 for x in z.infolist():
  p=(doc/x.filename).resolve();assert p.is_relative_to(doc.resolve())
  if x.is_dir():p.mkdir(parents=True,exist_ok=True)
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(x))
q=json.loads((doc/'DOCUMENT_QA.json').read_text());assert q['voices_generated'] and q['voice_count_verified']==17 and q['target_seconds']==1352
for n in ['PUBLIC_DOWNLOAD_QA.json','PRODUCTION_STEPS_APPLIED.md','PROMPT_TIEP_TUC_CHU_DE_38.txt']:shutil.copyfile(R/n,doc/n)
guide='''CHỦ ĐỀ 38 — CẦU ĐẤT QUA NHỮNG CHU KỲ BĂNG HÀ — 22:32

1. Kịch bản chính: KICH_BAN_EN_22m32s.txt. Có 136 mốc lời: 135 mốc 10 giây và mốc cuối 2 giây, tổng 1.352 giây.
2. Trong PROMPTS có 12 TXT, mỗi TXT 10 prompt, tổng 120 bối cảnh mới. Tạo clip im lặng 10 giây, đặt tên 001.mp4 đến 120.mp4 theo ID prompt.
3. TIMELINE_136_CANH.csv nối ID mốc lời với ID prompt. Có 16 mốc REUSE, không tạo lại clip. Mốc cuối chỉ lấy 2 giây từ clip 001.
4. Không có trẻ em hoặc thiếu niên, kể cả nền, tranh, màn hình, bóng và phản chiếu. Clip không có lời, nhạc hoặc tiếng hiệu ứng; xóa hết âm thanh clip gốc khi dựng.
5. Các mô hình trong prompt là minh họa nguyên lý. Bản đồ, nhãn và số liệu cần kiểm tra trước khi thêm vào phần dựng.
6. Đã có 17 MP3 riêng theo quốc gia: 16 giọng nam và nữ H'mông female-3. Mỗi tệp đã giải mã kiểm tra đúng 64.896.000 mẫu mono 48 kHz, tương đương 22:32.
7. Bản Anh là giọng chính, được căn theo 136 mốc. Các bản dịch giữ 14 ranh giới chương: 13 chương 100 giây và chương cuối 52 giây. Cùng tổng thời lượng không đồng nghĩa từng từ trùng thời điểm.
8. Mã giọng và tham chiếu giữ nguyên. Nhấn nhá bằng nhịp câu, khoảng nghỉ và nhấn từ nhẹ; không đổi pitch. SRT bản dịch là mốc chương, cần chia nhỏ trước khi hiển thị như phụ đề.
9. Kiểm kỹ thuật không thay thế việc nghe và biên tập bản ngữ. Phương ngữ H'mông Trắng chưa được người bản ngữ xác nhận độc lập.
10. Chưa có footage hoặc MP4 của tập 38. Khi có clip, chọn 10 cảnh mạnh trong 30 giây đầu, nằm trong tổng 22:32; chỉ dùng voice Anh, không nhạc/SFX. Cảnh thiếu dùng video chuyển động liên quan, không dùng ảnh tĩnh hoặc thẻ chữ.
'''
(doc/'HUONG_DAN_SU_DUNG.txt').write_text(guide,encoding='utf-8-sig')
readme=doc/'README.md';text=readme.read_text();text+='\n[5 tiêu đề và prompt thumbnail]('+base+'LAND_BRIDGES_38_5_TIEU_DE_5_PROMPT_THUMBNAIL.txt) · [Kiểm tra bản tải công khai]('+base+'PUBLIC_DOWNLOAD_QA.json)\n';readme.write_text(text)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(doc.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(doc))
for p in [archive,doc/'HUONG_DAN_SU_DUNG.txt',doc/'PRODUCTION_STEPS_APPLIED.md',doc/'PROMPT_TIEP_TUC_CHU_DE_38.txt',doc/'PUBLIC_DOWNLOAD_QA.json',readme]:upload(p)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--notes-file',str(readme),'--latest=false'],check=True)
release=api();assets={a['name']:a for a in release['assets']}
excluded={'DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt','LAND_BRIDGES_38_17_VOICES_22m32s.zip'}
manifest={'topic_id':38,'target_seconds':1352,'stage':'documents_updated_after_all17voices_and_public_audio_verification','self_and_checksum_file_excluded':True,'assets':[{'name':a['name'],'bytes':a['size'],'sha256':a['digest'].removeprefix('sha256:')} for a in release['assets'] if a['name'] not in excluded and not a['name'].endswith('.mp3')]}
p=R/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));upload(p)
release=api();p=R/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda a:a['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
print('COMPLETE_DELIVERY_DOCUMENTS_REFRESHED',sha(archive),flush=True)
