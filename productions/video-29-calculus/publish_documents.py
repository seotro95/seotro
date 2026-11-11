from pathlib import Path
import os,json,subprocess,hashlib,zipfile
R=Path(__file__).resolve().parent;D=R/'documents';repo=os.environ['GITHUB_REPOSITORY'];tag='dental-calculus-video-29-21m42s';out=R/'document-release';out.mkdir(exist_ok=True)
qa=json.loads((D/'DOCUMENT_QA.json').read_text());assert qa['target_seconds']==1302 and qa['unique_prompts']==130 and qa['txt_files']==13
files=sorted(p for p in D.rglob('*') if p.is_file())
manifest={str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(out/'DOCUMENT_SHA256SUMS.txt').write_text(''.join(f'{s}  {p}\n' for p,s in manifest.items()))
archive=out/'CALCULUS_29_TAI_LIEU_21m42s.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.relative_to(D))
base=f'https://github.com/{repo}/releases/download/{tag}/'
notes=f'''# Cao răng cổ — chủ đề29 — tài liệu21:42

**Tên phim:** Dental Calculus: The Smallest Archive.

Đã chuẩn bị kịch bản tiếng Anh3344từ,131mốc hình và130prompt mới, chia13TXT×10prompt đánh số1–130. Mốc131dùng2giây của clip1; không thêm thời lượng. Mỗi clip tạo10giây. Prompt không có trẻ em ở bất kỳ vị trí nào và yêu cầu video hoàn toàn im lặng.

[Tải bộ tài liệu,13TXT,kịch bản,timeline,nguồn và hồ sơ17giọng]({base}{archive.name})

Phân tích nguồn dựa trên metadata, lấy mẫu khung hình và hồ sơ chuỗi. Không tuyên bố xem/nghe tay liên tục toàn bộ. Mọi hình khoa học tạo sinh là mô hình minh họa; dùng dữ liệu đã kiểm khi thêm nhãn trongeditor.

**Voice:** đang chuẩn bị, chưa ghi nhận đã hoàn thành17bản. Giữ16nam vàH’mông nữfemale-3, đúnghai toolbackend đã khóa. Tổng mỗi bản sẽ được đo theo mục tiêu1302giây. Bản dịch cần kiểm biên tập/nghe độc lập, nhất là phương ngữH’mông Trắng.

'''
for p in sorted((D/'PROMPTS').glob('*.txt')):notes+=f'- [{p.stem}]({base}{p.name})\n'
(out/'DOCUMENT_RELEASE_NOTES.md').write_text(notes)
def gh(*args):subprocess.run(['gh',*args,'--repo',repo],check=True)
exists=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True).returncode==0
if not exists:gh('release','create',tag,'--target',os.environ['GITHUB_SHA'],'--title','Cao răng cổ — chủ đề29 — tài liệu21:42','--draft','--notes-file',str(out/'DOCUMENT_RELEASE_NOTES.md'))
for p in [archive,out/'DOCUMENT_SHA256SUMS.txt',D/'KICH_BAN_EN_21m42s.txt',D/'PHAN_TICH_VIDEO_NGUON.md',D/'NGUON_KIEM_CHUNG.md',*sorted((D/'PROMPTS').glob('*.txt'))]:gh('release','upload',tag,str(p),'--clobber')
if '[docs29]' in os.environ.get('COMMIT_MESSAGE','') or not exists:gh('release','edit',tag,'--draft=false','--latest=false','--notes-file',str(out/'DOCUMENT_RELEASE_NOTES.md'))
(R/'DOCUMENT_DELIVERY_STATE.json').write_text(json.dumps({'topic':29,'target_seconds':1302,'release_tag':tag,'production_head':os.environ['GITHUB_SHA'],'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'status':'documents_published'},indent=2))
print('Published documents:',f'https://github.com/{repo}/releases/tag/{tag}',flush=True)
