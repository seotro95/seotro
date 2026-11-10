import hashlib,json,os,shutil,subprocess,zipfile
from pathlib import Path
P=Path('productions/video-19-kostenki');O=Path('document-delivery');O.mkdir(exist_ok=True)
REPO=os.environ['GITHUB_REPOSITORY'];TAG='kostenki-video-19-20m15s'
assert REPO=='seotro95/seotro'
archive=P/'KOSTENKI_VIDEO_19_TAI_LIEU_20m15s.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='1c08af370717dfb79b7fb47f20639ffb05a7f1dd62b539dd1f9770bf88ba7ed9'
with zipfile.ZipFile(archive) as z:assert not any(n.endswith(('.mp4','.wav','.mp3','.pdf')) for n in z.namelist())
shutil.copyfile(archive,O/archive.name)
for p in [P/'KICH_BAN_EN_20m15s.txt',P/'KICH_BAN_EN_CO_MOC.txt',P/'PHAN_TICH_NGUON_VA_QUY_TRINH.txt',P/'HUONG_DAN_20m15s.txt']+sorted((P/'PROMPTS').glob('*.txt')):
    shutil.copyfile(p,O/('KOSTENKI_19_'+p.name))
notes='''# Chủ đề 19 — Nhà bằng xương voi ma mút — 20:15

Kostenki: The House That Remains a Question. Tài liệu được bàn giao trước khi tạo voice: kịch bản Anh 2.816 từ, 122 mốc gồm 121×10giây và mốc kết5giây.120prompt mới trong12TXT,đúng10prompt/tệp,2mốcREUSE cóCSV đánh dấu. Mỗi prompt tạo clip10giây,không hình trẻ em,và kết thúc bằng cụm “không có âm thanh”. Clip cuối dùng5giây khi dựng để đúng20:15.

ZIP gồm kịch bản sạch/có mốc,SRT,timeline,12TXTprompt,shotlist,hook30giây,phân tích phong cách và nguồn kiểm chứng. Các TXT cũng có link tải riêng tại Assets. Không kèm video/ảnh/bài báo nguồn hoặc mã tệp riêng tư.

Nguồn: Pryor etal.2020;Rey-Iglesia etal.2025;Chu,Shydlovskyi,Maier2025 và phương pháp định tuổi từOxford/PennState. Mái che và chức năng của mỗi cấu trúc là các giả thuyết cần đối chiếu;không gộp mọi di chỉ cùng niên đại,không biến khoảng tuổi thành số năm cư trú liên tục. Hình tạo mới dùng mô hình/diễn viên trưởng thành,không coi là ảnh khảo cổ xác thực.

17voice đang chuẩn bị,cùng ID/style đã lưu:16nam,H’MôngTrắngnữ3. Chưa có clip và chưa dựng video19. Các tập đã bàn giao được giữ nguyên.
'''
(O/'NOTES.md').write_text(notes)
if subprocess.run(['gh','release','view',TAG,'--repo',REPO],capture_output=True).returncode:
    subprocess.run(['gh','release','create',TAG,'--repo',REPO,'--target',os.environ['GITHUB_SHA'],'--title','Kostenki Topic19 —20m15s script and120 silent prompts','--draft','--notes-file',str(O/'NOTES.md')],check=True)
for p in O.iterdir():
    if p.suffix in ['.txt','.zip']:subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--notes-file',str(O/'NOTES.md'),'--draft=false','--latest=false'],check=True)
print('Topic19 documents published;17voices not yet claimed.',flush=True)
