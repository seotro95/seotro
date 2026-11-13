import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';tag='homo-luzonensis-video-85-21m22s';repo='seotro95/seotro'
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['target_seconds']==1282 and q['unique_prompts']==120 and q['prompt_txt_files']==12 and q['all_prompts_silent_suffix'] and q['minor_exclusion_in_every_prompt']
exists=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True)
assert exists.returncode!=0,'Existing episode release must be inspected before overwrite'
subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',os.environ['GITHUB_SHA'],'--title','Chủ đề 85 — Homo luzonensis — Kịch bản,120 prompt21:22','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
assets=[R/'HOMO_LUZONENSIS_85_TAI_LIEU_21m22s.zip',*[D/n for n in ['KICH_BAN_EN_21m22s.txt','en-US.srt','TIMELINE_129_CANH.csv','CAC_CANH_DUNG_LAI.txt','DOCUMENT_QA.json','NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','HUONG_DAN_SU_DUNG.txt','README.md','VOICE_PROFILES_LOCKED_BASELINE.json','5_TIEU_DE_VA_THUMBNAIL.txt']],*sorted((D/'PROMPTS').glob('*.txt'))]
manifest={'topic_id':85,'target_seconds':1282,'stage':'documents_published_before_voice_synthesis','assets':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in assets]}
p=D/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));assets.append(p)
for p in assets:subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo],check=True);print('DOCUMENT_PUBLISHED',p.name,flush=True)
print('TOPIC85_DOCUMENTS_DELIVERED',flush=True)
