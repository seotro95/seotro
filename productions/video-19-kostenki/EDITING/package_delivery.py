import csv,hashlib,json,re,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';qa=json.loads((O/'FINAL_VIDEO_QA.json').read_text());assert qa['status']=='passed'
review=json.loads((R/'VISUAL_REVIEW_APPROVED.json').read_text());assert review['final_movie_review_status']=='passed'
plan=json.loads((R/'EDIT_PLAN.json').read_text());used={s['clip_id'] for p in plan for s in p['segments']}
inventory=json.loads((R/'inventory.json').read_text());safe={'topic':19,'raw_source_media_included':False,'private_upload_identifiers_included':False,'clips':[{**{k:x[k] for k in ['label','clip_id','source_name','source_bytes','source_sha256','source_audio_streams']},'used_in_final':x['clip_id'] in used} for x in inventory]}
(R/'SOURCE_MANIFEST.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2));(O/'SOURCE_MANIFEST.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2))
for n in ['EDITOR_DECISIONS.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json','VISUAL_REVIEW_APPROVED.json','SUBSTITUTIONS.csv']:shutil.copyfile(R/n,O/n)
with (O/'SOURCE_CLIP_MANIFEST.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(safe['clips'][0]));w.writeheader();w.writerows(safe['clips'])
text=(R/'TITLES_AND_THUMBNAIL_PROMPTS.txt').read_text();assert text.count('TITLE EN:')==text.count('PROMPT:')==5
(O/'KOSTENKI_19_TITLES_THUMBNAILS.txt').write_text(text,encoding='utf-8-sig')
with zipfile.ZipFile(O/'KOSTENKI_19_TITLES_THUMBNAILS.zip','w',zipfile.ZIP_DEFLATED) as z:z.write(O/'KOSTENKI_19_TITLES_THUMBNAILS.txt','KOSTENKI_19_TITLES_THUMBNAILS.txt')
base='https://github.com/seotro95/seotro/releases/download/kostenki-video-19-final-20m15s/'
readme=f'''# Kostenki — chủ đề 19 — bản dựng hoàn chỉnh 20:15

[Tải video hoàn chỉnh]({base}KOSTENKI_19_EN_FINAL_20m15s_720p.mp4) · [Mở đầu 30 giây]({base}KOSTENKI_19_OPENING_30s.mp4)

[5 tiêu đề và 5 prompt thumbnail — TXT]({base}KOSTENKI_19_TITLES_THUMBNAILS.txt) · [ZIP dự phòng cho TXT]({base}KOSTENKI_19_TITLES_THUMBNAILS.zip) · [Dự án dựng]({base}KOSTENKI_19_EDIT_PROJECT.zip)

1280×720, 24 fps, 29.160 khung hình, đúng 20:15. Chỉ một đường voice tiếng Anh đã lưu: en-US-AndrewNeural. Bỏ toàn bộ tiếng gốc của clip; không nhạc hoặc hiệu ứng âm thanh. Giữ lời, cao độ và thời gian voice; chỉ chuẩn hóa độ lớn khi xuất.

Đúng 10 cảnh khác nhau trong 30 giây đầu, nằm trong tổng 20:15. Cắt theo câu chuyện và dùng chín chuyển cảnh hòa hình 0,4 giây có bù thời gian. Phần kết trở lại hàm và vòng xương. Có phụ đề Anh tùy chọn, mặc định tắt, SRT riêng và 12 chương.

Đã kiểm tra mẫu hình ở ba thời điểm trong 100 clip khác nhau; dùng {len(used)} clip trong bản cuối. Hai mươi mã prompt chưa có clip được bù bằng video liên quan. Các clip khác không phù hợp hình/bối cảnh cũng được thay; xem SUBSTITUTIONS.csv và EDIT_PLAN.json. Không dùng ảnh đứng hoặc bảng chữ để bù cảnh. Không có hình trẻ em được phát hiện trong những mẫu hình đã duyệt. Đây là kiểm tra bằng mẫu hình, không phải xem tay liên tục toàn bộ video.

Hình là minh họa và mô hình giảng giải. Mái che và chức năng cấu trúc Kostenki còn được tranh luận; không coi hình tái dựng là chứng minh thiết kế thật. Các mẫu vật hiển thị không được tuyên bố là đúng những mẫu đã phân tích trong nghiên cứu. Các cấu trúc xương quá cao, cảnh có chữ lớn hoặc bối cảnh không phù hợp đã được lọc/cắt khung/thay thế.

Đã giải mã toàn bộ video, kiểm tra số khung hình, thời lượng, khoảng đen, độ lớn/đỉnh âm và 15 điểm đồng bộ sóng âm với voice Anh. FINAL_VIDEO_QA.json ghi số đo. Bộ 17 voice riêng vẫn ở [release lời đọc](https://github.com/seotro95/seotro/releases/tag/kostenki-video-19-20m15s).

Dự án không kèm video nguồn, proxy, ảnh trích nguồn hay mã tải lên riêng tư. Bản tải lên gốc trong cuộc trò chuyện được giữ; chỉ thu hồi cache tải về sau khi đã tạo bản video im lặng và lưu hash. Dùng SOURCE_CLIP_MANIFEST.csv và link_sources.py để nối lại các clip bạn đã tải.
'''
(O/'README.md').write_text(readme)
instructions='''DỰNG LẠI CHỦ ĐỀ 19 — KOSTENKI 20:15

Yêu cầu Python 3.11+, ffmpeg/ffprobe có libx264 và drawtext, numpy cho QA. Font mặc định /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf; trên Windows đặt đường dẫn font trong render_edit.py thành đường dẫn tương đối tới một bản font đã cài.

1. Giải nén và mở terminal ở thư mục edit. Cần khoảng 1,5 GB trống.
2. python link_sources.py /thu-muc-chua-video-goc
3. python render_edit.py --workers 2
4. python assemble_final.py
5. python qa_final.py

Giữ EDIT_PLAN.json đã duyệt; không cần tạo lại storyboard. Voice và bảng đo loudness được kèm để dựng lại. link_sources.py xác minh hash nguồn và tạo video im lặng 720p; không di chuyển/xóa bản gốc. Các phiên bản ffmpeg khác nhau có thể tạo byte mã hóa khác nhau.
'''
(O/'HUONG_DAN_DUNG_LAI.txt').write_text(instructions,encoding='utf-8-sig')
with zipfile.ZipFile(O/'KOSTENKI_19_EDIT_PROJECT.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in ['render_edit.py','assemble_final.py','qa_final.py','link_sources.py','EDIT_PLAN.json','SOURCE_MANIFEST.json','EDITOR_DECISIONS.json','SUBSTITUTIONS.csv','loudness_measurement.log','VISUAL_REVIEW_APPROVED.json']:z.write(R/n,'edit/'+n)
 for p in (R/'input').iterdir():
  if p.is_file():z.write(p,'edit/input/'+p.name)
 z.write(O/'HUONG_DAN_DUNG_LAI.txt','HUONG_DAN_DUNG_LAI.txt')
pattern=re.compile(rb'file_[0-9a-f]{32}|/workspace/attachments/[0-9a-f]{8}-')
with zipfile.ZipFile(O/'KOSTENKI_19_EDIT_PROJECT.zip') as z:
 assert not any(n.endswith(('.mp4','.png','.jpg')) for n in z.namelist())
 for n in z.namelist():
  if not n.endswith('.mp3'):assert not pattern.search(z.read(n)),n
assets=[]
for p in sorted(O.iterdir()):
 if p.is_file() and p.name not in ['SHA256SUMS.txt','RELEASE_ASSET_MANIFEST.json']:
  if p.suffix in ['.txt','.md','.json','.csv','.srt']:assert not pattern.search(p.read_bytes()),p.name
  assets.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
(O/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in assets));(O/'RELEASE_ASSET_MANIFEST.json').write_text(json.dumps({'topic':19,'raw_source_clips_included':False,'assets':assets},indent=2))
print(json.dumps({'assets':len(assets),'source_clips_used':len(used),'private_source_references':0}),flush=True)
