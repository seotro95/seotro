import concurrent.futures,json,os,sys,time,threading,re
from pathlib import Path

ROOT=Path(os.environ.get('PRODUCTION_WORK_DIR',Path(__file__).resolve().parent)).resolve();sys.path.insert(0,str(ROOT))
os.environ.setdefault('MELO_VIET_ROOT',str(ROOT/'melo-data'))
assert (ROOT/'DOCUMENT_DELIVERY_STATE.json').exists(),'Deliver documents before starting voice.'
import edge_tts.voices,edge_tts.communicate
for module in [edge_tts.voices,edge_tts.communicate]:
    if os.environ.get('SSL_CERT_FILE'):module._SSL_CTX.load_verify_locations(cafile=os.environ['SSL_CERT_FILE'])
from render_common import AUDIO,BASE,PROFILES,chunks,finalize
import online_backend
from prosody import begin,style_wav,install_edge_adapter,EN_PACING_REPAIRS
install_edge_adapter()

def render_locale(locale):
    script=BASE/'scripts'/f'{locale}.json'
    deadline=time.monotonic()+1200
    while not script.exists() or (locale!='en-US' and not script.with_suffix('.terminology-v2').exists()):
        if time.monotonic()>deadline:raise TimeoutError('Translation not ready: '+locale)
        time.sleep(2)
    rows=json.loads(script.read_text());out=AUDIO/locale;out.mkdir(exist_ok=True)
    report=out/'render_report.json'
    if report.exists():return locale
    records=[]
    stop=threading.Event()
    for cue,row in enumerate(rows):
        texts=([row['voice'].strip()] if cue+1 in EN_PACING_REPAIRS else re.split(r'(?<=[.!?])\s+',row['voice'].strip())) if locale=='en-US' else chunks(row['voice'],limit=int(os.environ.get('TTS_CHUNK_LIMIT','480')))
        for n,text in enumerate(texts):records.append((cue,text,out/f'raw-{cue+1:03d}-{n+1:02d}.wav'))
    def render_piece(text,path,depth=0):
        if path.exists():return
        # A NoAudio response for a long request is retried once with smaller,
        # faithful pieces, using the exact same voice. Auth/rate errors stop.
        try:
            online_backend.handle({'op':'render','language':locale,'voice':PROFILES[locale]['voice_id'],'text':text,'output':str(path)})
        except RuntimeError as e:
            if '[NoAudioReceived]' not in str(e) or len(text)<120 or depth>=3:
                raise
            pieces=chunks(text,limit=max(60,min(180,len(text)//2)))
            assert len(pieces)>1
            print(json.dumps({'provider_split':locale,'characters':len(text),'pieces':len(pieces),'depth':depth}),flush=True)
            children=[]
            for i,piece in enumerate(pieces):
                child=path.with_name(path.stem+f'-retry-{depth}-{i:02d}.wav')
                render_piece(piece,child,depth+1);children.append(child)
            import subprocess
            concat=path.with_suffix('.concat.txt')
            assert all("'" not in str(p.resolve()) for p in children)
            concat.write_text(''.join("file '"+str(p.resolve())+"'\n" for p in children))
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(path)],check=True)
            concat.unlink()
            path.with_suffix('.words.jsonl').unlink(missing_ok=True)  # Combined fallback has no trustworthy joined word offsets.
            for child in children:child.unlink()
    def synth(record):
        cue,text,path=record
        if not path.exists():
            if stop.is_set():raise RuntimeError('Stopped after repeated provider failure; preserve completed pieces.')
            for attempt in range(2):
                try:
                    begin(locale,cue,text,path,int(path.stem.rsplit('-',1)[1])-1)
                    render_piece(text,path);break
                except RuntimeError as e:
                    if any(code in str(e) for code in ['HTTP 401','HTTP 403','429']) or attempt==1:
                        stop.set();raise
                    print(json.dumps({'provider_backoff':locale,'cue':cue+1,'seconds':20}),flush=True)
                    time.sleep(20)
            time.sleep(.5)
        if not path.with_suffix('.style.json').exists():
            cfg=begin(locale,cue,text,path,int(path.stem.rsplit('-',1)[1])-1)
            style_wav(path,locale,cfg)
        return path
    if locale=='en-US':
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            for index,path in enumerate(pool.map(synth,records),1):
                if index%11==0:print(json.dumps({'synthesis':locale,'parts':index,'total':len(records)}),flush=True)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('TTS_LOCALE_WORKERS','2'))) as pool:
            for index,path in enumerate(pool.map(synth,records),1):
                if index%6==0:print(json.dumps({'synthesis':locale,'parts':index,'total':len(records)}),flush=True)
    finalize(locale,rows,records,out);return locale

if __name__=='__main__':
    catalog=online_backend.get_catalog();lookup={v['ShortName']:v for v in catalog}
    locales=sys.argv[1:] or [l for l in PROFILES if l!='mww']
    for locale in locales:
        p=PROFILES[locale];assert lookup[p['voice_id']]['Gender']=='Male'
    with concurrent.futures.ThreadPoolExecutor(max_workers=2 if 'en-US' not in locales else 1) as pool:
        futures={pool.submit(render_locale,l):l for l in locales}
        errors=[]
        for f in concurrent.futures.as_completed(futures):
            try:print('FINISHED',f.result(),flush=True)
            except Exception as e:
                print('VOICE_ERROR',futures[f],type(e).__name__,str(e),flush=True);errors.append(futures[f])
        if errors:raise SystemExit(1)
