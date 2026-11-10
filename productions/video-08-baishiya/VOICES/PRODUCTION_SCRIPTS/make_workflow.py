import hashlib,json,shutil,subprocess
from pathlib import Path
R=Path(__file__).parent;B=R/'github-build';subprocess.run(['python',str(R/'validate_voice_inputs.py')],check=True)
profiles=json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text())
for p in profiles['profiles']:
 loc=p['locale'];rows=json.loads((R/'voice/scripts'/f'{loc}.json').read_text());dest=B/'input/scripts'/f'{loc}.json';dest.write_text(json.dumps([{k:x[k] for k in ['id','start','end','voice']} for x in rows],ensure_ascii=False))
 if loc!='en-US':shutil.copy(R/'voice/scripts'/f'{loc}.terminology-v2',dest.with_suffix('.terminology-v2'))
for n in ['render_common.py','render_online.py','prosody.py','job_init.py','publish_voices_job.py']:shutil.copy(R/n,B/'scripts'/n)
for n in ['BASELINE_VOICE_PROFILES.json','DOCUMENT_DELIVERY_STATE.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json','source_integrity.json','VOICE_INPUT_QA.json']:shutil.copy(R/n,B/'input'/n)
shutil.copy(R/'locales-workflow.yml',B/'.github/workflows/baishiya-locales08.yml')
# Do not alter the existing voice workflow or rerun our already-started English workflow.
entries=[dict(path=str(p.relative_to(B)),mode='100644',type='blob',content=p.read_text()) for p in sorted(B.rglob('*')) if p.is_file() and p.name!='baishiya-english08.yml']
groups=[];group=[];size=0
for e in entries:
 n=len(json.dumps(e,ensure_ascii=False).encode())
 if group and size+n>300000:groups.append(group);group=[];size=0
 group.append(e);size+=n
if group:groups.append(group)
for i,g in enumerate(groups):(R/f'voice_tree_group_{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'VOICE_BUILD_STAGING.json').write_text(json.dumps(dict(groups=len(groups),entries=len(entries),locales=17,english_run_reused=42826768097,workflow_file='baishiya-locales08.yml'),indent=2));print('Full build groups',len(groups),'files',len(entries))
