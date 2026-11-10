import csv,hashlib,json,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery'
qa=json.loads((O/'FINAL_VIDEO_QA.json').read_text());assert qa['status']=='passed'
review=json.loads((R/'VISUAL_REVIEW_APPROVED.json').read_text());assert review.get('final_movie_review_status')=='passed'
source=json.loads((R/'SOURCE_MANIFEST.json').read_text())
for name in ['EDITOR_DECISIONS.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json','VISUAL_REVIEW_APPROVED.json']:
    shutil.copyfile(R/name,O/name)
safe_source={'topic':8,'clips':[{k:x[k] for k in ['label','source_name','bytes','sha256','source_audio']} for x in source['clips']],
             'private_upload_ids_and_uris_included':False,'raw_source_media_included':False}
(O/'SOURCE_MANIFEST.json').write_text(json.dumps(safe_source,ensure_ascii=False,indent=2))
safe_inventory=[{k:x[k] for k in ['label','clip_id','path','sha256','seconds']} for x in json.loads((R/'inventory_cloud.json').read_text())]
with (O/'SOURCE_CLIP_MANIFEST.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['label','source_filename','bytes','sha256','original_audio_present'])
    for x in source['clips']:w.writerow([x['label'],x['source_name'],x['bytes'],x['sha256'],x['source_audio']])
text=(R/'TITLES_AND_THUMBNAIL_PROMPTS.txt').read_text(encoding='utf-8-sig')
assert text.count('TITLE EN:')==5 and text.count('PROMPT:')==5
(O/'BAISHIYA_08_TITLES_THUMBNAILS.txt').write_text(text,encoding='utf-8-sig')
with zipfile.ZipFile(O/'BAISHIYA_08_TITLES_THUMBNAILS.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(O/'BAISHIYA_08_TITLES_THUMBNAILS.txt','BAISHIYA_08_TITLES_THUMBNAILS.txt')
base='https://github.com/seotro95/seotro/releases/download/baishiya-video-08-final-22m20s/'
readme='''# Baishiya — chủ đề 8 — bản dựng hoàn chỉnh 22:20

Video 1280×720, 24 fps, 32.160 khung hình. Chỉ voice tiếng Anh đã lưu (en-US-AndrewNeural); không tiếng clip gốc, nhạc nền hoặc hiệu ứng âm thanh. Giữ nguyên lời, nhịp, thời lượng và cao độ; chỉ chuẩn hóa độ lớn âm thanh khi xuất. 12 cảnh trong 30 giây đầu, nằm trong tổng thời lượng 22:20.

'''
readme+=f'[Tải video hoàn chỉnh]({base}BAISHIYA_08_EN_FINAL_22m20s_720p.mp4) · [Mở đầu 30 giây]({base}BAISHIYA_08_OPENING_30s.mp4)\n\n'
readme+=f'[5 tiêu đề và 5 prompt thumbnail — TXT]({base}BAISHIYA_08_TITLES_THUMBNAILS.txt) · [ZIP dự phòng cho TXT]({base}BAISHIYA_08_TITLES_THUMBNAILS.zip) · [Dự án dựng]({base}BAISHIYA_08_EDIT_PROJECT.zip)\n\n'
readme+='Có phụ đề Anh tùy chọn trong MP4 và SRT riêng, 12 chương. Dùng 91 clip đã chọn trong 114 clip gửi mới, 19 đồ họa giải thích và 7 chuyển cảnh hòa hình ngắn. Toàn bộ 35 đường tiếng clip gốc được loại. Sáu mã prompt thiếu được xử lý bằng cảnh đã kiểm tra và đồ họa phù hợp.\n\n'
readme+='Dự án không kèm video gốc, proxy hoặc ảnh trích từ video nguồn. Các bản tải lên gốc trong cuộc trò chuyện không thay đổi; bộ nhớ đệm tải về cục bộ được thu hồi sau khi kiểm tra mã băm để tiết kiệm dung lượng. Dùng SOURCE_CLIP_MANIFEST.csv và link_sources.py với các clip bạn đã tải để dựng lại.\n\n'
readme+='Cảnh vật, người trưởng thành và thao tác là hình minh họa; mẫu hàm và dấu vết được ghi là mẫu giảng giải, không phải ảnh xác thực của hóa thạch Xiahe. Không có hình trẻ em trong các cảnh được chọn qua kiểm tra mẫu khung hình. Kiểm tra hình là lấy mẫu ở đầu, giữa và gần cuối từng clip, cùng mẫu bản dựng, không phải xem tay liên tục toàn bộ phim.\n\n'
readme+='Đồ họa bảo toàn các giới hạn nghiên cứu: tuổi tối thiểu của hàm Xiahe; niên đại lớp chứa Xiahe 2 không phải ngày tử vong; nguồn gốc xương bị đốt chưa rõ; không khẳng định cư trú liên tục hoặc có bộ gene hoàn chỉnh của các cá thể Xiahe. Bản đồ Natural Earth chỉ định hướng địa lý hiện đại, không phải tuyến di cư.\n\n'
readme+='Đã giải mã toàn bộ video, kiểm tra khoảng đen, đúng thời lượng và số khung hình, một đường tiếng Anh, độ lớn/đỉnh âm và 15 điểm đồng bộ sóng âm với voice gốc. Xem FINAL_VIDEO_QA.json để biết số đo.\n\n'
readme+='[17 voice riêng đã bàn giao](https://github.com/seotro95/seotro/releases/tag/baishiya-video-08-22m20s). Tất cả voice cũ được giữ; video này chỉ sử dụng bản tiếng Anh.\n'
(O/'README.md').write_text(readme)
instructions='''DỰNG LẠI CHỦ ĐỀ 8 — BAISHIYA 22:20

Yêu cầu Python 3.11+, ffmpeg/ffprobe có libx264, Pillow, numpy; font DejaVu Sans. Script render mặc định dùng font Linux /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf; nếu dựng trên Windows, chép DejaVuSans.ttf vào thư mục edit và đặt font_path trong render_edit.py thành ./DejaVuSans.ttf để tránh dấu hai chấm của đường dẫn ổ đĩa trong bộ lọc ffmpeg.

1. Giải nén, mở terminal trong thư mục edit.
2. python link_sources.py /thu-muc-chua-cac-clip-goc
   Script chỉ sao chép clip cần dùng, kiểm tra SHA-256; không di chuyển hoặc sửa bản gốc.
3. python render_edit.py --start 1 --end 134 --workers 2
4. python assemble_final.py
5. python qa_final.py

Giữ nguyên EDIT_PLAN.json, graphics, overlays và input để tái lập bản đã giao. assemble_final.py xóa các bản scene xuất trung gian có thể tạo lại sau khi đã ghép, có khoảng đệm an toàn 60 giây; không xóa clip nguồn. Cần khoảng 2 GB trống để dựng lại thoải mái. Không chạy build_plan.py nếu chỉ muốn tái lập: đồ họa đã được đóng gói sẵn, không cần tải thêm dữ liệu bản đồ.

Input voice: BAISHIYA_08_My_Tieng_Anh.mp3, SHA-256 14131b625739f903c4f165a02ffc60c5d54b9f09dd628cf92a13f64477e222c4.
Khung thời gian: 134 đoạn × 10 giây, 22:20; tiếng clip bị loại ngay trong render, chỉ map voice tiếng Anh khi ghép cuối.
'''
(O/'HUONG_DAN_DUNG_LAI.txt').write_text(instructions,encoding='utf-8-sig')
with zipfile.ZipFile(O/'BAISHIYA_08_EDIT_PROJECT.zip','w',zipfile.ZIP_DEFLATED) as z:
    names=['build_plan.py','link_sources.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','package_delivery.py','EDIT_PLAN.json','inventory_cloud.json','INVENTORY_SUMMARY.json','EDITOR_DECISIONS.json','SOURCE_MANIFEST.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json','VISUAL_REVIEW_APPROVED.json']
    for n in names:
        if n=='SOURCE_MANIFEST.json':z.writestr('edit/'+n,json.dumps(safe_source,ensure_ascii=False,indent=2))
        elif n=='inventory_cloud.json':z.writestr('edit/'+n,json.dumps(safe_inventory,indent=2))
        elif (R/n).exists():z.write(R/n,'edit/'+n)
    for folder in ['graphics','overlays','input']:
        for p in (R/folder).rglob('*'):
            if p.is_file():z.write(p,'edit/'+str(p.relative_to(R)))
    for p in O.iterdir():
        if p.is_file() and p.suffix not in ['.mp4','.zip','.jpg','.png']:z.write(p,'delivery/'+p.name)
    for p in (R.parent/'package').rglob('*'):
        if p.is_file() and p.suffix not in ['.mp4','.mp3','.wav','.zip']:z.write(p,'package/'+str(p.relative_to(R.parent/'package')))
with zipfile.ZipFile(O/'BAISHIYA_08_EDIT_PROJECT.zip') as z:
    assert not any(n.endswith('.mp4') or n.startswith(('raw/','frames/','review/')) for n in z.namelist())
    import re
    pattern=re.compile(rb'file_[0-9a-f]{32}|/workspace/attachments/[0-9a-f]{8}-')
    for n in z.namelist():assert not pattern.search(z.read(n)),('Private source reference in project',n)
rows=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.suffix not in ['.jpg','.png'] and p.name not in ['SHA256SUMS.txt','RELEASE_ASSET_MANIFEST.json']:
        rows.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
(O/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in rows))
(O/'RELEASE_ASSET_MANIFEST.json').write_text(json.dumps({'topic':8,'render_location':'local','render_pipeline_sha256':hashlib.sha256((R/'render_edit.py').read_bytes()).hexdigest(),'assets':rows},indent=2))
print(json.dumps({'delivery_files':len(rows),'final_bytes':qa['bytes'],'project_bytes':(O/'BAISHIYA_08_EDIT_PROJECT.zip').stat().st_size}),flush=True)
