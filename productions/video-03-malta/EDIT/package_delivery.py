import csv,hashlib,json,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery'
qa=json.loads((O/'FINAL_VIDEO_QA.json').read_text());assert qa['status']=='passed'
for name in ['TITLES_AND_THUMBNAIL_PROMPTS.txt','EDITOR_DECISIONS.json']:shutil.copy(R/name,O/name)
inv=json.loads((R/'inventory.json').read_text());plan=json.loads((R/'EDIT_PLAN.json').read_text());used={s['label'] for p in plan for s in p['segments']}
with (O/'SOURCE_CLIP_MANIFEST.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['label','original_filename','sha256','bytes','duration_seconds','contains_audio','used_in_edit'])
 for x in inv:w.writerow([x['label'],x['name'],x['sha256'],x['size_bytes'],x['format']['duration'],any(s['codec_type']=='audio' for s in x['streams']),x['label'] in used])
readme='''# Mal’ta — chủ đề 3, bản dựng hoàn chỉnh 20:00

MALTA_03_EN_FINAL_20m_720p.mp4: H.264, 1280×720, 24fps, AAC 48kHz. Chỉ có voice tiếng Anh gốc đã có nhấn nhá (en-US-AndrewNeural, science-documentary-expressive-v1). Không tạo lại giọng, đổi cao độ hay thay tốc độ; chỉ cân bằng âm lượng. Không nhạc, SFX hoặc tiếng từ clip nguồn. Phụ đề tiếng Anh có thể bật/tắt và có SRT riêng. 120 mốc lời, mỗi mốc10s; 12 chương100s.

Mở đầu8shot/30s: hạt trang sức → bàn tay chế tác → người và thung lũng Siberia → mô hình bối cảnh chôn cất không có thi thể → đồ trang sức replica → hộp lưu trữ → thao tác phòng thí nghiệm → bản đồ quan hệ tổ tiên. Giữ nguyên thời gian voice, không nối thêm intro. Phần còn lại dùng cắt thẳng, cutaway theo lời kể,5 chuyển cảnh ngắn ở đổi bối cảnh và đoạn kết, tiêu đề chương, chú thích và sơ đồ có nhãn.

Đã kiểm kê100 clip10s, chọn66 clip phù hợp và bổ sung17 đồ hoạ.30 clip đầu vào có audio; toàn bộ audio clip bị loại khỏi đường tiếng cuối. EDIT_TIMELINE.csv ghi vị trí, nguồn, source-in và thời lượng từng shot. SOURCE_CLIP_MANIFEST.csv ghi SHA256 và clip nào được dùng. Cảnh có bản đồ sai, biểu đồ giả, mẫu xương sai loại hoặc không phù hợp lời kể đã được thay. HìnhAI, hiện vật replica và cảnh thực nghiệm đều là minh hoạ; không coi là ghi hình thực địa gốc, mẫu MA-1 thật hoặc chân dung xác thực của đứa trẻ.

Đã sửa lỗi khép mảnh đa giác khi hiển thị đường bờ quanh kinh tuyến180° trên3 nền bản đồ cũ. Bản cuối dùng vòng đa giác Natural Earth nguyên vẹn và bản sao dịch kinh độ cả vòng; không cuộn từng điểm rồi nối tắt qua Siberia. Nền bờ biển/hồ là địa lý hiện đại tổng quát. NPS bathymetry giữ nguyên nhãn và credit khoảng21.000BP, không coi là bờ24.000năm hay tuyến đi của MA-1. Dòng nối nét đứt chỉ quan hệ di truyền, không phải hành trình đã chứng minh. Sơ đồ gene không phải kết quả đo thật, tỷ lệ tổ tiên phổ quát hoặc phả hệ cá nhân.

FINAL_VIDEO_QA.json ghi kiểm tra thời lượng, frame, số đường tiếng, đồng bộ dạng sóng ở13 vị trí, loudness và giải mã toàn bộ. Rà hình bằng ảnh tổng quan100 clip và lấy mẫu phần mở đầu, đồ hoạ, các chương, đoạn kết; không tuyên bố đã xem thủ công liên tục cả20phút.

MALTA_03_EDIT_PROJECT.zip chứa kế hoạch dựng, code, đồ hoạ, overlay, voice Anh gốc, phụ đề, hồ sơ nguồn, ảnh kiểm tra và nền bản đồ đã sửa. Không đóng lại100 clip nguồn: giữ tệp người dùng upload để tái dựng. Khi chuyển máy cần ánh xạ lại đường dẫn clip/frame trong inventory.json, đường dẫn ROOT và đầu vào package/voice/references trong các script. Thư mục script_inputs chứa kịch bản, CHAPTERS_12 và ánh xạ clip; original_english_voice chứa MP3 có SHA256 trong báo cáo. ZIP tài liệu kịch bản trước đây là bản chụp cũ: dùng nền bản đồ mới trong project/REFERENCES khi tạo composite.

17 voice riêng theo tên quốc gia vẫn ở release https://github.com/seotro95/seotro/releases/tag/malta-video-03-20min
Không thay đổi bản dịch, giọng khác hoặc hàng đợi chủ đề4. Nguồn khoa học xem SCIENCE_REFERENCES.md. Tham chiếu cách kể/dựng là video người dùng cung cấp, SHA256f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c.
'''
(O/'README.md').write_text(readme)
with zipfile.ZipFile(O/'MALTA_03_EDIT_PROJECT.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in ['build_plan.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','review_opening.py','inventory.py','inventory.json','EDIT_PLAN.json','EDITOR_DECISIONS.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json','chapters.ffmetadata']:
  z.write(R/name,name)
 for folder in ['graphics','overlays','review']:
  for p in (R/folder).glob('*'):
   if p.is_file():z.write(p,str(p.relative_to(R)))
 for p in O.iterdir():
  if p.suffix in ['.json','.csv','.txt','.srt','.md']:z.write(p,'delivery/'+p.name)
 for name in ['SCENES_AND_PROMPTS.json','CHAPTERS_12.csv','UNIQUE_PROMPTS_100.json']:z.write(R.parent/'package'/name,'script_inputs/'+name)
 z.write(R.parent/'voice/verified-en/MALTA_03_My_Tieng_Anh.mp3','original_english_voice/MALTA_03_My_Tieng_Anh.mp3');z.write(R.parent/'voice/verified-en/VERIFIED_AUDIO.json','original_english_voice/VERIFIED_AUDIO.json')
 z.write(R.parent/'package/NGUON_KIEM_CHUNG.md','SCIENCE_REFERENCES.md');z.write(R.parent/'make_reference_maps.py','references/make_reference_maps.py');z.write(R.parent/'ne_110m_lakes.geojson','references/ne_110m_lakes.geojson');z.write('/workspace/work/beringia/edit/ne_110m_land.geojson','references/ne_110m_land.geojson')
 for p in (R.parent/'package/REFERENCES').glob('*'):
  if p.is_file():z.write(p,'REFERENCES/'+p.name)
 for p in (R/'frames').glob('*.jpg'):z.write(p,'source_frames/'+p.name)
with zipfile.ZipFile(O/'MALTA_03_EDIT_PROJECT.zip') as z:assert z.testzip() is None
rows=[]
for p in sorted(O.iterdir()):
 if p.is_file() and p.name!='SHA256SUMS.txt':rows.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(O/'SHA256SUMS.txt').write_text('\n'.join(rows)+'\n')
print(json.dumps({'files':[(p.name,p.stat().st_size) for p in sorted(O.iterdir())]}),flush=True)
