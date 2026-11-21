import json,subprocess,time
from pathlib import Path
R=Path(__file__).parent;REPO='seotro95/seotro';SOURCES=json.loads((R/'SOURCE_RUNS.json').read_text());RUNS=[SOURCES['documents_and_english'],SOURCES['country_voice_generation']]
for attempt in range(110):
 pending=[]
 for run_id in RUNS:
  r=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/actions/runs/{run_id}']))
  if r['conclusion']=='success':continue
  if r['status']=='completed':raise RuntimeError(f'Voice source {run_id} did not pass. Retain checkpoints and repair failed parts before publication.')
  pending.append(run_id)
 if not pending:print('BOTH_VOICE_SOURCES_READY',RUNS,flush=True);break
 print('WAITING_VOICE_SOURCES',pending,attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('Voice sources still pending')
