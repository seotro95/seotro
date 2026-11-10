import hashlib,json,re,sys
from pathlib import Path
R=Path(__file__).parent;loc=sys.argv[1];name='hmong' if loc=='mww' else 'vietnamese';p=R/'voice/scripts'/f'{loc}.json';rows=json.loads(p.read_text());raw=(R/f'{name}_reviewed_chapters.txt').read_text()
for a,b in {'ib bộ pob txha':'ib pawg pob txha','lẫn rau hauv':'xyaw rau hauv','cao nguyên':'thaj av siab'}.items():raw=raw.replace(a,b)
parts=[' '.join(s.split()) for s in raw.split('===CHAPTER===')];assert len(parts)==12
for row,voice in zip(rows,parts):
 if loc=='mww':voice=re.sub(r'(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])',' ',voice)
 row['voice']=voice;row['editorial_review']='Rewritten by assistant for scientific meanings, dating not romance, coverage not insurance, specimen identity, inheritance, molecular evidence and appropriate local narration; independent native editorial/listening review pending.'
 assert voice.strip()
p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n');p.with_suffix('.reviewed-v3').write_text('Assistant full chapter rewrite; independent native listening/dialect review pending.\n');print(loc,'reviewed_words',sum(len(x['voice'].split()) for x in rows),'characters',sum(len(x['voice']) for x in rows))
