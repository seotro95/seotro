import hashlib,json,re,sys,wave
from pathlib import Path
from render_episode import R,S,A,PROFILES,online,split,finish,normalized
out=A/'en-US';out.mkdir(parents=True,exist_ok=True)
rows=json.loads((S/'en-US.json').read_text());assert len(rows)==136 and rows[-1]['end']==1352
mode=sys.argv[1]
if mode=='shard':
 shard=int(sys.argv[2]);assert 0<=shard<4
 start=34*shard;end=min(34*(shard+1),len(rows))
 for p in out.glob('raw-*'):
  m=re.match(r'raw-(\d{3})-',p.name)
  if m and not start<=int(m[1])-1<end:p.unlink()
 result=online('en-US',synthesis_range=(start,end),synthesis_only=True)
 (out/f'SHARD_{shard}_QA.json').write_text(json.dumps(result,indent=2));print('ENGLISH_SHARD_COMPLETE',shard,result,flush=True)
elif mode=='finalize':
 raws=[]
 for i,row in enumerate(rows):
  paths=[]
  for j,text in enumerate(split(row['voice'],limit=700)):
   p=out/f'raw-{i+1:03}-{j+1:02}.wav';assert p.exists(),f'Missing speech cue {i+1}'
   meta=json.loads(p.with_suffix('.meta.json').read_text())
   rate=-8
   if '?' in text or '？' in text:rate-=1
   if i>=len(rows)-max(1,len(rows)//12):rate-=2
   if j%2:rate+=1
   sig=hashlib.sha256((text+'\0'+PROFILES['en-US']['voice_id']+'\0'+f'{rate:+d}%').encode()).hexdigest()
   assert meta['request_signature']==sig and meta['voice_id']==PROFILES['en-US']['voice_id'] and meta['coverage']>=.97
   with wave.open(str(p)) as w:assert w.getnframes()>0 and w.getnchannels()==1 and w.getframerate()==24000
   paths.append(p)
  raws.append(paths)
 result=finish('en-US',rows,raws,out=out);assert result['decoded_frames_48000']==64896000
 print('COMPLETE_ENGLISH_VERIFIED',result['sha256'],flush=True)
else:raise ValueError(mode)
