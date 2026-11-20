"""Keep all existing speech except cue 134; give the two-second ending natural native pacing."""
import hashlib,json,wave
from render_common import R,S,A,PROFILES,digest,normalized,finish,accent,seconds
from online_transport import request,configure,BACKENDS
rows=json.loads((S/'en-US.json').read_text());assert len(rows)==134 and rows[-1]['voice']=='Keep looking.' and rows[-1]['end']==1332
out=A/'en-US';assert out.is_dir();voice=PROFILES['en-US']['voice_id']
# Check every original group against its genuine provider word metadata and source WAV hash.
groups=[rows[i:i+3] for i in range(0,len(rows),3)]
for index,g in enumerate(groups,1):
 source=out/f'group-{index:03}.wav';m=json.loads(source.with_suffix('.request.json').read_text());w=json.loads(source.with_suffix('.edge.words.json').read_text())
 assert m['sha256']==digest(source) and m['voice_id']==voice and m['rate']=='+2%'
 assert normalized(''.join(x['text'] for x in w))==normalized(' '.join(x['voice'] for x in g))
for row in rows[:-1]:
 p=out/f'raw-{row["id"]:03}-01.wav';m=json.loads(p.with_suffix('.meta.json').read_text())
 expected=hashlib.sha256((row['voice']+'\0'+voice+'\0+2%').encode()).hexdigest()
 assert m['request_signature']==expected and m['coverage']==1 and m['voice_id']==voice
 assert m['source_group_sha256']==digest(out/f'group-{m["source_group_id"]:03}.wav')
print('ORIGINAL_45_GROUPS_AND_133_CUES_VERIFIED_NO_REGENERATION',flush=True)
BACKENDS['en-US']=configure('en-US');last=rows[-1];source=out/'ending-native-slower.wav';rate='-12%'
words=request('en-US',last['voice'],source,rate,attempts=3)
assert normalized(''.join(x['text'] for x in words))==normalized(last['voice'])
duration=seconds(source);tempo=duration/1.92
assert .55<=tempo<=1.65,('ending still outside unchanged pacing gate',duration,tempo)
p=out/'raw-134-01.wav';p.write_bytes(source.read_bytes());accents=accent(p,words,'en-US')
p.with_suffix('.meta.json').write_text(json.dumps(dict(request_signature=hashlib.sha256((last['voice']+'\0'+voice+'\0'+rate).encode()).hexdigest(),voice_id=voice,rate=rate,coverage=1.0,accents=accents,source_words=len(words),source_ending_sha256=digest(source),method='Same Andrew voice and pitch, native slower final phrase only')))
raws=[[out/f'raw-{x["id"]:03}-01.wav'] for x in rows];report=finish('en-US',rows,raws,out=out,target=1332)
report.update(word_metadata_exact_script_match=True,word_boundary_cue_split=True,transport_base_rate='+2%',final_cue_native_rate=rate,original_group_checkpoint_count=45,original_cues_reused=133,regenerated_cue_ids=[134],original_source_run=44761841149,prosody_method='Original 133 cue speech retained; same Andrew and zero pitch shift; final phrase natively slower at -12%; original pacing gate .55–1.65 retained')
(out/'render_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('ENGLISH_ENDING_REPAIR_AND_FULL_22m12s_PASSED',flush=True)
