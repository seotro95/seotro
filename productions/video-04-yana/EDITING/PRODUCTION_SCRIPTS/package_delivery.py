import csv,hashlib,json,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';qa=json.loads((O/'FINAL_VIDEO_QA.json').read_text());assert qa['status']=='passed'
for n in ['TITLES_AND_THUMBNAIL_PROMPTS.txt','EDITOR_DECISIONS.json']:shutil.copy(R/n,O/n)
inv=json.loads((R/'inventory.json').read_text());plan=json.loads((R/'EDIT_PLAN.json').read_text());used={x['label'] for p in plan for x in p['segments']}
with (O/'SOURCE_CLIP_MANIFEST.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['label','original_filename','sha256','bytes','seconds','contained_audio','used_in_edit'])
 for x in inv:w.writerow([x['label'],x['name'],x['sha256'],x['size_bytes'],x['format']['duration'],any(s['codec_type']=='audio' for s in x['streams']),x['label'] in used])
dec=json.loads((R/'EDITOR_DECISIONS.json').read_text())
readme=f'''# Yana — chủ đề 4, video tiếng Anh hoàn chỉnh 23:00

YANA_04_EN_FINAL_23m_720p.mp4: H.264,1280×720,24fps; AAC48kHz. Giữ độ phân giải của clip nguồn. Một đường tiếng duy nhất từ voice Anh gốc có nhấn nhá, en-US-AndrewNeural. Không tạo lại giọng, thay tốc độ hay cao độ; chỉ cân bằng âm lượng. Không nhạc, SFX hoặc tiếng từ clip gốc. Phụ đề Anh có thể bật/tắt và có SRT riêng.

Mở đầu12shot trong30giây có sẵn của voice: mẫu răng → cảnh quan → định hướngYana → hệ sinh thái và cộng đồng trưởng thành → thao tác phòng thí nghiệm → mô hình so sánh. Không cộng thêm intro. Toàn bộ phim138ô10s,{dec['planned_shots']}shot;12chương theo ranh thật: sáu chương120s, sáu chương110s. Cắt theo ý lời dẫn, sáu dissolve ngắn đổi quy mô/bối cảnh, chú thích và tiêu đề chương.22đồ họa giải thích chiếm khoảng27%thời gian hình; chúng không phải kết quả đo gene thật.

Đã nhận133tệp, xác định18bản trùng hoàn toàn, kiểm kê115clip10s và chọn{dec['used_source_clips']}clip theo nội dung.36clip đầu vào có audio; tất cả audio này bị loại trước khi ghép. Năm bối cảnh prompt chưa có clip được thay bằng cảnh phù hợp và đồ họa, không để ô trống. Không dùng sốscene trong tên tệp làm thứ tự dựng một cách máy móc. EDIT_TIMELINE.csv ghi từng shot; SOURCE_CLIP_MANIFEST.csv ghi SHA256 và nguồn đã chọn.

Giữ yêu cầu không có hình trẻ em. Cảnh người chỉ chọn người trưởng thành đã kiểm tra; loại hình người nhỏ khó xác định tuổi, cảnh có thiết bị hiện đại trong bối cảnh cổ và bản đồ/chữ/biểu đồ tạo sai. Không tái dựng chủ mẫu răng sữa. Các mẫu răng nhìn thấy là vật minh họa/replica, không coi là ảnh mẫu Yana thật. Cảnh con người cổ là minh họa cộng đồng, không phải cá nhân đã nhận diện hay footage khảo cổ gốc.

Bản đồ NaturalEarth giữ nguyên vòng đa giác qua kinh tuyến180°, chỉ định hướng địa lý hiện đại tổng quát. Bản NPS giữ nhãn khoảng21.000BP, không gán thành bờ31.600năm hoặc đường đi của cá thể Yana. Đường nối chỉ giải thích so sánh; không khẳng định tuyến di cư, phả hệ cá nhân hoặc tỷ lệ tổ tiên phổ quát. Nguồn khoa học xem SCIENCE_REFERENCES.md trong project và bộ tài liệu chủ đề4.

FINAL_VIDEO_QA.json lưu kiểm tra1380giây,33.120frame, một đường tiếng,15điểm đối chiếu dạng sóng với voice Anh gốc, phụ đề đủ3648từ, loudness và giải mã toàn bộ. Kiểm tra hình bằng contact sheet115nguồn,13cảnh nhóm người ở ba thời điểm, mở đầu, đồ họa, các chương và kết. Không tuyên bố đã xem thủ công liên tục toàn bộ23phút.

YANA_04_EDIT_PROJECT.zip chứa kế hoạch dựng, code, đồ họa, overlays, phụ đề, hồ sơ nguồn, ảnh kiểm tra, nền bản đồ và voice Anh gốc. Không đóng lại133clip nguồn. Khi chuyển máy, ánh xạ lại đường dẫn clip trong inventory.json và đường dẫn đầu vào của các script. ZIP giữ script_inputs và original_english_voice để phục hồi dự án.

17voice các ngôn ngữ vẫn giữ tại https://github.com/seotro95/seotro/releases/tag/yana-video-04-23min
Voice Anh nguồn SHA256:7014702fdb86744e8ddbf8a74eb7ef176bbb4cb9865aaf4e0e7931e27ae0047c.
Video tham chiếu nhịp kể/dựng do người dùng cung cấp SHA256:f1a8659dbccd4db12a79e3c18ea2e1fe08f46f7a03c42bc2250f454f69eff70c.
'''
(O/'README.md').write_text(readme)
with zipfile.ZipFile(O/'YANA_04_EDIT_PROJECT.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in ['inventory.py','build_plan.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','package_delivery.py','inventory.json','INVENTORY_SUMMARY.json','DUPLICATES.json','EDIT_PLAN.json','EDITOR_DECISIONS.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json','chapters.ffmetadata']:
  
  if name=='inventory.json':z.writestr(name,json.dumps([{k:v for k,v in x.items() if k!='file_id'} for x in inv],ensure_ascii=False,indent=2))
  else:z.write(R/name,name)
 for folder in ['graphics','overlays','review','frames']:
  for p in (R/folder).glob('*'):
   if p.is_file():z.write(p,str(p.relative_to(R)))
 for p in O.iterdir():
  if p.suffix in ['.json','.csv','.txt','.srt','.md']:z.write(p,'delivery/'+p.name)
 for name in ['SCENES_AND_PROMPTS.json','CHAPTERS_12.csv','UNIQUE_PROMPTS_120.json']:z.write(R.parent/'package'/name,'script_inputs/'+name)
 z.write(R.parent/'verified-release/YANA_04_My_Tieng_Anh.mp3','original_english_voice/YANA_04_My_Tieng_Anh.mp3')
 z.write(R.parent/'package/NGUON_KIEM_CHUNG.md','SCIENCE_REFERENCES.md');z.write(R.parent/'make_reference_maps.py','references/make_reference_maps.py')
 for p in (R.parent/'package/REFERENCES').glob('*'):
  if p.is_file():z.write(p,'REFERENCES/'+p.name)
with zipfile.ZipFile(O/'YANA_04_EDIT_PROJECT.zip') as z:assert z.testzip() is None
(O/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(O.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt')+'\n')
print(json.dumps({'files':[(p.name,p.stat().st_size) for p in sorted(O.iterdir())]},ensure_ascii=False),flush=True)
