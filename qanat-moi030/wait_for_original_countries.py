import json,subprocess,time
REPO='seotro95/seotro';RUN=44159606094
for attempt in range(100):
 r=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/actions/runs/{RUN}']))
 if r['status']=='completed':
  jobs=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/actions/runs/{RUN}/jobs?per_page=100']))['jobs']
  failures={j['name'].removeprefix('countries (').removesuffix(')') for j in jobs if j['name'].startswith('countries (') and j['conclusion']!='success'}
  assert failures=={'it-IT','ja-JP','ko-KR'},failures
  print('Original twelve countries complete; three revised locales supplied by recovery run',flush=True);break
 print('WAITING_ORIGINAL_COUNTRIES',attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('Original countries not ready')
