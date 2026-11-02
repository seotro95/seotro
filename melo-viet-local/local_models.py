"""Checksum-pinned optional CPU models, shared by native multilingual readers."""
import hashlib,json,os,shutil,tarfile,tempfile,time,urllib.request
from pathlib import Path,PurePosixPath
VERIFIED=set()
def catalog():return json.loads(Path(__file__).with_name('multi_catalog.json').read_text(encoding='utf-8'))
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()
def verify(folder,record):return all((folder/n).is_file() and digest(folder/n)==sha for n,sha in record['files'].items())
def ensure(key,offline=False):
    record=catalog()[key];root=Path(os.environ.get('MELO_VIET_ROOT',Path.home()/'.local/share/melo-viet-local'))/'models';root.mkdir(parents=True,exist_ok=True)
    folder=root/key
    if str(folder) in VERIFIED:return folder
    if verify(folder,record):VERIFIED.add(str(folder));return folder
    if offline:raise ValueError('Chưa có đủ mô hình '+record['name']+'. Dùng bản cập nhật kèm giọng hoặc mở MO_TOOL.bat có Internet để tải một lần.')
    with tempfile.TemporaryDirectory(prefix=key+'-',dir=root) as scratch:
        scratch=Path(scratch);archive=scratch/'model.tar';staged=scratch/'files';staged.mkdir()
        for attempt in range(3):
            try:
                req=urllib.request.Request(record['archive_url'],headers={'User-Agent':'Melo-Viet-Studio/1.3.0'})
                with urllib.request.urlopen(req,timeout=90) as src,archive.open('wb') as dst:
                    received=0
                    while block:=src.read(1024*1024):
                        received+=len(block)
                        if received>record['archive_bytes']:raise ValueError('Kích thước mô hình không khớp.')
                        dst.write(block)
                if archive.stat().st_size!=record['archive_bytes'] or digest(archive)!=record['archive_sha256']:raise ValueError('SHA256 mô hình không khớp.')
                break
            except (OSError,ValueError) as e:
                if attempt==2:raise RuntimeError('Không tải được '+record['name']+'. Kiểm tra kết nối GitHub hoặc dùng bản cập nhật kèm giọng.') from e
                time.sleep(attempt+1)
        with tarfile.open(archive,'r:*') as tar:
            for member in tar:
                parts=PurePosixPath(member.name).parts
                if len(parts)==2 and parts[0]==record['archive_prefix'] and parts[1] in record['files'] and member.isfile():
                    if member.size>250*1024*1024:raise ValueError('Thành phần mô hình quá lớn.')
                    with tar.extractfile(member) as src,(staged/parts[1]).open('wb') as dst:shutil.copyfileobj(src,dst,1024*1024)
        if not verify(staged,record):raise ValueError('Mô hình tải về thiếu hoặc sai mã xác minh.')
        folder.mkdir(exist_ok=True)
        for name in record['files']:
            tmp=folder/(name+'.'+str(os.getpid())+'.partial');shutil.copyfile(staged/name,tmp);tmp.replace(folder/name)
    VERIFIED.add(str(folder));return folder
