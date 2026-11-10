import json,shutil
from pathlib import Path
R=Path(__file__).parent;B=R/'github-build'
for name in ['input/scripts','scripts','.github/workflows']:(B/name).mkdir(parents=True,exist_ok=True)
profiles=json.load(open(R/'BASELINE_VOICE_PROFILES.json'))
for p in profiles['profiles']:
 loc=p['locale'];rows=json.load(open(R/'voice/scripts'/f'{loc}.json'));assert len(rows)==(126 if loc=='en-US' else 12)
 (B/'input/scripts'/f'{loc}.json').write_text(json.dumps([{k:x[k] for k in ['id','start','end','voice']} for x in rows],ensure_ascii=False))
 if loc!='en-US':shutil.copy(R/'voice/scripts'/f'{loc}.terminology-v2',B/'input/scripts'/f'{loc}.terminology-v2')
for name in ['render_common.py','render_online.py','prosody.py','job_init.py','publish_voices_job.py']:shutil.copy(R/name,B/'scripts'/name)
for name in ['BASELINE_VOICE_PROFILES.json','DOCUMENT_DELIVERY_STATE.json','NARRATION_STYLE_LOCKED.json','VOICE_FILE_NAMING.json']:shutil.copy(R/name,B/'input'/name)
shutil.copy('/workspace/work/malta/github-build/input/source_integrity.json',B/'input/source_integrity.json')
old=Path('/workspace/work/malta/github-build/.github/workflows/siberia-final-voices.yml').read_text()
s=old.replace('Malta episode 3','Denisova episode6').replace('ma03-','dn06-').replace('MALTA_03_','DENISOVA_06_').replace('All17','All17')
(B/'.github/workflows/siberia-final-voices.yml').write_text(s)
entries=[{'path':str(p.relative_to(B)),'mode':'100644','type':'blob','content':p.read_text()} for p in sorted(B.rglob('*')) if p.is_file()]
(R/'build-tree-entries.json').write_text(json.dumps(entries,ensure_ascii=False));print('Build files',len(entries),'characters',len((R/'build-tree-entries.json').read_text()))
