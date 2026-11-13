"""Stage only the episode's verified delivery documents and individual MP3s."""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'github-delivery'
BRANCH='flores-040-22m00s'
PAGE=f'https://github.com/seotro95/seotro/tree/{BRANCH}'
RAW=f'https://github.com/seotro95/seotro/raw/refs/heads/{BRANCH}/'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()

def main():
 manifest=json.loads((ROOT/'DELIVERY_MANIFEST.json').read_text())
 assert manifest['voices']==17 and len(manifest['files'])==17
 for directory in ['scripts','prompts','research','titles-thumbnails','source-analysis','tools']:
  for source in (ROOT/directory).rglob('*'):
   if source.is_file() and '__pycache__' not in source.parts and not source.name.endswith('.pyc'):
    target=STAGE/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 for name in ['KICH-BAN-CHINH.md','EDITING-GUIDE.md','BANG-TINH-132-DOAN.md','scene-voice-edit.csv','shot-reuse-map.json',
              'VOICE_PROFILES.json','DELIVERY_MANIFEST.json','PRODUCTION_STATE.json','Flores-040-production-kit.zip',
              '60-prompts-6-txt-10s.zip','validation/final-delivery.json','validation/reference-access.json',
              'validation/research-access.json','validation/pending-text-revisions.json']:
  source=ROOT/name;target=STAGE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 for row in manifest['files']:
  source=ROOT/row['file'];target=STAGE/row['file'];target.parent.mkdir(exist_ok=True,parents=True)
  assert sha(source)==row['sha256']
  if target.exists() and sha(target)!=row['sha256']:target.unlink()
  if not target.exists():os.link(source,target)
  report=ROOT/f"audio/{row['language']}-report.json"
  dst=STAGE/'validation/audio-reports'/report.name;dst.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(report,dst)
 lines=['# Flores — tập 40 — 22:00','',
 'Chủ đề đã lưu: **Flores: Caves, Volcanoes, and an Unexpected Past**. Đã tạo đủ **17 MP3 thật**, mỗi bản giải mã đúng **1.320 giây**, cùng 132 mốc lời × 10 giây. Tiếng Anh Andrew là bản phim chính; 16 track khác là lựa chọn thay thế.','',
 f'**[TẢI TẤT CẢ: 17 MP3 + kịch bản + prompt + SRT](https://github.com/seotro95/seotro/archive/refs/heads/{BRANCH}.zip)**','',
 'Trong trang này, bấm tên ngôn ngữ để tải MP3 riêng. Không cần chạy Python hoặc cài công cụ để nghe. Nếu trình duyệt phát trực tiếp, dùng chức năng tải của trình phát.','',
 '| Quốc gia / ngôn ngữ | Giọng đã khóa | Độ dài |', '|---|---|---|']
 for row in manifest['files']:
  lines.append(f"| [{row['label']}]({RAW+row['file']}) | `{row['voice_id']}` | 22:00 |")
 lines.extend(['','## Kịch bản, hình và cách dựng','',
 f'- [Kịch bản chính Anh–Việt, đủ timecode]({PAGE}/KICH-BAN-CHINH.md)',
 f'- [17 bản lời và SRT]({PAGE}/scripts)',
 f'- [Tải 60 prompt trong 6 TXT, mỗi TXT 10 prompt]({RAW}60-prompts-6-txt-10s.zip)',
 f'- [Bảng 132 đoạn từ 00:00 đến 22:00]({PAGE}/BANG-TINH-132-DOAN.md)',
 f'- [Hướng dẫn dựng]({PAGE}/EDITING-GUIDE.md)',
 f'- [5 tiêu đề và 5 prompt thumbnail]({PAGE}/titles-thumbnails/5-TIEU-DE-VA-THUMBNAIL.md)',
 f'- [Phân tích video nguồn]({PAGE}/source-analysis/PHAN-TICH-VIDEO-NGUON.md)',
 f'- [Gói sản xuất nhỏ: lời, prompt, hướng dẫn, hồ sơ giọng]({RAW}Flores-040-production-kit.zip)','',
 '**Tạo 60 clip × 10 giây; dùng lại ở 72 ô theo bảng: 600 + 720 = 1.320 giây.** Các ô dùng lại vẫn chạy đủ 10 giây, không xóa khỏi timeline. Prompt đánh số 1–60, không tạo lại cho bối cảnh lặp. Mỗi prompt ghi không trẻ em, không âm thanh, không lời nói. Bộ này chưa chứa clip video được sinh hoặc phim MP4 dựng sẵn.','',
 'Mạch phim: cửa hang → địa chất → biển và sinh thái đảo → phát hiện Homo floresiensis → niên đại sửa đổi → Mata Menge → Kelimutu, Inerie, Wae Rebo → trở lại cửa hang. Các mô hình là hình giải thích, không phải tư liệu khai quật hoặc khảo sát thực địa.','',
 '## Giọng cho các tập sau và kiểm tra','',
 f'Giữ nguyên [VOICE_PROFILES.json]({PAGE}/VOICE_PROFILES.json): 16 giọng nam, ngoại lệ H’Mông Trắng nữ female-3. Dùng backend Python của Melo-Viet Studio 1.3.1 và Voice Studio Hmong 1.6.6; Windows EXE không chạy trong Linux cloud. Phiên bản, model và bản tham chiếu giọng được ghi để tái sử dụng.','',
 'Đã giải mã lại từng MP3: 31.680.000 mẫu ở 24 kHz, mono, 96 kbps; kiểm tra SHA-256, 132 đoạn có tín hiệu, không cắt từ, kịch bản khớp báo cáo render và mức tăng tốc tối đa không quá 1,3. MP3 có thể hiện lệch vài mili giây trong một số trình đọc metadata do khung mã hóa.','',
 'Chưa có vòng duyệt đầy đủ bởi người bản ngữ; nên nghe rà lời dịch và phát âm, nhất là H’Mông, trước khi phát hành phim. Những trang nghiên cứu bên ngoài bị proxy chặn được ghi rõ trong ghi chú nguồn, không được trình bày như đã truy cập thành công.','',
 f'[Manifest và mã băm]({PAGE}/DELIVERY_MANIFEST.json) · [Kết quả kiểm tra]({PAGE}/validation/final-delivery.json) · [Hồ sơ công cụ]({PAGE}/tools/TOOL_SOURCES.json)'])
 (STAGE/'README-final.md').write_text('\n'.join(lines)+'\n')
 assert all(p.stat().st_size<100*1024*1024 for p in STAGE.rglob('*') if p.is_file())
 print('Staged 17 individual MP3 files and production documents. Combined voice archive remains local; GitHub branch archive provides the full download.')

if __name__=='__main__':main()
