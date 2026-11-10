import json,shutil
from pathlib import Path
R=Path(__file__).parent;B=R/'github-build';(B/'input/scripts').mkdir(parents=True,exist_ok=True);(B/'scripts').mkdir(exist_ok=True)
assert json.loads((R/'DOCUMENT_DELIVERY_STATE.json').read_text())['target_seconds']==1215
rows=json.loads((R/'voice/scripts/en-US.json').read_text());assert len(rows)==122 and rows[-1]['end']==1215
(B/'input/scripts/en-US.json').write_text(json.dumps(rows,ensure_ascii=False))
for name in ['BASELINE_VOICE_PROFILES.json','DOCUMENT_DELIVERY_STATE.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json','source_integrity.json']:shutil.copyfile(R/name,B/'input'/name)
for name in ['render_common.py','render_online.py','prosody.py','job_init.py']:shutil.copyfile(R/name,B/'scripts'/name)
entries=[dict(path=str(p.relative_to(B)),mode='100644',type='blob',content=p.read_text()) for p in sorted(B.rglob('*')) if p.is_file()]
entries.append(dict(path='.github/workflows/kostenki-english19.yml',mode='100644',type='blob',content=(R/'english-workflow.yml').read_text()))
(R/'english-build-entries.json').write_text(json.dumps(entries,ensure_ascii=False));print('English staged:',len(entries),'files')
