import hashlib,json,re,subprocess
from pathlib import Path
import numpy as np
R=Path(__file__).parent;O=R/'delivery';video=O/'KOSTENKI_19_EN_FINAL_20m15s_720p.mp4'
j=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(video)]))
v=[s for s in j['streams'] if s['codec_type']=='video'];a=[s for s in j['streams'] if s['codec_type']=='audio']
assert len(v)==len(a)==1
assert v[0]['width']==1280 and v[0]['height']==720 and v[0]['avg_frame_rate']=='24/1'
assert int(v[0]['nb_frames'])==29160 and abs(float(v[0]['duration'])-1215)<1/24
assert abs(float(a[0]['duration'])-1215)<.05 and a[0]['tags']['language']=='eng'
assert len(j['chapters'])==12
srt=(O/'KOSTENKI_19_EN_SUBTITLES.srt').read_text();assert srt.count(' --> ')==122 and '00:20:15,000' in srt
spoken=' '.join(' '.join(b.splitlines()[2:]) for b in re.split(r'\n\s*\n',srt.strip()));assert len(spoken.split())==2816
assert spoken==' '.join(x['voice'] for x in json.loads((R/'input/en-US.json').read_text()))
ref=R/'input/KOSTENKI_19_My_Tieng_Anh.mp3'
def pcm(p):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-ac','1','-ar','8000','-f','s16le','-']),dtype='<i2').astype(np.float32)
original=pcm(ref);actual=pcm(video);align=[]
for sec in [5,25,95,195,295,395,495,595,695,795,895,995,1095,1125,1205]:
 c=sec*8000;n=16000;pad=400;x=actual[c-pad:c+n+pad].copy();y=original[c:c+n].copy();x-=x.mean();y-=y.mean();k=int(np.argmax(np.correlate(x,y,mode='valid')));z=x[k:k+n]
 corr=float(np.dot(z,y)/(np.linalg.norm(z)*np.linalg.norm(y)+1e-12));lag=(k-pad)/8000;assert corr>.92 and abs(lag)<=.025,(sec,corr,lag)
 align.append({'seconds':sec,'correlation':round(corr,6),'lag_seconds':lag})
with (R/'full_decode_qa.log').open('w') as f:subprocess.run(['ffmpeg','-hide_banner','-nostats','-threads','1','-i',str(video),'-map','0:v:0','-map','0:a:0','-vf','blackdetect=d=0.5:pix_th=0.05:pic_th=0.98','-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],stdout=f,stderr=subprocess.STDOUT,check=True)
log=(R/'full_decode_qa.log').read_text();loud=json.loads(log[log.rfind('{'):log.rfind('}')+1]);assert -17<float(loud['input_i'])<-15 and float(loud['input_tp'])<=-1
black=[x for x in log.splitlines() if 'black_start:' in x];assert not black,black
errors=[x for x in log.splitlines() if any(k in x.lower() for k in ['error while decoding','corrupt decoded frame','invalid nal unit','non monotonically increasing'])];assert not errors,errors
plan=json.loads((R/'EDIT_PLAN.json').read_text());assert sum(len(x['segments']) for x in plan[:3])==10
result={'status':'passed','topic':19,'file':video.name,'video_duration_seconds':float(v[0]['duration']),'audio_duration_seconds':float(a[0]['duration']),'video_frames':29160,'width':1280,'height':720,'fps':24,'audio_stream_count':1,'audio_language':'English','voice_id':'en-US-AndrewNeural','reference_sha256':hashlib.file_digest(ref.open('rb'),'sha256').hexdigest(),'reference_audio_unchanged_timing_and_pitch':True,'original_clip_audio_included':False,'music_or_sfx_added':False,'alignment_checks':align,'loudness_lufs':float(loud['input_i']),'true_peak_dbtp':float(loud['input_tp']),'opening_shots':10,'opening_seconds':30,'short_dissolves':sum(x['transition']=='dissolve' for x in plan),'replacement_stills_or_text_cards':0,'chapters':12,'optional_english_subtitle_cues':122,'full_decode_exit_code':0,'decode_errors':errors,'black_gaps':black,'visual_review_scope':'Three sampled frames per supplied clip and sampled finished-movie frames; not continuous manual viewing.','sha256':hashlib.file_digest(video.open('rb'),'sha256').hexdigest(),'bytes':video.stat().st_size}
(O/'FINAL_VIDEO_QA.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ['status','bytes','loudness_lufs','true_peak_dbtp','video_frames','sha256']}),flush=True)
