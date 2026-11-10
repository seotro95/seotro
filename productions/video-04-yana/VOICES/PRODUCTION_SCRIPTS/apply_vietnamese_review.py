import hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';p=S/'vi-VN.json';rows=json.loads(p.read_text());parts=[x.strip() for x in (R/'vietnamese_reviewed_chapters.txt').read_text().split('===CHAPTER===')];assert len(parts)==12
for row,v in zip(rows,parts):
 row['voice']=' '.join(re.sub(r'(?<=[A-Za-zÀ-ỹ])(?=\d)|(?<=\d)(?=[A-Za-zÀ-ỹ])',' ',v).split());row['editorial_review']='Assistant rewrote all12 chapters for Vietnamese documentary narration and corrected scientific/lexical errors; independent native listening review pending'
p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');p.with_suffix('.reviewed-v3').write_text('Assistant scientific/localisation rewrite; independent native listening review pending.\n');print('Vietnamese reviewed:',sum(len(x['voice'].split()) for x in rows),'syllable-like words')
