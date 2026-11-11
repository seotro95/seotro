import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];sha=os.environ['GITHUB_SHA'];base=f'https://raw.githubusercontent.com/{repo}/{sha}/productions/HANDOFF/'
with urllib.request.urlopen(base+'HANDOFF_ASSETS.json',timeout=60) as f:raw=f.read()
manifest=json.loads(raw);assert manifest['release_tag']=='science-series-handoff-20261111'
out=Path('handoff-delivery');out.mkdir(exist_ok=True);(out/'HANDOFF_ASSETS.json').write_bytes(raw)
for item in manifest['assets']:
 assert Path(item['name']).name==item['name']
 with urllib.request.urlopen(base+item['name'],timeout=60) as f:data=f.read()
 assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
 (out/item['name']).write_bytes(data)
tag=manifest['release_tag']
notes='Hồ sơ chuyển dự án sang tài khoản ChatGPT khác:ZIP186tệp,danh sách100chủ đề,tiến độ,cấu hình17giọng,tài liệu và quy trình chủ đề19,prompt khởi động. Kèm link các video/voice đã giao. Không kèm rawclip,ảnh trích,model lớn hoặc thông tin đăng nhập. Tài khoản mới cần kết nối GitHub riêng khi ghi/chạy Actions và gửi lại clip nguồn khi cần dựng lại.'
if subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True).returncode:
 subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',sha,'--title','Bàn giao dự án100chủ đề — chuyển tài khoản ChatGPT','--draft','--notes',notes],check=True)
for p in sorted(out.iterdir()):subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--draft=false','--latest=false'],check=True)
print('Handoff bundle and startup prompt verified and published',flush=True)
