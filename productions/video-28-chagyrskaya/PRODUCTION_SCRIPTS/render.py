import concurrent.futures,asyncio,json,os,sys,re,subprocess,wave,time,hashlib,unicodedata,difflib
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'melo'))
os.environ['MELO_VIET_ROOT']=str(R/'melo-data')
import edge_tts,edge_tts.voices,edge_tts.communicate
for m in [edge_tts.voices,edge_tts.communicate]:m._SSL_CTX.load_verify_locations(cafile=os.environ.get('SSL_CERT_FILE','/etc/ssl/certs/ca-certificates.crt'))
import online_backend
profiles={p['locale']:p for p in json.loads((R/'BASELINE_VOICE_PROFILES.json').read_text())['profiles']}
def command(args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-threads','1',*map(str,args)],check=True)
def split(text,limit=750):
    sentences=re.split(r'(?<=[.!?。！？])\s*',text)
    pieces=[];current=''
    for sentence in sentences:
        if not sentence:continue
        if len(sentence)>limit:
            if current:pieces.append(current);current=''
            words=sentence.split();part=''
            if len(words)<2:pieces.extend(sentence[i:i+limit] for i in range(0,len(sentence),limit));continue
            for word in words:
                if len(part+' '+word)>limit:pieces.append(part);part=''
                part=(part+' '+word).strip()
            if part:pieces.append(part)
        elif len(current+' '+sentence)>limit:pieces.append(current);current=sentence
        else:current=(current+' '+sentence).strip()
    if current:pieces.append(current)
    assert pieces and all(0<len(p)<=1200 for p in pieces)
    return pieces
def duration(path):
    with wave.open(str(path)) as w:return w.getnframes()/w.getframerate()
def final(locale,rows,raws):
    out=R/'voice/audio'/locale;report=[];prepared=[]
    for idx,(row,paths) in enumerate(zip(rows,raws)):
        concat=out/'raw-concat.txt';concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in paths))
        joined=out/f'joined-{idx:03}.wav'
        command(['-f','concat','-safe','0','-i',concat,'-ar','48000','-ac','1','-c:a','pcm_s16le',joined])
        seconds=duration(joined);target=row['end']-row['start'];pause=.16 if target>2 else .08
        tempo=seconds/(target-pause)
        if not .5<=tempo<=1.65:raise RuntimeError(f'Unacceptable tempo {locale} cue{idx+1}: {tempo:.3f}; retain audio for repair')
        dest=out/f'cue-{idx:03}.wav';frames=target*48000
        command(['-i',joined,'-af',f'atempo={tempo:.9f},apad,atrim=end_sample={frames}','-ar','48000','-ac','1','-c:a','pcm_s16le',dest])
        with wave.open(str(dest)) as w:assert w.getnframes()==frames
        report.append(dict(id=row['id'],start=row['start'],end=row['end'],raw_seconds=seconds,tempo=tempo,trailing_pause_target=pause,parts=len(paths)))
        prepared.append(dest);joined.unlink()
    concat=out/'final-concat.txt';concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in prepared))
    dst=out/f'CHAGYRSKAYA_28_{locale}.mp3'
    command(['-f','concat','-safe','0','-i',concat,'-af','loudnorm=I=-19:TP=-2:LRA=8','-ar','48000','-ac','1','-c:a','libmp3lame','-b:a','96k',dst])
    decoded=out/'decoded.wav';command(['-i',dst,'-ar','48000','-ac','1','-c:a','pcm_s16le',decoded])
    with wave.open(str(decoded)) as w:n=w.getnframes();assert n==1362*48000,(locale,n)
    decoded.unlink()
    p=profiles[locale]
    j=dict(locale=locale,voice_id=p['voice_id'],gender=p['gender'],source_commit=p['source_commit'],target_seconds=1362,decoded_frames_48000=n,decoded_seconds=n/48000,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),filename=dst.name,bytes=dst.stat().st_size,cues=report,pitch_shift=False,technical_qa_passed=True,independent_native_listening_review=False,translation_method='original' if locale=='en-US' else 'Google automated draft; assistant context checks; independent native editorial review pending')
    if locale=='mww':j.update(reference_sha256=p['reference_sha256'],white_hmong_dialect_independently_verified=False)
    (out/'render_report.json').write_text(json.dumps(j,ensure_ascii=False,indent=2));print('VOICE_DONE',locale,flush=True)
    return j
def online(locale):
    out=R/'voice/audio'/locale;out.mkdir(parents=True,exist_ok=True)
    if (out/'render_report.json').exists():return locale
    rows=json.loads((R/'voice/scripts'/f'{locale}.json').read_text());raws=[]
    # Adapter retains the selected tool's backend and voice; adds native rate and word metadata.
    rate='-12%' if locale=='en-US' else '+0%'
    async def download(text,voice,output):
        error=None
        for attempt in range(3):
            words=[]
            try:
                s=edge_tts.Communicate(text,voice,rate=rate,volume='+0%',pitch='+0Hz',boundary='WordBoundary',proxy=os.environ.get('HTTPS_PROXY'),connect_timeout=20,receive_timeout=60)
                with Path(output).open('wb') as f:
                    async for chunk in s.stream():
                        if chunk['type']=='audio':f.write(chunk['data'])
                        elif chunk['type']=='WordBoundary':words.append(chunk)
                assert Path(output).stat().st_size>0
                Path(output).with_suffix('.words.json').write_text(json.dumps(words,ensure_ascii=False))
                return
            except Exception as e:error=e;await asyncio.sleep(2*(attempt+1))
        raise error
    online_backend.download_audio=download
    records=[]
    for idx,row in enumerate(rows):
        paths=[]
        for part,text in enumerate(split(row['voice'])):
            dest=out/f'raw-{idx+1:03}-{part+1:02}.wav';paths.append(dest);records.append((text,dest))
        raws.append(paths)
    def synth(item):
        text,dest=item
        for attempt in range(3):
            if not dest.exists():
                online_backend.handle(dict(op='render',language=locale,voice=profiles[locale]['voice_id'],text=text,output=str(dest)))
            meta=dest.with_suffix('.edge.words.json')
            words=json.loads(meta.read_text());actual=''.join(w['text'] for w in words)
            norm=lambda s:''.join(c for c in unicodedata.normalize('NFKC',s).lower() if c.isalnum())
            ratio=difflib.SequenceMatcher(None,norm(text),norm(actual),autojunk=False).ratio()
            if ratio>=.97:break
            dest.unlink();meta.unlink();print('REPAIR_INCOMPLETE',locale,dest.name,ratio,flush=True)
            if attempt==2:raise RuntimeError('Provider repeatedly omitted words: '+str(dest))
        return dest
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for idx,dest in enumerate(pool.map(synth,records),1):
            if idx%10==0:print('SYNTH',locale,idx,len(records),flush=True)
    final(locale,rows,raws);return locale
if __name__=='__main__':
    # Serial locale jobs avoid global adapter settings colliding. Pieces run concurrently.
    online_backend.get_catalog()
    for locale in sys.argv[1:] or ['en-US']:online(locale)
