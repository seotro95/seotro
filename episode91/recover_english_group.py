"""Smaller same-voice requests with genuine word metadata, preserving successful audio."""
import hashlib,json,wave
from render_common import PROFILES,normalized,digest
from online_transport import request
def recover(group,index,source):
 out=source.parent;events=[];chunks=[];frames=0;rate=24000
 for row in group:
  p=out/f'fallback-group-{index+1:03}-cue-{row["id"]:03}.wav'
  words=request('en-US',row['voice'],p,'+0%',attempts=4)
  assert normalized(''.join(w['text'] for w in words))==normalized(row['voice'])
  with wave.open(str(p)) as w:
   assert w.getframerate()==rate and w.getnchannels()==1 and w.getsampwidth()==2
   pcm=w.readframes(w.getnframes());n=len(pcm)//2
  events.extend({**e,'offset':round(e['offset']+frames/rate*1e7)} for e in words);chunks.append(pcm);frames+=n
 body=' '.join(r['voice'] for r in group);assert normalized(''.join(e['text'] for e in events))==normalized(body)
 with wave.open(str(source),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(chunks))
 source.with_suffix('.edge.words.json').write_text(json.dumps(events,ensure_ascii=False))
 voice=PROFILES['en-US']['voice_id'];sig=hashlib.sha256((body+'\0'+voice+'\0+0%').encode()).hexdigest()
 source.with_suffix('.request.json').write_text(json.dumps({'request_signature':sig,'sha256':digest(source),'voice_id':voice,'rate':'+0%','smaller_native_requests':[r['id'] for r in group],'method':'Same voice/backend; real word offsets shifted by concatenated sample counts'}))
 print('ENGLISH_SMALLER_REQUEST_RECOVERY',index+1,[r['id'] for r in group],flush=True)
 return events
