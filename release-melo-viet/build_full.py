"""Build the full release from the reviewed small ZIP and checksum-pinned models."""
import hashlib,json,os,shutil,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
out=Path(os.environ['RELEASE_ASSETS']);out.mkdir(parents=True,exist_ok=True)
model_root=Path(os.environ['MELO_VIET_ROOT'])/'models/piper'
small=json.loads((HERE/'expected-package.json').read_text())
small_file=out/small['name'];shutil.copyfile(HERE/'package.zip',small_file)
shutil.copyfile(HERE/'package.sha256',out/(small['name']+'.sha256'))
full=out/'Melo-Viet-Studio-1.2.0-CPU-Day-Du-Windows.zip'
prefix='Melo-Viet-Cai-Rieng/'
catalog=json.loads((HERE.parent/'melo-viet-local/fast_catalog.json').read_text())['models']
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()
manifest=[]
with zipfile.ZipFile(full,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
    with zipfile.ZipFile(small_file) as source:
        for item in source.infolist():z.writestr(item,source.read(item.filename))
    for model in catalog:
        for name,sha in model['files'].items():
            file=model_root/model['id']/name
            assert digest(file)==sha, 'Unverified model file '+model['id']+'/'+name
            relative='models/piper/'+model['id']+'/'+name
            z.write(file,prefix+'voice-pack/'+relative);manifest.append(sha+'  '+relative+'\n')
    z.writestr(prefix+'voice-pack/MANIFEST.sha256',''.join(manifest))
    z.writestr(prefix+'voice-pack/DOC_TRUOC.txt','27 mo hinh Piper FP32 cho 24 tieng. CAP_NHAT.bat xac minh SHA256 va chep vao Ubuntu. Model cards/giay phep goc duoc giu lai. Thu vien van can cai lan dau.\n')
assert full.stat().st_size<2*1024**3, 'GitHub single asset size limit exceeded'
(out/(full.name+'.sha256')).write_text(digest(full)+'  '+full.name+'\n')
print('Full installer:',full.stat().st_size,'bytes;',len(catalog),'verified models',flush=True)
