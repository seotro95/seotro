"""Publish verified delivery records without changing any completed audio."""
import hashlib,json,os,subprocess,urllib.request,zipfile
from pathlib import Path

R=Path(__file__).parent
TAG='homo-luzonensis-video-85-21m22s'
REPO='seotro95/seotro'
BASE=f'https://github.com/{REPO}/releases/download/{TAG}/'
ZIP='HOMO_LUZONENSIS_85_TAI_LIEU_21m22s.zip'
AUDIOZIP='HOMO_LUZONENSIS_85_17_VOICES_21m22s.zip'
qa=json.loads((R/'PUBLIC_DOWNLOAD_QA.json').read_text())
assert qa['status']=='passed' and qa['topic_id']==85 and qa['voice_count']==17
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
assets={a['name']:a for a in release['assets']}
assert assets[AUDIOZIP]['digest']=='sha256:'+qa['public_voice_archive_sha256']
for v in qa['voices']:assert assets[v['filename']]['digest']=='sha256:'+v['sha256']
data=urllib.request.urlopen(BASE+ZIP,timeout=90).read()
assert hashlib.sha256(data).hexdigest()==assets[ZIP]['digest'].removeprefix('sha256:')
archive=R/ZIP;archive.write_bytes(data)
D=R/'verified_documents';D.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for x in z.infolist():
        dest=(D/x.filename).resolve();assert dest.is_relative_to(D.resolve())
        if x.is_dir():continue
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(x))
for n in ['PUBLIC_DOWNLOAD_QA.json','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md']:(D/n).write_bytes((R/n).read_bytes())
readme=D/'README.md'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(D.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(D))
def upload(p):
    subprocess.run(['gh','release','upload',TAG,str(p),'--repo',REPO,'--clobber'],check=True)
    print('DELIVERY_METADATA_PUBLISHED',p.name,flush=True)
for p in [archive,*[D/n for n in ['PUBLIC_DOWNLOAD_QA.json','5_TIEU_DE_VA_THUMBNAIL.txt','PRODUCTION_STEPS_APPLIED.md','README.md','HUONG_DAN_SU_DUNG.txt']]]:upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
manifest={'topic_id':85,'target_seconds':1282,'stage':'all17voices_and_documents_public_download_verified','self_and_checksum_file_excluded':True,'assets':[{'name':a['name'],'bytes':a['size'],'sha256':a['digest'].removeprefix('sha256:')} for a in release['assets'] if a['name'] not in ['DOCUMENT_ASSET_MANIFEST.json','SHA256SUMS.txt'] and not a['name'].endswith('.mp3')]}
p=R/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));upload(p)
release=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{TAG}']))
p=R/'SHA256SUMS.txt';p.write_text(''.join(a['digest'].removeprefix('sha256:')+'  '+a['name']+'\n' for a in sorted(release['assets'],key=lambda a:a['name']) if a['name']!='SHA256SUMS.txt'));upload(p)
assert next(a for a in release['assets'] if a['name']==AUDIOZIP)['digest']=='sha256:'+qa['public_voice_archive_sha256']
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--notes-file',str(readme),'--latest=false'],check=True)
print('VERIFIED_TOPIC85_DELIVERY_METADATA_COMPLETE',flush=True)
