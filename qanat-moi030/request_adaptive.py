"""Retry transient incomplete speech with smaller same-voice requests and real word offsets."""
import hashlib,json,wave
from render_common import PROFILES,digest,split
from online_transport import request,IncompleteSpeechError,complete_words

def adaptive(locale,text,path,rate,depth=0):
    try:return request(locale,text,path,rate,attempts=2)
    except Exception as error:
        import edge_tts
        if not isinstance(error,(edge_tts.exceptions.NoAudioReceived,IncompleteSpeechError,TimeoutError)) or depth>=2:raise
        pieces=split(text,300 if depth==0 else 150)
        if len(pieces)<2:raise
    chunks=[];events=[];frames=0;sr=24000
    for i,piece in enumerate(pieces):
        sub=path.with_name(path.stem+f'-small-{i+1:03}.wav')
        words=adaptive(locale,piece,sub,rate,depth+1)
        with wave.open(str(sub)) as w:
            assert w.getframerate()==sr and w.getnchannels()==1 and w.getsampwidth()==2
            pcm=w.readframes(w.getnframes())
        events.extend({**e,'offset':round(e['offset']+frames/sr*1e7)} for e in words)
        chunks.append(pcm);frames+=len(pcm)//2
    assert complete_words(locale,text,events)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(b''.join(chunks))
    path.with_suffix('.edge.words.json').write_text(json.dumps(events,ensure_ascii=False))
    signature=hashlib.sha256((text+'\0'+PROFILES[locale]['voice_id']+'\0'+rate).encode()).hexdigest()
    path.with_suffix('.request.json').write_text(json.dumps(dict(request_signature=signature,sha256=digest(path),voice_id=PROFILES[locale]['voice_id'],rate=rate,smaller_same_voice_requests=len(pieces))))
    print('COUNTRY_SMALLER_REQUEST_RECOVERY',locale,path.name,len(pieces),flush=True)
    return events

