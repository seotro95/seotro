import json,subprocess,time
from pathlib import Path
R=Path(__file__).parent;repo='seotro95/seotro';run_id=json.loads((R/'ENGLISH_SOURCE_RUN.json').read_text())['run_id']
for attempt in range(100):
 r=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/actions/runs/{run_id}']))
 if r['conclusion']=='success':print('ENGLISH_SOURCE_VERIFIED',run_id,flush=True);break
 if r['status']=='completed':raise RuntimeError(f'English source {run_id} did not pass; retain checkpoints and repair before country generation')
 print('WAITING_FOR_ENGLISH_SOURCE',run_id,attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('English source still pending')
