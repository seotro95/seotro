import json,subprocess,time
REPO='seotro95/seotro';RUNS=[44703983383,44704980586]
for attempt in range(110):
 pending=[]
 for run_id in RUNS:
  run=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/actions/runs/{run_id}']))
  if run['conclusion']=='success':continue
  if run['status']=='completed':raise RuntimeError(f'Voice source {run_id} is incomplete; keep checkpoints and recover failed jobs before publication')
  pending.append(run_id)
 if not pending:print('BOTH_VOICE_SOURCES_READY',flush=True);break
 print('WAITING_VOICE_SOURCES',pending,attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('Sources not ready')
