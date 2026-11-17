import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';REPO='seotro95/seotro';TAG='stonehenge-moi-027-21m32s'
def gh(*a,**kw):return subprocess.run(['gh',*a,'--repo',REPO],check=True,**kw)
q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['target_seconds']==1292 and q['unique_prompts']==140
found=subprocess.run(['gh','release','view',TAG,'--repo',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if found.returncode:
    gh('release','create',TAG,'--target',__import__('os').environ['GITHUB_SHA'],'--title','MỚI-022 Stonehenge — tài liệu 21:32','--notes-file',str(D/'README.md'),'--latest=false')
files=[R/'STONEHENGE_MOI027_PROMPT_NGOAI_TROI_14_TXT.zip']+sorted((D/'PROMPTS').glob('*.txt'))+[R/'STONEHENGE_MOI027_TAI_LIEU_21m32s.zip']
files += [D/n for n in ['KICH_BAN_EN_21m32s.txt','KICH_BAN_EN_CO_MOC.txt','en-US.srt','5_TIEU_DE_VA_THUMBNAIL.txt','NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','DOCUMENT_QA.json','TIMELINE_137_CANH.csv','OPENING_10_SHOTS_30s.json','BACKUP_138_140.json','README.md']]
state=dict(documents_published=True,target_seconds=1292,full_voices_published=False)
(R/'DOCUMENT_DELIVERY_STATE.json').write_text(json.dumps(state,indent=2)+'\n')
files.append(R/'DOCUMENT_DELIVERY_STATE.json')
for p in files:
    gh('release','upload',TAG,str(p),'--clobber')
manifest=dict(topic_id='MOI-027',stage='documents_published_voice_rendering_pending',target_seconds=1292,assets=[dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
p=D/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');gh('release','upload',TAG,str(p),'--clobber')
print('ROMAN_DOCUMENTS_READY',flush=True)
