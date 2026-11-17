import json,subprocess,time
RUN=44116339197
for attempt in range(118):
 j=json.loads(subprocess.check_output(['gh','api',f'repos/seotro95/seotro/actions/runs/{RUN}/jobs?filter=latest&per_page=100']))
 english=[x for x in j['jobs'] if x['name']=='english']
 if english and english[-1]['conclusion']=='success':print('QANAT_ENGLISH_READY',RUN,flush=True);break
 if english and english[-1]['status']=='completed':raise RuntimeError('English needs recovery from retained checkpoints before final publication')
 print('WAITING_FOR_ENGLISH',attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('English not ready; country artifacts remain retained')
