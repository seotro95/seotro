import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';tag='saqqaq-hair-video-91-22m12s';repo='seotro95/seotro'
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['target_seconds']==1332 and q['unique_prompts']==120 and q['prompt_txt_files']==12 and q['all_prompts_silent_suffix'] and q['minor_exclusion_in_every_prompt']
exists=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True)
assert exists.returncode!=0,'Existing episode release must be inspected before overwrite'
subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',os.environ['GITHUB_SHA'],'--title','Chủ đề 91 — Tóc Saqqaq và ADN Bắc Cực — Kịch bản,120 prompt22:12','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
assets=[R/'SAQQAQ_HAIR_91_TAI_LIEU_22m12s.zip',*[D/n for n in ['KICH_BAN_EN_22m12s.txt','en-US.srt','TIMELINE_134_CANH.csv','CAC_CANH_DUNG_LAI.txt','DOCUMENT_QA.json','NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','HUONG_DAN_SU_DUNG.txt','README.md','VOICE_PROFILES_LOCKED_BASELINE.json','5_TIEU_DE_VA_THUMBNAIL.txt']],*sorted((D/'PROMPTS').glob('*.txt'))]
manifest={'topic_id':91,'target_seconds':1332,'stage':'documents_published_before_voice_synthesis','assets':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in assets]}
p=D/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));assets.append(p)
for p in assets:subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo],check=True);print('DOCUMENT_PUBLISHED',p.name,flush=True)
print('TOPIC91_DOCUMENTS_DELIVERED',flush=True)
