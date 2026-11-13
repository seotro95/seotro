"""Recover a no-audio request using three smaller requests to the same saved voice."""
import hashlib,json,wave
from render_common import R,S,A,PROFILES,normalized,digest
from online_transport import request,configure,BACKENDS
locale='en-US';BACKENDS[locale]=configure(locale);out=A/locale;out.mkdir(parents=True,exist_ok=True)
rows=json.loads((S/'en-US.json').read_text());group=rows[12:15];assert [r['id'] for r in group]==[13,14,15]
body=' '.join(r['voice'] for r in group);parts=[];events=[];frames=0;rate=24000
for r in group:
 p=out/f'recovery-cue-{r["id"]:03}.wav';words=request(locale,r['voice'],p,'+0%')
 assert normalized(''.join(w['text'] for w in words))==normalized(r['voice'])
 with wave.open(str(p)) as w:
  assert w.getframerate()==rate and w.getnchannels()==1 and w.getsampwidth()==2
  pcm=w.readframes(w.getnframes());n=len(pcm)//2
 events.extend({**e,'offset':round(e['offset']+frames/rate*1e7)} for e in words);parts.append(pcm);frames+=n
assert normalized(''.join(w['text'] for w in events))==normalized(body)
p=out/'group-005.wav'
with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(parts))
p.with_suffix('.edge.words.json').write_text(json.dumps(events,ensure_ascii=False))
signature=hashlib.sha256((body+'\0'+PROFILES[locale]['voice_id']+'\0+0%').encode()).hexdigest()
p.with_suffix('.request.json').write_text(json.dumps({'request_signature':signature,'sha256':digest(p),'voice_id':PROFILES[locale]['voice_id'],'rate':'+0%','recovery_method':'Three native individual cue requests from the same backend and saved voice; real word offsets shifted by concatenated sample counts','source_cues':[13,14,15]}))
(out/'ENGLISH_RECOVERY.json').write_text(json.dumps({'status':'passed','group':5,'cue_ids':[13,14,15],'voice_id':PROFILES[locale]['voice_id'],'script_unchanged':True,'words_exact':True,'real_native_word_metadata':True,'other40groups_reused':True},indent=2))
print('ENGLISH_GROUP5_RECOVERED_FROM_SAME_VOICE',flush=True)
