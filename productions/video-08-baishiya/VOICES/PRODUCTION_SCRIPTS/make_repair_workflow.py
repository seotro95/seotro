import json,shutil,subprocess
from pathlib import Path
R=Path(__file__).parent;B=R/'github-build';subprocess.run(['python',str(R/'validate_voice_inputs.py')],check=True)
entries=[]
for name in ['render_online.py','prosody.py','job_init_repair.py','publish_voices_job.py','collect_original_voices.py']:
 shutil.copy(R/name,B/'scripts'/name);entries.append(dict(path='scripts/'+name,mode='100644',type='blob',content=(R/name).read_text()))
for loc in ['ja-JP','ko-KR']:
 p=R/'voice/scripts'/f'{loc}.json';rows=json.loads(p.read_text());dest=B/'input/scripts'/p.name;dest.write_text(json.dumps([{k:x[k] for k in ['id','start','end','voice']} for x in rows],ensure_ascii=False));entries.append(dict(path='input/scripts/'+p.name,mode='100644',type='blob',content=dest.read_text()));entries.append(dict(path='input/scripts/'+loc+'.terminology-v2',mode='100644',type='blob',content=p.with_suffix('.terminology-v2').read_text()))
for name in ['REPAIR_PLAN.json','VOICE_INPUT_QA.json','LOCALIZATION_REPAIRS.json']:entries.append(dict(path='input/'+name,mode='100644',type='blob',content=(R/name).read_text()))
entries.append(dict(path='.github/workflows/baishiya-repair08.yml',mode='100644',type='blob',content=(R/'repair-workflow.yml').read_text()))
(R/'repair-tree-entries.json').write_text(json.dumps(entries,ensure_ascii=False));print('Repairfiles',len(entries),'characters',len((R/'repair-tree-entries.json').read_text()))
