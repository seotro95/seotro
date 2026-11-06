"""Retrieve the completed text/SRT, preserve its review metadata, and rerender pacing."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
code=sys.argv[1];root=Path(__file__).resolve().parent
out=Path('translated');out.mkdir(exist_ok=True)
patterns=[code+'.srt'] if code=='en' else [code+'.srt',code+'.txt',code+'.json',code+'-text-review.json']
cmd=['gh','release','download','siberia-2536-production-v1','--repo',os.environ['GITHUB_REPOSITORY'],'--dir',str(out),'--clobber']
for p in patterns:cmd+=['--pattern',p]
subprocess.run(cmd,check=True)
if code!='en':
 meta=json.loads((out/(code+'-text-review.json')).read_text())
 assert meta['curation_sha256']==hashlib.sha256((root/'curated_cues.json').read_bytes()).hexdigest()
 assert code=='vi' or meta['translation_status'].startswith('Public web translation')
 assert hashlib.sha256((out/(code+'.srt')).read_bytes()).hexdigest()==meta['narration_srt_sha256']
shutil.copyfile(out/(code+'.srt'),root/'voices'/(code+'.srt'))
