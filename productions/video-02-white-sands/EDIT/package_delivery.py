import csv,hashlib,json,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery'
assert json.loads((O/'FINAL_VIDEO_QA.json').read_text())['status']=='passed'
for name in ['TITLES_AND_THUMBNAIL_PROMPTS.txt','EDITOR_DECISIONS.json']:shutil.copy(R/name,O/name)
inv=json.loads((R/'inventory.json').read_text())
with (O/'SOURCE_CLIP_MANIFEST.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['label','original_filename','sha256','bytes','duration_seconds','contains_audio','used_in_edit'])
 used={s['label'] for p in json.loads((R/'EDIT_PLAN.json').read_text()) for s in p['segments']}
 for x in inv:w.writerow([x['label'],x['name'],x['sha256'],x['size_bytes'],x['format']['duration'],any(s['codec_type']=='audio' for s in x['streams']),x['label'] in used])
readme='''# White Sands — chủ đề 2, bản dựng hoàn chỉnh 22:00

Video: WHITE_SANDS_02_EN_FINAL_22m_720p.mp4 — H.264, 1280×720, 24 fps, AAC 48 kHz.
Chỉ có giọng đọc tiếng Anh gốc; mọi âm thanh của clip nguồn đã bị loại bỏ. Không thêm nhạc hoặc hiệu ứng âm thanh. Giọng không đổi cao độ hoặc tốc độ, chỉ cân bằng âm lượng. Phụ đề tiếng Anh có thể bật/tắt và có SRT riêng. 12 chương, 132 mốc lời dài 10 giây.

30 giây đầu gồm 8 shot: bàn chân ấn bùn → dấu chân → đụn cát hiện đại → trackway → hố nghiên cứu → người đi bên hồ → mammoth → đụn cát hiện đại. Không thêm intro làm lệch voice. Phần còn lại dùng cắt thẳng, cutaway theo ý lời dẫn, chuyển cảnh ngắn khi đổi bối cảnh, tiêu đề chương và sơ đồ định tuổi có nhãn.

98 clip đã nhận đều được kiểm kê, chọn 66 clip phù hợp cho bản dựng và bổ sung 15 sơ đồ minh hoạ. 29 clip có audio nhưng tất cả bị loại khỏi đường âm thanh cuối. Tệp SOURCE_CLIP_MANIFEST.csv ghi nguồn và SHA256; EDIT_TIMELINE.csv ghi từng vị trí sử dụng. Một số cảnh tạo sinh có bản đồ, biểu đồ hoặc nội dung không phù hợp được thay bằng hình khác và sơ đồ minh hoạ. Không trình bày hình tạo sinh như ghi hình khảo cổ thực địa thật. Đường bờ tham chiếu hiện đại lấy từ Natural Earth 1:110m, không phải đường bờ cổ chính xác.

FINAL_VIDEO_QA.json ghi thời lượng, số frame, đồng bộ dạng sóng giọng đọc, loudness và kiểm tra giải mã toàn bộ. Kiểm tra hình ảnh thực hiện bằng ảnh tổng quan nguồn và lấy mẫu phần mở đầu, các chương, đồ hoạ, đoạn kết; không phải tuyên bố đã xem thủ công liên tục cả 22 phút.

WHITE_SANDS_02_EDIT_PROJECT.zip chứa kế hoạch dựng, code render, overlay, đồ hoạ, phụ đề, bảng nguồn, lựa chọn biên tập và ảnh kiểm tra. Không đóng gói lại 98 clip gốc; giữ các tệp upload gốc để tái dựng. Đường dẫn nguồn trong inventory.json và đường dẫn ROOT trong các script cần ánh xạ lại khi chuyển máy. Đầu vào audio tiếng Anh giữ đúng SHA256 trong báo cáo QA.

17 voice riêng của tập 2 vẫn ở release: https://github.com/seotro95/seotro/releases/tag/white-sands-video-02-22min
Nguồn tham chiếu khoa học và cách kể: xem SCIENCE_REFERENCES.md và REFERENCE_STYLE.txt trong ZIP project.
'''
(O/'README.md').write_text(readme)
with zipfile.ZipFile(O/'WHITE_SANDS_02_EDIT_PROJECT.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in ['build_plan.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','inventory.py','inventory.json','EDIT_PLAN.json','EDITOR_DECISIONS.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json','chapters.ffmetadata']:
  z.write(R/name,name)
 for folder in ['graphics','overlays','review']:
  for p in (R/folder).glob('*'):
   if p.is_file():z.write(p,str(p.relative_to(R)))
 for p in O.iterdir():
  if p.suffix in ['.json','.csv','.txt','.srt','.md']:z.write(p,'delivery/'+p.name)
 for name in ['SCENES_AND_PROMPTS.json','CHAPTERS_12.csv','UNIQUE_PROMPTS_100.json']:
  z.write(R.parent/'package'/name,'script_inputs/'+name)
 z.write(R.parent/'voice/verified-en/WHITE_SANDS_02_en-US.mp3','original_english_voice/WHITE_SANDS_02_en-US.mp3')
 z.write('/workspace/work/beringia/edit/ne_110m_land.geojson','references/ne_110m_land.geojson')
 for p in (R/'frames').glob('*.jpg'):z.write(p,'source_frames/'+p.name)
 z.write(R.parent/'package/NGUON_KIEM_CHUNG.md','SCIENCE_REFERENCES.md');z.write(R.parent/'package/PHAN_TICH_NGUON_VA_QUY_TRINH.txt','REFERENCE_STYLE.txt')
rows=[]
for p in sorted(O.iterdir()):
 if p.is_file() and p.name!='SHA256SUMS.txt':rows.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(O/'SHA256SUMS.txt').write_text('\n'.join(rows)+'\n')
print(json.dumps({'files':[(p.name,p.stat().st_size) for p in sorted(O.iterdir())]}),flush=True)
