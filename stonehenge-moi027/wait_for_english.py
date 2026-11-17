import json,subprocess,time
run=44096963783
for attempt in range(118):
 j=json.loads(subprocess.check_output(['gh','api',f'repos/seotro95/seotro/actions/runs/{run}/jobs?filter=latest&per_page=100']))
 english=[x for x in j['jobs'] if x['name']=='english']
 if english and english[-1]['conclusion']=='success':
  print('STONEHENGE_ENGLISH_SUCCESS',run,flush=True);break
 if english and english[-1]['status']=='completed':raise RuntimeError('English failed; recover retained English checkpoints. Country outputs remain in artifacts.')
 print('WAITING_FOR_ENGLISH',attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('English not ready; country outputs remain retained')
