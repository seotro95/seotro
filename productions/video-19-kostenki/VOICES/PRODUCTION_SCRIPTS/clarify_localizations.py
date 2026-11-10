"""Resolve polysemous archaeology terms before localising the full chapter."""
import concurrent.futures,hashlib,json,re,time
from pathlib import Path
import prepare_scripts as p
R=Path(__file__).parent;S=R/'voice/scripts';backup=R/'voice/machine-first';backup.mkdir(exist_ok=True)
def clearer(ch):
    t=p.chapter_source(ch)
    changes={
      'ordinary daily life in a dwelling':'the normal everyday activities of people living in a dwelling',
      'animals that did not all die together':'mammoths whose deaths occurred at different times',
      'a single dramatic killing event':'one event in which many mammoths were killed',
      'the resulting deposits':'the resulting layers of soil and debris',
      'incomplete deposits':'incomplete layers of soil and archaeological material',
      'associated deposits':'associated layers of soil and archaeological material',
      'a deposit that preserves them together':'one layer of soil that preserves traces from different visits together',
      'human use':'human activity',
      'occupation duration':'duration of human use of a site',
      'about occupation':'about people using a place',
      'supporting members':'supporting beams',
      'while a measurement on wood can concern growth long before burning':'while dating wood can measure the time a tree ring grew, long before the wood was burned',
      'with uncertainty still attached':'and these estimates still have uncertainty',
      'a dated sample':'a sample whose age has been scientifically measured',
      'long term residential base':'base camp where people lived for a long time',
      'a complete recipe, a harvested crop, or a daily menu':'a complete recipe or evidence of cultivated crops or a complete daily diet',
      'the number of fragments and the minimum number of individuals':'the number of bone fragments and the minimum number of separate animals',
      'the record of ordinary life':'physical evidence of everyday human activities',
      'a narrow estimated interval':'a narrow estimated date range',
      'the builders\' personal lives':'the personal lives of the people who built the structure',
      'a heavily loaded support':'a support bearing a heavy load',
      'a ring of bones':'a circular arrangement of bones',
      'the ring':'the circular arrangement of bones',
      'the roof':'the proposed roof',
      'a footprint':'a physical trace',
      'a particular hunting party':'a particular group of hunters',
      'which event have we actually dated':'which event has the age measurement actually dated',
      'a sheltered hollow':'a hollow protected from wind',
      'a dark speck will reveal fire':'a tiny dark fragment will provide evidence of fire',
      'a space where our imagined house ought to stand':'the empty space where we imagine an ancient house',
      'supports its details':'provides evidence for its details',
      'add supporting members':'add supporting beams',
      'complete the ring':'complete the circular bone arrangement',
      'charred biological remains':'charred remains of plants and other organic material',
    }
    for a,b in changes.items():t=t.replace(a,b)
    t=t.replace('tree ring','tree growth layer')
    t=re.sub(r'\boccupation\b','human use of the site',t)
    t=re.sub(r'\bdeposits\b','layers of soil and archaeological material',t)
    t=re.sub(r'\bring\b','circular bone arrangement',t)
    return t
def run(loc):
    file=S/f'{loc}.json';mark=file.with_suffix('.translated19-v2')
    if mark.exists():return loc
    if not (backup/file.name).exists():(backup/file.name).write_bytes(file.read_bytes())
    old=json.loads(file.read_text());partial=file.with_suffix('.v2partial.json');rows=json.loads(partial.read_text()) if partial.exists() else []
    for i in range(len(rows),12):
        ch=p.chapters[i];en=clearer(ch);out=p.adapt(p.translate(en,p.LANGS[loc]),loc)
        for sentence in [x.strip() for x in re.split(r'(?<=[.!?])\s+',en) if len(x.strip())>=25]:
            if sentence in out:raise ValueError('Untranslated sentence '+loc+':'+str(i+1))
        rows.append(dict(id=i+1,start=int(ch['start_seconds']),end=int(ch['end_seconds']),voice=out,source_en=en,editorial_status='Chapter-context translation with disambiguated archaeological terms;assistant terminology review pending;independent native review pending'))
        partial.write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps({'clarified':loc,'chapter':i+1}),flush=True);time.sleep(2)
    file.write_text(json.dumps(rows,ensure_ascii=False,indent=2));file.with_suffix('.txt').write_text('\n\n'.join(x['voice'] for x in rows));mark.write_text(hashlib.sha256(file.read_bytes()).hexdigest());partial.unlink(missing_ok=True);return loc
if __name__=='__main__':
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(run,l):l for l in p.LANGS if l!='vi-VN'}
        for f in concurrent.futures.as_completed(jobs):
            try:print('CLARIFIED',f.result(),flush=True)
            except Exception as e:errors.append(jobs[f]);print('CLARIFY_ERROR',jobs[f],str(e),flush=True)
    if errors:raise SystemExit('Incomplete:'+','.join(errors))
