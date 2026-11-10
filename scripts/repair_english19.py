"""Repair only failed English cue113; retain every other synthesized cue."""
import hashlib,json,os,re,shutil,subprocess,sys,urllib.request,wave
from pathlib import Path

work=Path('repair19').resolve();work.mkdir(exist_ok=True)
tool=work/'melo-tool';tool.mkdir(exist_ok=True)
for name,rec in json.loads(Path('input/source_integrity.json').read_text()).items():
    data=urllib.request.urlopen(rec['url'],timeout=60).read()
    assert hashlib.sha256(data).hexdigest()==rec['sha256']
    (tool/name).write_bytes(data)
sys.path[:0]=[str(tool),str(Path('scripts').resolve())]
import online_backend
from documents import convert_audio
from timing import TimedAssembler,measure_encoded
from prosody import begin,install_edge_adapter,style_wav
install_edge_adapter()
folder=Path('artifacts/k19-voice-en-US')
report_path=folder/'render_report.json';old=json.loads(report_path.read_text())
old_audio=folder/old['mp3_file'];old_hash=hashlib.sha256(old_audio.read_bytes()).hexdigest()
assert old_hash==old['mp3_sha256'] and old['voice_id']=='en-US-AndrewNeural'
rows=json.loads(Path('input/scripts/en-US.json').read_text());row=rows[112]
assert row['start']==1120 and row['end']==1130
bad=[c for c in old['sync_report']['cues'] if c['padding_frames']/48000>.1]
assert [c['cue'] for c in bad]==[113]
raw=work/'cue113.wav';text=row['voice']
cfg=begin('en-US',112,text,raw,0)
online_backend.handle({'op':'render','language':'en-US','voice':'en-US-AndrewNeural','text':text,'output':str(raw)})
events=[json.loads(x) for x in raw.with_suffix('.words.jsonl').read_text().splitlines()]
words=[e['text'] for e in events if e.get('type')=='WordBoundary']
tokens=lambda s:re.findall(r'[a-z]+',s.lower())
assert tokens(' '.join(words))==tokens(text),(words,text)
with wave.open(str(raw)) as w:seconds=w.getnframes()/w.getframerate()
assert len(text.split())*.18<seconds<20,seconds
style_wav(raw,'en-US',cfg)
prepared=work/'prepared.wav';convert_audio(raw,prepared,1,sample_rate=48000,gain_db=0)
plan={'source_format':'srt','target_seconds':10,'target_frames':480000,'cues':[{'start_ms':0,'end_ms':10000,'text':text}]}
assembler=TimedAssembler(work,plan,max_tempo=1.4)
try:assembler.append(prepared,text,cue=0);segment=assembler.finish()
except Exception:assembler.close();raise
cue=segment['sync_report']['cues'][0]
assert cue['padding_frames']/48000<.1
decoded=work/'original.wav'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(old_audio),'-ac','1','-ar','48000','-c:a','pcm_s16le',str(decoded)],check=True)
new_wav=work/'repaired.wav'
with wave.open(str(decoded)) as src,wave.open(str(work/'part-0001.wav')) as fix,wave.open(str(new_wav),'wb') as out:
    assert src.getnframes()==58320000 and fix.getnframes()==480000
    assert src.getnchannels()==fix.getnchannels()==1 and src.getsampwidth()==fix.getsampwidth()==2
    out.setnchannels(1);out.setsampwidth(2);out.setframerate(48000)
    out.writeframesraw(src.readframes(1120*48000));src.readframes(10*48000)
    out.writeframesraw(fix.readframes(480000));out.writeframesraw(src.readframes(src.getnframes()-src.tell()))
with wave.open(str(new_wav)) as w:assert w.getnframes()==58320000
repaired=work/old_audio.name
# A higher final bitrate limits generation loss outside the repaired sentence.
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(new_wav),'-map','0:a:0','-ac','1','-ar','24000','-c:a','libmp3lame','-b:a','128k',str(repaired)],check=True)
duration=measure_encoded(repaired,work,48000,58320000);assert duration['verified']
cue.update(cue=113,start_frame=1120*48000,end_frame=1130*48000)
old['sync_report']['cues'][112]=cue
old.update(mp3_decoded_duration=duration,mp3_bytes=repaired.stat().st_size,mp3_sha256=hashlib.sha256(repaired.read_bytes()).hexdigest())
sync=old['sync_report']['cues']
old.update(max_cue_padding_seconds=max(c['padding_frames'] for c in sync)/48000,max_used_post_tempo=max(c['tempo'] for c in sync),min_used_post_tempo=min(c['tempo'] for c in sync))
assert old['max_cue_padding_seconds']<.1
old['cue113_repair']={'reason':'Provider returned a short audio result; original cue left 9.49 seconds of padding.','cue':113,'start_seconds':1120,'end_seconds':1130,'original_full_audio_sha256':old_hash,'same_voice_id':True,'same_source_commit':True,'same_style_and_pitch':True,'script_unchanged':True,'all_word_boundary_tokens_match':True,'replacement_word_count':len(text.split()),'replacement_word_boundaries':len(words),'other_cues_not_resynthesized':True,'assembly':'Decoded original MP3, replaced only 1120–1130s, re-encoded at128kbps; total and cue boundaries preserved.'}
shutil.copyfile(repaired,old_audio);report_path.write_text(json.dumps(old,ensure_ascii=False,indent=2))
print(json.dumps({'repair':'passed','cue':113,'word_tokens_match':True,'max_padding_seconds':old['max_cue_padding_seconds'],'seconds':1215,'sha256':old['mp3_sha256']}),flush=True)
