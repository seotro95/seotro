import hashlib,json,os,subprocess
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';TAG='qanat-moi-030-22m42s';REPO='seotro95/seotro'
def gh(*a):return subprocess.run(['gh',*a,'--repo',REPO],check=True)
q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['target_seconds']==1362 and q['unique_prompts']==150
found=subprocess.run(['gh','release','view',TAG,'--repo',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if found.returncode:gh('release','create',TAG,'--target',os.environ['GITHUB_SHA'],'--title','MỚI-030 Qanat — tài liệu 22:42','--notes-file',str(D/'README.md'),'--latest=false')
files=sorted((D/'PROMPTS').glob('*.txt'))+[R/'QANAT_MOI030_TAI_LIEU_22m42s.zip',R/'QANAT_MOI030_PROMPT_15_TXT.zip']
files += [D/n for n in ['KICH_BAN_EN_22m42s.txt','KICH_BAN_EN_CO_MOC.txt','en-US.srt','5_TIEU_DE_VA_THUMBNAIL.txt','NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','DOCUMENT_QA.json','TIMELINE_144_CANH.csv','OPENING_10_SHOTS_30s.json','BACKUP_145_150.json','README.md']]
p=R/'DOCUMENT_DELIVERY_STATE.json';p.write_text(json.dumps(dict(documents_published=True,target_seconds=1362,full_voices_published=False),indent=2)+'\n');files.append(p)
for p in files:gh('release','upload',TAG,str(p),'--clobber')
record=dict(topic_id='MOI-030',stage='documents_published_audio_pending',target_seconds=1362,assets=[dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
p=D/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');gh('release','upload',TAG,str(p),'--clobber')
print('QANAT_DOCUMENTS_READY',flush=True)
