import glob,json,re,subprocess,sys,wave
from pathlib import Path
locale=sys.argv[1];plan=json.loads(Path('input/REPAIR_PLAN.json').read_text());folder=Path('build/voice/audio')/locale;folder.mkdir(parents=True,exist_ok=True)
changed=plan['changed_chapters'].get(locale,[]);runtime={}
if locale=='en-US':
 rows=json.loads(Path('input/scripts/en-US.json').read_text());complete=[];incomplete=[]
 for row in rows:
  pieces=re.split(r'(?<=[.!?])\s+',row['voice'].strip());ok=True
  for i,text in enumerate(pieces,1):
   p=folder/f'raw-{row["id"]:03d}-{i:02d}.wav'
   try:
    with wave.open(str(p),'rb') as f:assert f.getnframes()>0
   except Exception:ok=False;break
  (complete if ok else incomplete).append(row['id'])
 for cue in incomplete:
  for p in folder.glob(f'raw-{cue:03d}-*'):
   if p.is_file():p.unlink()
 pro=Path('scripts/prosody.py');s=pro.read_text();s=re.sub(r'EN_PACING_REPAIRS=.*','EN_PACING_REPAIRS='+repr(set(incomplete)),s,count=1);pro.write_text(s)
 runtime=dict(locale=locale,original_run=plan['source_runs'][locale],complete_cached_cues=complete,incomplete_whole_cue_requests=incomplete,english_wording_unchanged=True,method='Keep complete sentence pieces;single full-cue requests only for missing/incomplete cues;samevoice;bounded+3percentexistingstylerange;digitalzeroedgetrimwith30msguard')
 print('EN_CHECKPOINT_RECOVERY',json.dumps(runtime),flush=True)
else:
 for cue in changed:
  for p in folder.glob(f'raw-{cue:03d}-*'):
   if p.is_file():p.unlink()
 runtime=dict(locale=locale,invalidated_chapters=changed,reason=plan['reasons'].get(locale,'Measured timing or scientific localization repair'))
# Successful old jobs may retain style metadata without WAVs. Never reuse an
# orphan style receipt for newly generated audio.
for p in folder.glob('raw-*.style.json'):
 if not p.with_name(p.name.replace('.style.json','.wav')).exists():
  p.unlink();p.with_name(p.name.replace('.style.json','.words.jsonl')).unlink(missing_ok=True)
(folder/'REPAIR_RUNTIME_PLAN.json').write_text(json.dumps(runtime,ensure_ascii=False,indent=2))
subprocess.run([sys.executable,'-u','scripts/job_init.py',locale,'full'],check=True)
