"""Render one aligned track using the owner's pinned Melo 1.3.1 source."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,wave,hashlib

p=argparse.ArgumentParser();p.add_argument('language');args=p.parse_args()
codes={'en':'EN','vi':'VI','es':'ES','fr':'FR','ja':'JP','ko':'KR','de':'DE','it':'IT','pt':'PT','nl':'NL','pl':'PL','sv':'SV','da':'DA','fi':'FI','no':'NO','cs':'CS','hi':'HI'}
if args.language not in codes:raise SystemExit('Unsupported language')
lang=codes[args.language];base=Path(__file__).resolve().parent
source=Path('melo-source/melo-viet-local').resolve();sys.path.insert(0,str(source))
root=Path(os.environ.get('RUNNER_TEMP',str(base)))/('melo-'+args.language)
root.mkdir(parents=True,exist_ok=True);os.environ['MELO_VIET_ROOT']=str(root)
os.environ['HF_HOME']=str(root/'models/huggingface')
from app import Studio,VERSION
from multilingual_backend import voices_for as multi_voices
from fast_backend import voices_for as fast_voices,catalog,ensure_model
from local_models import ensure
assert VERSION=='1.3.1'
provider='multi' if args.language in {'en','ja','ko'} else 'fast'
if provider=='multi':
 voice=next(v for v in multi_voices(lang) if v['name']=='Supertonic 3 · M3')
 ensure('supertonic3',False);engine='multi'
else:
 candidates=fast_voices(lang)
 locales={'es':'es-ES','fr':'fr-FR','de':'de-DE','pt':'pt-PT','it':'it-IT','nl':'nl-NL','pl':'pl-PL','sv':'sv-SE','da':'da-DK','fi':'fi-FI','no':'no-NO','cs':'cs-CZ','hi':'hi-IN','vi':'vi-VN'}
 candidates=[v for v in candidates if v['locale']==locales[args.language]]
 if not candidates:raise RuntimeError('No regional voice found')
 candidates.sort(key=lambda v:({'Male':0,'Female':1,'Unknown':2}.get(v['gender'],3),0 if v['quality'] in {'medium','high'} else 1))
 voice=candidates[0];record=next(m for m in catalog() if m['id']==voice['id'].split(':')[1])
 ensure_model(record,False);engine='piper'
for runtime_engine in {'piper','multi'}:
 envbin=root/'envs'/runtime_engine/'bin';envbin.mkdir(parents=True,exist_ok=True)
 if not (envbin/'python').exists():(envbin/'python').symlink_to(sys.executable)
out=Path('rendered')/args.language;out.mkdir(parents=True,exist_ok=True)
studio=Studio(root,True)
try:
 studio.settings(1)
 job=studio.start({'op':'render','engine':'local','language':lang,'local_provider':provider,'voice':voice['id'],
  'threads':2 if engine=='piper' else 3,'chunk_workers':2 if engine=='piper' else 1,
  'name':args.language+'_25m36.srt','text':(base/'voices'/(args.language+'.srt')).read_text(encoding='utf-8'),
  'format':'srt','speed':1.0 if args.language=='en' else .95,'style':'narration','expressive':False,'emphasis':False,
  'chunk_size':240,'use_cache':False,'timing_mode':'exact'})
 ident=job['id'];last=-1
 while True:
  item=studio.jobs[ident];pct=int(item.get('progress',0)*100)
  if pct//10!=last//10:print(args.language,item['status'],item.get('stage'),pct,'%',flush=True);last=pct
  if item['status'] in {'done','error','cancelled','interrupted'}:break
  time.sleep(1)
 if item['status']!='done':raise RuntimeError(item.get('error'))
 folder=root/'outputs'/ident
 with wave.open(str(folder/'part-0001.wav')) as wav:
  assert wav.getnchannels()==1 and wav.getsampwidth()==2
  assert wav.getframerate()==48000 and wav.getnframes()==73728000
 report=json.loads((folder/'report.json').read_text());assert report['duration_verified'] and report['sync_ok']
 assert report['sync_report']['error_frames']==0 and len(report['sync_report']['cues'])==59
 studio.exports.start(ident)
 while studio.jobs[ident].get('mp3_status') not in {'done','error','cancelled','interrupted'}:time.sleep(1)
 if studio.jobs[ident].get('mp3_status')!='done':raise RuntimeError(studio.jobs[ident].get('mp3_error'))
 import shutil
 for src,dst in [('part-0001.wav',args.language+'.wav'),('voice.mp3',args.language+'.mp3'),('subtitles.srt',args.language+'.srt')]:shutil.copyfile(folder/src,out/dst)
 report['selected_voice_metadata']=voice;report['source_commit']='4f4fa1d72d976d6e2b9c94f906b0e12c6a2cf043'
 report['script_status']='Original English narration / localized translation; not a source-video transcription'
 report['audio_sha256']=hashlib.sha256((out/(args.language+'.wav')).read_bytes()).hexdigest()
 (out/(args.language+'-report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
finally:studio.close()
subprocess.run(['gh','release','upload','siberia-2536-production-v1',*[str(f) for f in out.iterdir()],
 '--repo',os.environ['GITHUB_REPOSITORY'],'--clobber'],check=True)
print('UPLOADED',args.language,'1536 seconds, 73728000 samples, zero frame error',flush=True)
