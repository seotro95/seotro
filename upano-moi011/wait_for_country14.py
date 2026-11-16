import json
import subprocess
import time

for attempt in range(110):
    jobs = json.loads(subprocess.check_output(['gh','api','repos/seotro95/seotro/actions/runs/43909217031/jobs?filter=latest&per_page=100']))['jobs']
    required = [j for j in jobs if j['name'].startswith('countries (') and j['name']!='countries (de-DE)']
    assert len(required)==14
    failed = [(j['name'],j['conclusion']) for j in required if j['status']=='completed' and j['conclusion']!='success']
    assert not failed,failed
    complete = sum(j['conclusion']=='success' for j in required)
    print('ORIGINAL_COUNTRY_VOICES_DONE',complete,'of14',flush=True)
    if complete==14:
        print('COUNTRY14_READY',flush=True)
        break
    time.sleep(20)
else:
    raise RuntimeError('Country jobs still running; successful outputs retained')
