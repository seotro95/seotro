import json,re,shutil,subprocess
from pathlib import Path
R=Path(__file__).parent;B=R/'github-build';subprocess.run(['python',str(R/'validate_voice_inputs.py')],check=True)
profiles=json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text())
for p in profiles['profiles']:
    loc=p['locale'];source=R/'voice/scripts'/f'{loc}.json';a=json.loads(source.read_text());dst=B/'input/scripts'/source.name;dst.write_text(json.dumps([{k:x[k] for k in ['id','start','end','voice']} for x in a],ensure_ascii=False))
    if loc!='en-US':shutil.copyfile(source.with_suffix('.terminology-v2'),dst.with_suffix('.terminology-v2'))
for name in ['render_common.py','render_online.py','prosody.py','job_init.py','publish_voices_job.py']:shutil.copyfile(R/name,B/'scripts'/name)
for name in ['BASELINE_VOICE_PROFILES.json','DOCUMENT_DELIVERY_STATE.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json','source_integrity.json','VOICE_INPUT_QA.json','TRANSLATION_REVIEW.json','TASK_SCOPE_AUTHORIZATION19.json']:shutil.copyfile(R/name,B/'input'/name)
entries=[dict(path=str(p.relative_to(B)),mode='100644',type='blob',content=p.read_text()) for p in sorted(B.rglob('*')) if p.is_file()]
entries.append(dict(path='.github/workflows/kostenki-locales19.yml',mode='100644',type='blob',content=(R/'locales-workflow.yml').read_text()))
for e in entries:assert not re.search(r'file_[0-9a-f]{32}|/workspace/attachments/[0-9a-f]{8}-',e['content']),e['path']
groups=[];g=[];count=0
for e in entries:
    n=len(json.dumps(e,ensure_ascii=False).encode())
    if g and count+n>270000:groups.append(g);g=[];count=0
    g.append(e);count+=n
if g:groups.append(g)
for i,g in enumerate(groups):(R/f'voice_tree_group_{i}.json').write_text(json.dumps(g,ensure_ascii=False))
(R/'VOICE_BUILD_STAGING.json').write_text(json.dumps(dict(groups=len(groups),files=len(entries),characters=[len(json.dumps(g,ensure_ascii=False)) for g in groups]),indent=2));print((R/'VOICE_BUILD_STAGING.json').read_text())
