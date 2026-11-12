import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).parent;D=R/'documents';tag='bone-traces-video-58-22m42s';repo='seotro95/seotro'
subprocess.run([sys.executable,str(R/'build_documents.py')],check=True)
q=json.loads((D/'DOCUMENT_QA.json').read_text());assert q['status']=='passed' and q['target_seconds']==1362 and q['unique_prompts']==130 and q['prompt_txt_files']==13 and q['all_prompts_silent_suffix'] and q['minor_exclusion_in_every_prompt']
exists=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True)
assert exists.returncode!=0,'Existing episode release must be inspected before overwrite'
subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',os.environ['GITHUB_SHA'],'--title','Chủ đề 58 — Móng, răng và xương — Kịch bản và 130 prompt 22:42','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
assets=[R/'BONE_TRACES_58_TAI_LIEU_22m42s.zip',*[D/n for n in ['KICH_BAN_EN_22m42s.txt','en-US.srt','TIMELINE_137_CANH.csv','CAC_CANH_DUNG_LAI.txt','DOCUMENT_QA.json','NGUON_KIEM_CHUNG.md','PHAN_TICH_VIDEO_NGUON.md','HUONG_DAN_SU_DUNG.txt','README.md','VOICE_PROFILES_LOCKED_BASELINE.json','ADAM_VOICE_LOCK.json','5_TIEU_DE_VA_THUMBNAIL.txt']],*sorted((D/'PROMPTS').glob('*.txt'))]
manifest={'topic_id':58,'target_seconds':1362,'stage':'documents_published_before_voice_synthesis','assets':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in assets]}
p=D/'DOCUMENT_ASSET_MANIFEST.json';p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));assets.append(p)
for p in assets:subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo],check=True);print('DOCUMENT_PUBLISHED',p.name,flush=True)
print('TOPIC58_DOCUMENTS_DELIVERED',flush=True)
