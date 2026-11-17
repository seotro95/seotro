from pathlib import Path
import json,hashlib,os,subprocess,zipfile
P=Path(__file__).resolve().parent;D=P/'documents';ready=json.loads((P/'READY.json').read_text());assert ready['topic']=='020-Hattusa' and ready['target_seconds']==1362
repo=os.environ['GITHUB_REPOSITORY'];tag=ready['release_tag'];files=[]
for item in ready['documents_inventory']:
 p=P/item['path'];assert p.is_relative_to(D) and p.suffix in {'.txt','.md','.csv','.srt','.json'}
 data=p.read_bytes();assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],item['path'];data.decode('utf-8');files.append(p)
zpath=P/'HATTUSA_020_TAI_LIEU_22m42s.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,str(p.relative_to(D)))
with zipfile.ZipFile(zpath) as z:assert len(z.namelist())==len(files) and z.testzip() is None
assets=[zpath,D/'KICH_BAN_EN_22m42s.txt',D/'KICH_BAN_EN_CO_MOC.txt',D/'TIMELINE_137_CANH.csv',D/'5_TIEU_DE_5_PROMPT_THUMBNAIL.txt',D/'VOICE_PROFILES_LOCKED.json',D/'NARRATION_STYLE_LOCKED.json',D/'VOICE_FILE_NAMING.json',D/'GIONG_DA_LUU.md',D/'PHAN_TICH_VIDEO_NGUON.md',D/'NGUON_KIEM_CHUNG.md',D/'VISUAL_STYLE_LOCKED.json']+sorted((D/'PROMPTS').glob('*.txt'))
qa={'topic':'020-Hattusa','duration_seconds':1362,'unique_prompts':140,'prompt_txt_count':14,'narration_text_languages':16,'document_file_count':len(files),'document_zip_sha256':hashlib.sha256(zpath.read_bytes()).hexdigest(),'document_zip_bytes':zpath.stat().st_size,'tts_generation_executed_in_export':False,'contains_source_media_models_credentials':False,'export_commit':os.environ['GITHUB_SHA'],'independent_native_listening_review':False}
(P/'DOCUMENT_PUBLICATION_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));assets.append(P/'DOCUMENT_PUBLICATION_QA.json')
(P/'DOCUMENT_SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in assets));assets.append(P/'DOCUMENT_SHA256SUMS.txt')
exists=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True)
if exists.returncode:subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',os.environ['GITHUB_SHA'],'--title','Hattusa — cổng đá và kho văn bản của một đế chế —22:42','--notes-file',str(D/'README.md'),'--latest=false'],check=True)
for p in assets:subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True);print('Uploaded',p.name,flush=True)
print('Published requested hattusa020 documents only; no synthesis in export',flush=True)
