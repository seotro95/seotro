import concurrent.futures,hashlib,json,time
from pathlib import Path
import clarify_localizations as c
R=Path(__file__).parent;S=R/'voice/scripts'
def run(loc):
    f=S/f'{loc}.json';rows=json.loads(f.read_text());en=c.clearer(c.p.chapters[9]);assert 'tree growth layer' in en and 'tree circular' not in en
    text=c.p.adapt(c.p.translate(en,c.p.LANGS[loc]),loc)
    rows[9].update(voice=text,source_en=en,editorial_status='Tree-growth dating context explicitly repaired;assistant terminology review;independent native review pending')
    f.write_text(json.dumps(rows,ensure_ascii=False,indent=2));f.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));f.with_suffix('.translated19-v2').write_text(hashlib.sha256(f.read_bytes()).hexdigest());print('TREE_CONTEXT_REPAIRED',loc,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,[l for l in c.p.LANGS if l!='vi-VN']))
