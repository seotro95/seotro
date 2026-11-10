import concurrent.futures,csv,hashlib,json,re,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
R=Path(__file__).parent;S=R/'voice/scripts';S.mkdir(parents=True,exist_ok=True)
source=[dict(id=int(a),start=(int(a)-1)*10,end=min(int(a)*10,1215),voice=b) for a,b in (l.split('\t',1) for l in (R/'script_en.tsv').read_text().splitlines())]
(S/'en-US.json').write_text(json.dumps(source,ensure_ascii=False,indent=2));(S/'en-US.txt').write_text('\n\n'.join(x['voice'] for x in source))
chapters=list(csv.DictReader(open(R/'package/CHAPTERS_12.csv',encoding='utf-8-sig')))
LANGS={'vi-VN':'vi','es-ES':'es','fr-FR':'fr','ja-JP':'ja','ko-KR':'ko','de-DE':'de','it-IT':'it','pt-PT':'pt','nl-NL':'nl','pl-PL':'pl','sv-SE':'sv','da-DK':'da','fi-FI':'fi','nb-NO':'no','cs-CZ':'cs'}
NUMBERS={'two thousand twenty five':'2025','two thousand twenty':'2020','twenty five thousand':'25000','eighteen thousand':'18000','thirty nine':'39','seventeen':'17','thirteen':'13','thirty':'30','sixty':'60','twelve metres':'12metres','Kostenki eleven':'Kostenki11'}
def chapter_source(ch):
    text=' '.join(x['voice'] for x in source if x['start']>=int(ch['start_seconds']) and x['end']<=int(ch['end_seconds']))
    for a,b in NUMBERS.items():text=text.replace(a,b)
    fixes={'biological sex':'biological male or female sex','sex estimates':'biological male or female classifications','a densely occupied house':'a house used intensively by people','ordinary domestic life':'ordinary daily life in a dwelling','pantry':'place for food storage','working space':'space for practical work','activity traces':'physical traces of human activities','flotation':'archaeological water flotation for recovering small remains','loose organic material':'loose organic matter','Calendar calibration':'Calibration into calendar years','material age':'age of the material','charred remains':'charred biological remains','inbuilt age':'inbuilt age of the sampled biological material'}
    for a,b in fixes.items():text=text.replace(a,b)
    return text
def translate(text,lang):
    u='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode(dict(client='gtx',sl='en',tl=lang,dt='t',q=text))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=50) as f:j=json.load(f)
            out=''.join(a[0] for a in j[0] if a and a[0]);assert out.strip();return ' '.join(out.replace('\u200b','').split())
        except urllib.error.HTTPError as e:
            if e.code not in [429,500,502,503,504] or attempt==2:raise
            n=e.headers.get('Retry-After','');delay=int(n) if n.isdigit() else 15*(attempt+1);print('TRANSLATION_BACKOFF',e.code,delay,flush=True);time.sleep(delay)
        except Exception:
            if attempt==2:raise
            time.sleep(10)
def adapt(t,loc):
    fix={'pt-PT':[('DNA','ADN'),('equipe','equipa'),('registro','registo'),('pesquisadores','investigadores'),('sequenciamento','sequenciação'),('compartilhar','partilhar'),('planejar','planear'),('contato','contacto'),('confiável','fiável')],'vi-VN':[('DNA','ADN'),('hẹn hò','định tuổi'),('tủy sống','tủy xương'),('đầu lâu ma mút','sọ voi ma mút')],'es-ES':[('computadoras','ordenadores')]}
    for a,b in fix.get(loc,[]):t=t.replace(a,b)
    return t
def run(loc):
    p=S/f'{loc}.json';part=p.with_suffix('.partial.json')
    if p.exists() and p.with_suffix('.translated19').exists():return loc
    rows=json.loads(part.read_text()) if part.exists() else []
    for i in range(len(rows),12):
        ch=chapters[i];en=chapter_source(ch);out=adapt(translate(en,LANGS[loc]),loc)
        for sentence in [s.strip() for s in re.split(r'(?<=[.!?])\s+',en) if len(s.strip())>=25]:
            if sentence in out:
                time.sleep(2);a=adapt(translate(sentence,LANGS[loc]),loc)
                if sentence in a:raise ValueError('Untranslated English span '+loc+':'+str(i+1))
                out=out.replace(sentence,a)
        rows.append(dict(id=i+1,start=int(ch['start_seconds']),end=int(ch['end_seconds']),voice=out,source_en=en,editorial_status='Machine translation and regional terminology adaptation;assistant review pending;independent native review pending'))
        part.write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps({'translation':loc,'chapter':i+1,'characters':len(out)}),flush=True);time.sleep(2)
    p.write_text(json.dumps(rows,ensure_ascii=False,indent=2));p.with_suffix('.txt').write_text('\n\n'.join(r['voice'] for r in rows));p.with_suffix('.translated19').write_text(hashlib.sha256(p.read_bytes()).hexdigest());part.unlink(missing_ok=True)
    return loc
if __name__=='__main__':
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(run,l):l for l in (sys.argv[1:] or LANGS)}
        for f in concurrent.futures.as_completed(tasks):
            try:print('TRANSLATED',f.result(),flush=True)
            except Exception as e:errors.append(tasks[f]);print('TRANSLATION_ERROR',tasks[f],type(e).__name__,str(e),flush=True)
    if errors:raise SystemExit('Unfinished locales:'+','.join(errors))
