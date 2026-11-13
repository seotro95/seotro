import concurrent.futures,difflib,hashlib,json,sys,time
from render_common import R,S,A,PROFILES,normalized,split,accent,finish
from online_transport import request,configure,BACKENDS,IncompleteSpeechError
locale=sys.argv[1];assert locale not in ['en-US','mww'];assert (S/f'{locale}.reviewed91').exists()
assert json.loads((R/'DOCUMENT_DELIVERY_STATE.json').read_text())['documents_published']
rows=json.loads((S/f'{locale}.json').read_text());assert len(rows)==14 and rows[-1]['end']==1332
out=A/locale;out.mkdir(parents=True,exist_ok=True);BACKENDS[locale]=configure(locale);records=[];raws=[]
for i,row in enumerate(rows):
 paths=[]
 for j,text in enumerate(split(row['voice'],700)):
  p=out/f'raw-{i+1:03}-{j+1:02}.wav';paths.append(p);records.append((i,j,text,p))
 raws.append(paths)
def synth(item):
 i,j,text,p=item;rate=-1-(1 if '?' in text or '？' in text else 0)-(2 if i==len(rows)-1 else 0)+(1 if j%2 else 0);rate=f'{rate:+d}%';sig=hashlib.sha256((text+'\0'+PROFILES[locale]['voice_id']+'\0'+rate).encode()).hexdigest();m=p.with_suffix('.meta.json')
 if p.exists() and m.exists() and json.loads(m.read_text()).get('request_signature')==sig:return p
 words=request(locale,text,p,rate);coverage=difflib.SequenceMatcher(None,normalized(text),normalized(''.join(w['text'] for w in words)),autojunk=False).ratio()
 assert coverage>=.97,(locale,i+1,j+1,'incomplete word metadata',coverage)
 count=accent(p,words,locale);m.write_text(json.dumps({'request_signature':sig,'voice_id':PROFILES[locale]['voice_id'],'rate':rate,'coverage':coverage,'accents':count,'source_words':len(words)}));time.sleep(.25);return p
pending=[];complete=0
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures={pool.submit(synth,item):item for item in records}
 for f in concurrent.futures.as_completed(futures):
  try:f.result();complete+=1
  except Exception as e:
   import edge_tts
   if isinstance(e,(edge_tts.exceptions.NoAudioReceived,IncompleteSpeechError)):pending.append([futures[f][0]+1,futures[f][1]+1]);print('SPEECH_PENDING',locale,pending[-1],flush=True)
   else:
    for other in futures:other.cancel()
    raise
  if complete and complete%10==0:print('SYNTH',locale,complete,len(records),flush=True)
if pending:
 (out/'pending_speech.json').write_text(json.dumps(pending));print('Transient country speech parts pending; successful speech retained',flush=True);sys.exit(75)
finish(locale,rows,raws,out=out)
