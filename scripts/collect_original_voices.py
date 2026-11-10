import json,os,shutil,subprocess,time
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];run='42830399069';deadline=time.monotonic()+2400
while True:
 j=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/actions/runs/{run}'],text=True))
 if j['status']=='completed':break
 if time.monotonic()>deadline:raise TimeoutError('Original localized jobs not yet terminal;retain all checkpoints')
 print('Waitingfororiginallocalizedjobs',j['status'],flush=True);time.sleep(20)
subprocess.run(['gh','run','download',run,'--repo',repo,'--pattern','bs08-voice-*','--dir','artifacts/original'],check=True)
plan=json.loads(Path('input/REPAIR_PLAN.json').read_text());removed=[]
for p in list(Path('artifacts/original').rglob('render_report.json')):
 j=json.loads(p.read_text())
 if j['locale'] in plan['locales']:removed.append(j['locale']);shutil.rmtree(p.parent)
print('Originalsuccessescollected;supersededlocalesremoved',removed,flush=True)
