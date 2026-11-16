import json
import subprocess
import time

for attempt in range(50):
    run = json.loads(subprocess.check_output(['gh','api','repos/seotro95/seotro/actions/runs/43909217031']))
    print('ORIGINAL_VOICE_RUN',run['status'],run.get('conclusion'),flush=True)
    if run['status'] == 'completed':
        jobs = json.loads(subprocess.check_output(['gh','api','repos/seotro95/seotro/actions/runs/43909217031/jobs']))['jobs']
        required = [j for j in jobs if j['name']=='english' or (j['name'].startswith('countries (') and j['name']!='countries (de-DE)')]
        assert len(required)==15
        failed = [(j['name'],j['conclusion']) for j in required if j['conclusion']!='success']
        assert not failed,failed
        print('ALL_OTHER15_ORIGINAL_VOICES_VERIFIED_SUCCESS',flush=True)
        break
    time.sleep(20)
else:
    raise RuntimeError('Original voice run still active; successful outputs retained')
