import json,subprocess,time
from pathlib import Path
R=Path(__file__).parent;deadline=time.monotonic()+1800
while True:
 log=(R/'render_all.log').read_text() if (R/'render_all.log').exists() else ''
 if 'Render stage complete' in log:break
 if 'Traceback' in log:raise RuntimeError('Render failed; preserve sources and completed intermediates.')
 if time.monotonic()>deadline:raise TimeoutError('Rendering has not completed.')
 time.sleep(2)
for name in ['assemble_final.py','qa_final.py','review_final.py','package_delivery.py']:
 p=R/'EDIT_WORKFLOW_STATE.json';s=json.load(open(p));s['phase']='local_'+name[:-3];p.write_text(json.dumps(s,indent=2));print('START',name,flush=True)
 with (R/(name[:-3]+'.log')).open('w') as f:subprocess.run(['python','-u',str(R/name)],stdout=f,stderr=subprocess.STDOUT,check=True)
 print('DONE',name,flush=True)
s=json.load(open(p));s['phase']='local_master_technical_qa_passed_pending_visual_review';p.write_text(json.dumps(s,indent=2));print('LOCAL_MASTER_AND_DELIVERY_READY',flush=True)
