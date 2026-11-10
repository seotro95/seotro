import csv,hashlib,json,os,shutil,zipfile
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';qa=json.load(open(O/'FINAL_VIDEO_QA.json'));assert qa['status']=='passed';src=json.load(open(R/'SOURCE_MANIFEST.json'));dec=json.load(open(R/'EDITOR_DECISIONS.json'))
for n in ['EDITOR_DECISIONS.json','SOURCE_MANIFEST.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json']:shutil.copy(R/n,O/n)
with (O/'SOURCE_CLIP_MANIFEST.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['label','source_filename','bytes','sha256','original_audio_present'])
 for x in src['clips']:w.writerow([x['label'],x['source_name'],x['bytes'],x['sha256'],x['source_audio']])
text=(R/'TITLES_AND_THUMBNAIL_PROMPTS.txt').read_text(encoding='utf-8-sig');assert text.count('TITLE EN:')==5 and text.count('PROMPT:')==5
(O/'DENISOVA_06_TITLES_THUMBNAILS.txt').write_text(text,encoding='utf-8-sig')
with zipfile.ZipFile(O/'DENISOVA_06_TITLES_THUMBNAILS.zip','w',zipfile.ZIP_DEFLATED) as z:z.write(O/'DENISOVA_06_TITLES_THUMBNAILS.txt','DENISOVA_06_TITLES_THUMBNAILS.txt')
base='https://github.com/seotro95/seotro/releases/download/denisova-video-06-final-21min/'
readme='''# Denisova — chủ đề 6, bản dựng hoàn chỉnh 21:00

Video 1280×720, 24 fps; chỉ voice tiếng Anh đã chốt, không có tiếng clip, nhạc nền hoặc hiệu ứng âm thanh. Giữ nguyên lời, nhịp và cao độ; chỉ chuẩn hóa độ lớn khi xuất. 12 shot trong 30 giây đầu nằm trong tổng 21 phút, không cộng intro.

'''
readme+=f'[Tải video hoàn chỉnh]({base}DENISOVA_06_EN_FINAL_21m_720p.mp4) · [Xem mở đầu 30 giây]({base}DENISOVA_06_OPENING_30s.mp4)\n\n'
readme+=f'[5 tiêu đề và 5 prompt thumbnail — TXT]({base}DENISOVA_06_TITLES_THUMBNAILS.txt) · [ZIP dự phòng cho TXT]({base}DENISOVA_06_TITLES_THUMBNAILS.zip) · [Dự án dựng]({base}DENISOVA_06_EDIT_PROJECT.zip)\n\n'
readme+='Dự án không kèm clip gốc. Dùng lại các clip bạn đã gửi theo SOURCE_CLIP_MANIFEST.csv; tất cả clip gốc vẫn được giữ trong phiên làm việc.\n\n'
readme+='Có phụ đề Anh tùy chọn trong MP4 và tệp SRT riêng. Bộ dựng dùng cảnh đã chọn từ 104 clip và đồ họa giải thích; 33 clip có tiếng gốc nhưng mọi tiếng clip đều bị loại. Sáu ô thiếu clip được xử lý bằng bản đồ đã đối chiếu và cảnh phù hợp. Không có hình trẻ em trong các cảnh được chọn qua kiểm tra mẫu khung hình.\n\n'
readme+='Bản đồ chỉ định hướng địa lý hiện đại, không phải tuyến di cư hoặc bờ biển cổ. Mẫu xương, cảnh thao tác và mô hình là minh họa, không phải ảnh gốc của hóa thạch hay chân dung Denisovan đã xác nhận. Đồ họa gene là sơ đồ giải thích, không phải số liệu đo.\n\n'
readme+='Đã kiểm tra 30.240 khung hình, đúng 21:00, một đường tiếng Anh, giải mã toàn bộ, khoảng đen và 15 điểm đồng bộ sóng âm. Kiểm tra hình bằng mẫu khung hình, không tuyên bố xem tay liên tục toàn bộ 21 phút.\n\n'
readme+='[17 voice riêng đã bàn giao](https://github.com/seotro95/seotro/releases/tag/denisova-video-06-21min). Bản dịch và phương ngữ H’Mông trắng vẫn cần người bản ngữ rà soát độc lập.\n'
(O/'README.md').write_text(readme)
with zipfile.ZipFile(O/'DENISOVA_06_EDIT_PROJECT.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in ['build_plan.py','render_edit.py','assemble_final.py','qa_final.py','review_final.py','package_delivery.py','EDIT_PLAN.json','inventory_cloud.json','INVENTORY_SUMMARY.json','EDITOR_DECISIONS.json','SOURCE_MANIFEST.json','SCENE_VERIFICATION.json','FINAL_EXPORT_COMMAND.json']:
  if (R/n).exists():z.write(R/n,'edit/'+n)
 for folder in ['graphics','overlays','input']:
  for p in (R/folder).rglob('*'):
   if p.is_file() and p.suffix!='.zip':z.write(p,'edit/'+str(p.relative_to(R)))
 for p in O.iterdir():
  if p.is_file() and p.suffix not in ['.mp4','.zip']:z.write(p,'delivery/'+p.name)
 for p in (R.parent/'package').rglob('*'):
  if p.is_file():z.write(p,'package/'+str(p.relative_to(R.parent/'package')))
 for n in ['NGUON_KIEM_CHUNG.md','NGUON_KIEM_CHUNG.csv','DOI_CHIEU_KHOA_HOC.csv','REFERENCES/REFERENCE_GUIDE.json']:
  if (R.parent/'package'/n).exists():z.write(R.parent/'package'/n,'sources/'+n)
 if Path('.github/workflows/siberia-final-video.yml').exists():z.write('.github/workflows/siberia-final-video.yml','GITHUB_ACTIONS_WORKFLOW.yml')
rows=[]
for p in sorted(O.iterdir()):
 if p.is_file() and p.suffix!='.jpg' and p.name not in ['SHA256SUMS.txt','RELEASE_ASSET_MANIFEST.json']:rows.append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
(O/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in rows));(O/'RELEASE_ASSET_MANIFEST.json').write_text(json.dumps({'topic':6,'render_location':'local','render_pipeline_sha256':hashlib.sha256((R/'render_edit.py').read_bytes()).hexdigest(),'assets':rows},indent=2));print(json.dumps({'delivery_files':len(rows),'final_bytes':qa['bytes'],'project_bytes':(O/'DENISOVA_06_EDIT_PROJECT.zip').stat().st_size}),flush=True)
