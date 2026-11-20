import hashlib,json,os,subprocess
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';C=json.loads((R/'EPISODE.json').read_text());TAG=C['release_tag'];REPO='seotro95/seotro'
def gh(*args):subprocess.run(['gh',*map(str,args),'--repo',REPO],check=True)
q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['target_seconds']==C['target_seconds'] and q['unique_prompts']==C['prompt_count']
found=subprocess.run(['gh','release','view',TAG,'--repo',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if found.returncode:gh('release','create',TAG,'--target',os.environ['GITHUB_SHA'],'--title','MỚI-061 Richat — tài liệu 21:42','--notes-file',D/'README.md','--latest=false')
files=sorted((D/'PROMPTS').glob('*.txt'))+[R/f"{C['prefix']}_TAI_LIEU_{C['duration_label']}.zip",R/f"{C['prefix']}_PROMPT_{C['prompt_txt_files']}_TXT.zip"]
files += [D/n for n in ['KICH_BAN_EN_21m42s.txt','KICH_BAN_EN_CO_MOC.txt','en-US.srt','5_TIEU_DE_VA_THUMBNAIL.txt','NGUON_KIEM_CHUNG.md','PHAN_TICH_VA_KE_HOACH_DUNG.md','DOCUMENT_QA.json','RETENTION_QA.json','RETENTION_RULES_LOCKED.json','TIMELINE_134_CANH.csv','OPENING_6_SHOTS_30s.json','BACKUP_135_140.json','README.md','SOURCE_ASSET_MANIFEST.json']]
files.append(D/'REFERENCE_ASSETS'/'richat_landsat_2026.jpg')
p=R/'DOCUMENT_DELIVERY_STATE.json';p.write_text(json.dumps(dict(documents_published=True,target_seconds=C['target_seconds'],full_voices_published=False),indent=2)+'\n');files.append(p)
for p in files:gh('release','upload',TAG,p,'--clobber')
record=dict(topic_id=C['topic_id'],stage='documents_published_audio_pending',target_seconds=C['target_seconds'],assets=[dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
p=D/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');gh('release','upload',TAG,p,'--clobber')
print('RICHAT_DOCUMENTS_READY',flush=True)
