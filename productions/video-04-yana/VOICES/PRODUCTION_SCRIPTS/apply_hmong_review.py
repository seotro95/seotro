import hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';p=S/'mww.json';rows=json.loads(p.read_text());text=(R/'hmong_reviewed_chapters.txt').read_text().replace('niên sijhawm','hnub nyoog thiab sijhawm')
parts=[x.strip() for x in text.split('===CHAPTER===')];assert len(parts)==12
for row,voice in zip(rows,parts):
 voice=re.sub(r'(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])',' ',voice)
 row['voice']=' '.join(voice.split());row['editorial_review']='Rewritten by assistant for scientific meanings, neutral population language, animal-skin sense and Americas versus USA; independent native/White Hmong listening review pending'
 assert not any(x in row['voice'] for x in ['hom kab mob caj ces','directs','belongs','Asmeskas'])
p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');p.with_suffix('.reviewed-v3').write_text('Assistant scientific/localisation rewrite; independent native listening/dialect review pending.\n')
print('Reviewed Hmong',sum(len(x['voice'].split()) for x in rows),'words;',sum(len(x['voice']) for x in rows),'characters')
