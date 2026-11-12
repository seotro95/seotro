import concurrent.futures,hashlib,json,sys,wave
from pathlib import Path
from render_common import R,S,A,PROFILES,normalized,finish,accent,digest
from online_transport import request,configure,BACKENDS
preview='--preview' in sys.argv
assert json.loads((R/'DOCUMENT_DELIVERY_STATE.json').read_text())['documents_published']
rows=json.loads((S/'en-US.json').read_text());assert len(rows)==136 and rows[-1]['end']==1358
if preview:rows=rows[:3]
out=R/'voice/en_preview' if preview else A/'en-US';out.mkdir(parents=True,exist_ok=True)
BACKENDS['en-US']=configure('en-US');groups=[rows[i:i+3] for i in range(0,len(rows),3)]
def synth(pair):
 index,group=pair;body=' '.join(x['voice'] for x in group);rate='+0%';source=out/f'group-{index+1:03}.wav'
 words=request('en-US',body,source,rate)
 observed=''.join(normalized(x['text']) for x in words);expected=normalized(body)
 assert observed==expected,f'English word metadata differs from script in group{index+1}'
 with wave.open(str(source)) as w:
  sr=w.getframerate();assert sr==24000 and w.getnchannels()==1 and w.getsampwidth()==2;pcm=w.readframes(w.getnframes());total=len(pcm)//2
 counts=[len(normalized(x['voice'])) for x in group];ends=[];n=0
 for c in counts:n+=c;ends.append(n)
 by_cue=[[] for _ in group];n=0;k=0
 for word in words:
  chars=len(normalized(word['text']))
  if not chars:continue
  while k<len(ends)-1 and n>=ends[k]:k+=1
  assert n+chars<=ends[k],'Word metadata spans a scripted cue boundary'
  by_cue[k].append(word);n+=chars
 assert n==len(expected) and all(by_cue)
 bounds=[0]
 for left,right in zip(by_cue,by_cue[1:]):
  end=(left[-1]['offset']+left[-1]['duration'])/1e7;start=right[0]['offset']/1e7
  assert start>=end-.03,('Overlapping English cue boundary',index+1,end,start)
  bounds.append(round((end+start)/2*sr))
 bounds.append(total);assert all(a<b for a,b in zip(bounds,bounds[1:]))
 for i,row in enumerate(group):
  p=out/f'raw-{row["id"]:03}-01.wav';signature=hashlib.sha256((row['voice']+'\0'+PROFILES['en-US']['voice_id']+'\0'+rate).encode()).hexdigest()
  events=[{**e,'offset':max(0,round(e['offset']-bounds[i]/sr*1e7))} for e in by_cue[i]]
  with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm[bounds[i]*2:bounds[i+1]*2])
  accents=accent(p,events,'en-US');p.with_suffix('.meta.json').write_text(json.dumps({'request_signature':signature,'voice_id':PROFILES['en-US']['voice_id'],'rate':rate,'coverage':1.0,'accents':accents,'source_words':len(events),'source_group_id':index+1,'source_group_sha256':digest(source),'crop_start_sample_24000':bounds[i],'crop_end_sample_24000':bounds[i+1]}))
 print('ENGLISH_GROUP_DONE',index+1,len(groups),'cues',[r['id'] for r in group],flush=True)
 return index
pending=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures={pool.submit(synth,pair):pair[0] for pair in enumerate(groups)}
 for future in concurrent.futures.as_completed(futures):
  try:future.result()
  except Exception as e:
   import edge_tts
   if isinstance(e,edge_tts.exceptions.NoAudioReceived):pending.append(futures[future]);print('ENGLISH_GROUP_PENDING',futures[future]+1,flush=True)
   else:
    for f in futures:f.cancel()
    raise
if pending:
 (out/'pending_groups.json').write_text(json.dumps(pending));print('Transient English parts pending; successful speech retained',flush=True);sys.exit(75)
raws=[[out/f'raw-{r["id"]:03}-01.wav'] for r in rows]
result=finish('en-US',rows,raws,out=out,target=30 if preview else 1358)
result.update(grouped_requests=len(groups),word_metadata_exact_script_match=True,word_boundary_cue_split=True,transport_base_rate='+0%',prosody_method='Native0%groupedEnglish with originalpunctuation, atmosttwo1.2dBwordaccentspercue andpitch-preservingfinalfit')
(out/'render_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('ENGLISH_COMPLETE',result['decoded_frames_48000'],flush=True)
