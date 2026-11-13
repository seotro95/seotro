"""Stage the completed, verified Angkor delivery without the large combined ZIP."""
import hashlib,json,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'github-delivery'
BRANCH='angkor-085-21m32s'
TREE=f'https://github.com/seotro95/seotro/tree/{BRANCH}'
BLOB=f'https://github.com/seotro95/seotro/blob/{BRANCH}'
RAW=f'https://github.com/seotro95/seotro/raw/refs/heads/{BRANCH}/'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()

def main():
 manifest=json.loads((ROOT/'DELIVERY_MANIFEST.json').read_text())
 assert len(manifest['files'])==17 and manifest['seconds']==1292 and manifest['prompt_txt_files']==10
 for folder in ['scripts','prompts','research','titles-thumbnails','source-analysis','tools']:
  for source in (ROOT/folder).rglob('*'):
   if source.is_file() and '__pycache__' not in source.parts and source.suffix!='.pyc':
    target=STAGE/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 for name in ['KICH-BAN-CHINH.md','EDITING-GUIDE.md','BANG-TINH-130-DOAN.md','scene-voice-edit.csv','shot-reuse-map.json',
  'VOICE_PROFILES.json','DELIVERY_MANIFEST.json','PRODUCTION_STATE.json','Angkor-085-production-kit.zip','100-prompts-10-txt-10s.zip',
  'validation/final-delivery.json','validation/reference-access.json','validation/research-access.json','validation/github-prompt-download.json']:
  target=STAGE/name;target.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(ROOT/name,target)
 for row in manifest['files']:
  source=ROOT/row['file'];target=STAGE/row['file'];target.parent.mkdir(exist_ok=True,parents=True)
  assert sha(source)==row['sha256']
  if target.exists() and sha(target)!=row['sha256']:target.unlink()
  if not target.exists():os.link(source,target)
  report=ROOT/f"audio/{row['language']}-report.json";dst=STAGE/'validation/audio-reports'/report.name
  dst.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(report,dst)
 lines=['# Angkor — tập 85 — 21:32','',
  'Chủ đề đã lưu: **Angkor: The City and Its Water Network** — **Angkor: thành phố và mạng lưới nước**. Đã tạo đủ **17 MP3 thật**, mỗi bản giải mã đúng **1.292 giây**. Tiếng Anh Andrew là bản chính, các ngôn ngữ khác thay thế cùng timeline.','',
  f'**[TẢI TẤT CẢ: 17 MP3 + 10 TXT + lời và SRT](https://github.com/seotro95/seotro/archive/refs/heads/{BRANCH}.zip)**','',
  'Bấm từng ngôn ngữ bên dưới để tải MP3 riêng. Nếu trình duyệt mở trình phát, dùng chức năng tải của trình phát. Không cần chạy mã hay cài công cụ để nghe.','',
  '| Quốc gia / ngôn ngữ | Giọng đã lưu | Thời lượng |','|---|---|---|']
 for row in manifest['files']:lines.append(f"| [{row['label']}]({RAW+row['file']}) | `{row['voice_id']}` | 21:32 |")
 lines+=['','## Kịch bản và prompt','',
  f'- [Tải 100 prompt trong 10 TXT, mỗi tệp 10 prompt]({RAW}100-prompts-10-txt-10s.zip)',
  f'- [Kịch bản chính Anh–Việt, đầy đủ timecode]({BLOB}/KICH-BAN-CHINH.md)',
  f'- [17 bản lời và SRT]({TREE}/scripts)',
  f'- [Bảng dựng 130 ô, đủ 21:32]({BLOB}/BANG-TINH-130-DOAN.md)',
  f'- [Hướng dẫn dựng]({BLOB}/EDITING-GUIDE.md)',
  f'- [5 tiêu đề và 5 prompt thumbnail]({BLOB}/titles-thumbnails/5-TIEU-DE-VA-THUMBNAIL.md)',
  f'- [Phân tích video nguồn và cách vận dụng]({BLOB}/source-analysis/PHAN-TICH-VIDEO-NGUON.md)',
  f'- [Gói sản xuất nhỏ, không chứa MP3]({RAW}Angkor-085-production-kit.zip)','',
  '**100 clip mới × 10 giây + 29 ô dùng lại × 10 giây + 2 giây giữ hình kết = 21:32.** Có đúng 10 TXT, đánh số prompt liên tục 1–100. Mỗi prompt ghi không trẻ em, không âm thanh, không lời nói. Dùng bảng để đặt clip, giữ nguyên các ô dùng lại. 129 cue lời kết ở 21:30; 2 giây cuối không lời.','',
  'Mạch kể: vệt nước trên đá → thành phố rộng hơn đền → mùa và địa hình → baray → mạng lưới → hộ gia đình và bảo trì → lidar, khí hậu → chuyển đổi lịch sử → bảo tồn và quay về vệt nước. Mô hình là hình minh họa, không phải bằng chứng một trận lũ cuối cùng hoặc khảo sát thực địa. Bộ giao chưa chứa 100 clip video được sinh hay phim MP4 dựng sẵn.','',
  '## Kiểm tra và giọng cho các tập sau','',
  f'Giữ nguyên [VOICE_PROFILES.json]({BLOB}/VOICE_PROFILES.json): 16 giọng nam; ngoại lệ H’Mông Trắng nữ female-3. Mã giọng, model và bản tham chiếu được khóa như tập trước. Dùng backend Python của Melo-Viet Studio 1.3.1 và Voice Studio Hmong 1.6.6 trên Linux cloud, không chạy Windows EXE.','',
  'Đã giải mã lại cả 17 MP3: 31.008.000 mẫu ở 24 kHz, mono, 96 kbps. Đã kiểm tra SHA-256, sự khớp với từng bản lời, 129 đoạn có tín hiệu, 2 giây kết và không cắt mất từ. Tăng tốc từng đoạn tối đa không vượt 1,3. Trình đọc metadata có thể hiện chênh vài mili giây do khung mã hóa MP3.','',
  'Chưa có vòng duyệt đầy đủ bởi người bản ngữ. Nên nghe rà lời dịch, địa danh và thuật ngữ, nhất là H’Mông, trước khi phát hành phim. Các trang nghiên cứu bên ngoài bị proxy chặn được ghi rõ trong ghi chú nguồn, không trình bày như đã đọc thành công.','',
  f'[Manifest và mã băm]({BLOB}/DELIVERY_MANIFEST.json) · [Kết quả kiểm tra]({BLOB}/validation/final-delivery.json) · [Hồ sơ công cụ]({BLOB}/tools/TOOL_SOURCES.json)']
 (STAGE/'README-final.md').write_text('\n'.join(lines)+'\n')
 assert all(p.stat().st_size<100*1024*1024 for p in STAGE.rglob('*') if p.is_file())
 print('Staged 17 MP3, 10 TXT and complete production documents; full download uses the GitHub branch archive.')

if __name__=='__main__':main()
