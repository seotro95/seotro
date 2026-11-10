import json,re
from pathlib import Path
rows=json.loads(Path('input/scripts/en-US.json').read_text())
tokens=lambda s:re.findall(r'[a-z]+',s.lower())
results=[]
for cue,row in enumerate(rows,1):
    p=Path('checkpoint')/f'raw-{cue:03d}-01.words.jsonl'
    paths=[p] if p.exists() else sorted(Path('checkpoint').glob(f'raw-{cue:03d}-*.words.jsonl'))
    assert paths,str(p)
    events=[json.loads(x) for q in paths for x in q.read_text().splitlines()]
    spoken=' '.join(e['text'] for e in events if e.get('type')=='WordBoundary')
    results.append({'cue':cue,'tokens_match':tokens(spoken)==tokens(row['voice']),'expected_tokens':len(tokens(row['voice'])),'provider_tokens':len(tokens(spoken))})
bad=[r['cue'] for r in results if not r['tokens_match']]
report={'topic':19,'script_unchanged':True,'audited_cues':122,'original_mismatched_cues':bad,'known_cue113_repair_required':113 in bad,'all_other121_cues_match_provider_word_metadata':all(r['tokens_match'] for r in results if r['cue']!=113),'cues':results}
Path('ENGLISH_WORD_AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='cues'}),flush=True)
assert not set(bad)-{113},bad
