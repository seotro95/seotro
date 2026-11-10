import hashlib,json,re
from pathlib import Path
R=Path(__file__).parent;p=R/'hmong_reviewed.tsv';t=p.read_text().replace('ib bộ khaub ncaws','ib pawg khaub ncaws').replace('hlwb txha','hlwb pob txha');p.write_text(t)
rows=json.loads((R/'voice/scripts/mww.json').read_text());texts=dict((int(a),b) for a,b in (l.split('\t',1) for l in t.splitlines()));assert len(texts)==12
for row in rows:
 row['machine_translation_before_review']=row['voice'];row['voice']=texts[row['id']];row['editorial_status']='Rewritten by assistant for scientific meaning,white-Hmong RPA phrasing and technical explanations;independent native dialect/editorial/listening review pending'
 assert not re.search('[àáảãạăâêôơưđộế]',row['voice'],re.I)
p=R/'voice/scripts/mww.json';p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));p.with_suffix('.terminology-v2').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n')
print('Hmong chapters/words',len(rows),[len(x['voice'].split()) for x in rows])
