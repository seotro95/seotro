import json,subprocess,time
from pathlib import Path
R=Path(__file__).parent;run=44033941869
for attempt in range(118):
    j=json.loads(subprocess.check_output(['gh','api',f'repos/seotro95/seotro/actions/runs/{run}/jobs?filter=latest&per_page=100']))
    english=[x for x in j['jobs'] if x['name']=='english']
    if english and english[-1]['conclusion']=='success':
        print('ROMAN_ENGLISH_SUCCESS',run,flush=True);break
    if english and english[-1]['status']=='completed':raise RuntimeError('English failed; preserve completed country artifacts and recover its retained checkpoints before final publication')
    print('WAITING_FOR_ENGLISH',attempt+1,flush=True);time.sleep(30)
else:raise TimeoutError('English not ready; successful country speech remains in artifacts')
