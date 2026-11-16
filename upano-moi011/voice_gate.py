import hashlib
import json
import urllib.request
from pathlib import Path

R = Path(__file__).parent
S = R / 'voice/scripts'
BASE = 'https://github.com/seotro95/seotro/releases/download/upano-moi-011-20m22s/'
with urllib.request.urlopen(BASE + 'DOCUMENT_QA.json', timeout=40) as response:
    document = json.load(response)
assert document['status'] == 'passed' and document['target_seconds'] == 1222
assert document['unique_prompts'] == 130 and document['prompt_txt_files'] == 13
with urllib.request.urlopen(BASE + 'DOCUMENT_DELIVERY_STATE.json', timeout=40) as response:
    state = json.load(response)
assert state['documents_published'] and state['english_preview_30s_verified'] and state['namminh_preview_10s_verified']
profiles = json.loads((R / 'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())['profiles']
assert len(profiles) == 16 and all(p['gender'] == 'Male' for p in profiles)
assert next(p for p in profiles if p['locale'] == 'vi-VN')['voice_id'] == 'vi-VN-NamMinhNeural'
qa = json.loads((R / 'VOICE_INPUT_QA.json').read_text())
assert qa['status'] == 'passed' and qa['target_seconds'] == 1222 and qa['voices'] == 16
for profile in profiles:
    locale = profile['locale']
    path = S / (locale + '.json')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == qa['script_sha256'][locale]
    rows = json.loads(path.read_text())
    assert len(rows) == (123 if locale == 'en-US' else 13)
    assert rows[0]['start'] == 0 and rows[-1]['end'] == 1222
    assert all(a['end'] == b['start'] for a,b in zip(rows, rows[1:]))
    if locale != 'en-US':
        marker = json.loads((S / (locale + '.context_checked')).read_text())
        assert marker['script_sha256'] == digest and not marker['independent_native_review']
(R / 'DOCUMENT_DELIVERY_STATE.json').write_text(json.dumps(state, indent=2) + '\n')
print('UPANO16VOICE_INPUT_GATE_PASSED', flush=True)
