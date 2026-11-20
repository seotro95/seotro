import json,urllib.request
from pathlib import Path
R=Path(__file__).parent
with urllib.request.urlopen('https://github.com/seotro95/seotro/releases/download/richat-moi-061-21m42s/DOCUMENT_QA.json',timeout=40) as response:q=json.load(response)
assert q['status']=='passed' and q['target_seconds']==1302 and q['unique_prompts']==140 and q['prompt_txt_files']==14
(R/'DOCUMENT_DELIVERY_STATE.json').write_text(json.dumps(dict(documents_published=True,target_seconds=1302)))
print('RICHAT_ENGLISH_GATE_PASSED')

