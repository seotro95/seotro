import json,urllib.request
from pathlib import Path
R=Path(__file__).parent
with urllib.request.urlopen('https://github.com/seotro95/seotro/releases/download/sky536-moi-053-22m12s/DOCUMENT_QA.json',timeout=40) as response:q=json.load(response)
assert q['status']=='passed' and q['target_seconds']==1332 and q['unique_prompts']==150 and q['prompt_txt_files']==15
(R/'DOCUMENT_DELIVERY_STATE.json').write_text(json.dumps(dict(documents_published=True,target_seconds=1332)))
print('SKY536_ENGLISH_GATE_PASSED')

