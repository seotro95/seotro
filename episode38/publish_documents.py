import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';repo='seotro95/seotro';tag='land-bridges-video-38-22m32s'
subprocess.run(['python',str(R/'build_documents.py')],check=True)
qa=json.loads((D/'DOCUMENT_QA.json').read_text());assert qa['status']=='passed' and qa['target_seconds']==1352
readme='''# Chủ đề 38 — Các cây cầu đất qua những chu kỳ băng hà — 22:32

Kịch bản Anh gốc: When the Sea Was Land: Earth's Vanishing Bridges. 3.581 từ; 136 mốc lời, gồm135đoạn10giây và2giây cuối. 120prompt tạo clip im lặng10giây, chia12TXT, mỗiTXT10prompt. 16mốc dùng lại đã ghi rõ trong timeline. Không có hình trẻ em hoặc thiếu niên. Không có lời nói, nhạc, âm thanh hoặc watermark trong clip yêu cầu.

Tải LAND_BRIDGES_38_TAI_LIEU_22m32s.zip để có kịch bản,12TXTprompt, SRTAnh, timeline, bản đồ dùng lại clip, phân tích nhịp video nguồn và nguồn kiểm chứng. Clip đặt tên theo IDprompt001–120; dùng timeline để xếp136mốc. Cuecuối chỉ lấy2giây. Không cộng thêm30giây mở đầu vào tổng22:32.

Giai đoạn hiện tại: đã bàn giao tài liệu.17voice riêng sẽ được bổ sung sau, giữ16giọng nam vàprofileH'môngnữfemale-3; chưa tuyên bố đã tạo đủvoice ở bước tài liệu. Footage vàvideo hoàn chỉnh chưa tạo. Các bản dịch vàgiọng H'mông cần kiểm tra nghe bản ngữ; kiểm tra kỹ thuật không phải chứng nhận phương ngữ.

Giữ nguyên17voiceIDđã khóa vàtham chiếu nữ. ToolMelo dùngbackendtrực tuyến của commit4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043; toolHmong1.6.6 ởcommit061430d958b8d5fc14d04209c6f0cd20492382c2.
'''
(D/'README.md').write_text(readme)
with __import__('zipfile').ZipFile(R/'LAND_BRIDGES_38_TAI_LIEU_22m32s.zip','w',__import__('zipfile').ZIP_DEFLATED) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
assets=[R/'LAND_BRIDGES_38_TAI_LIEU_22m32s.zip',D/'KICH_BAN_EN_22m32s.txt',D/'en-US.srt',D/'TIMELINE_136_CANH.csv',D/'CAC_CANH_DUNG_LAI.txt',D/'DOCUMENT_QA.json',D/'NGUON_KIEM_CHUNG.md',D/'PHAN_TICH_VIDEO_NGUON.md',D/'HUONG_DAN_SU_DUNG.txt',D/'README.md',*sorted((D/'PROMPTS').glob('*.txt'))]
checks=[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in assets]
(R/'DOCUMENT_ASSET_MANIFEST.json').write_text(json.dumps({'topic_id':38,'target_seconds':1352,'assets':checks},indent=2));assets.append(R/'DOCUMENT_ASSET_MANIFEST.json')
old=subprocess.run(['gh','release','view',tag,'--repo',repo,'--json','isDraft'],capture_output=True,text=True)
if old.returncode:
 subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',__import__('os').environ['GITHUB_SHA'],'--draft','--title','Chủ đề 38 — Cầu đất qua các chu kỳ băng hà — 22:32','--notes-file',str(D/'README.md')],check=True)
else:assert json.loads(old.stdout)['isDraft'],'Do not overwrite an existing published episode'
for p in assets:
 subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True);print('DOCUMENT_UPLOADED',p.name,flush=True)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--draft=false','--latest=false'],check=True)
print(json.dumps({'documents_published':True,'release_tag':tag,'target_seconds':1352,'voice_generation_started':False}),flush=True)
