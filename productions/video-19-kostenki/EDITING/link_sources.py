import argparse,hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).parent;p=argparse.ArgumentParser();p.add_argument('source_folder',type=Path);a=p.parse_args()
manifest=json.loads((R/'SOURCE_MANIFEST.json').read_text());files={}
for f in a.source_folder.rglob('*.mp4'):files.setdefault(f.name,[]).append(f)
(R/'sources').mkdir(exist_ok=True)
for rec in manifest['clips']:
 if not rec['used_in_final']:continue
 candidates=files.get(rec['source_name'],[]);src=next((f for f in candidates if hashlib.file_digest(f.open('rb'),'sha256').hexdigest()==rec['source_sha256']),None)
 assert src is not None,rec['source_name']
 out=R/'sources'/f"{rec['label']}.mp4"
 subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(src),'-map','0:v:0','-an','-vf','scale=1280:720:flags=lanczos,setsar=1,fps=24','-t','10','-frames:v','240','-c:v','libx264','-preset','fast','-crf','20','-maxrate','2200k','-bufsize','4400k','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(out)],check=True)
 print(rec['label'],flush=True)
