import hashlib,json
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts'
q=json.loads((R/'VOICE_INPUT_QA.json').read_text());assert q['status']=='passed' and q['target_seconds']==1292 and q['voices']==16
profiles=json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())['profiles']
assert len(profiles)==16 and all(p['gender']=='Male' for p in profiles)
for p in profiles:
    locale=p['locale'];path=S/f'{locale}.json';sha=hashlib.sha256(path.read_bytes()).hexdigest()
    assert q['script_sha256'][locale]==sha
    rows=json.loads(path.read_text());assert len(rows)==(130 if locale=='en-US' else 13)
    assert rows[0]['start']==0 and rows[-1]['end']==1292 and all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
    if locale!='en-US':
        marker=json.loads((S/f'{locale}.context_checked').read_text())
        assert marker['script_sha256']==sha and marker['independent_native_review'] is False
print('ROMAN_16VOICE_INPUT_GATE_PASSED')
