import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np

ROOT=Path('/workspace/work/yana/edit');OUT=ROOT/'delivery'
video=OUT/'YANA_04_EN_FINAL_23m_720p.mp4'
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(video)]))
v=[s for s in probe['streams'] if s['codec_type']=='video'];a=[s for s in probe['streams'] if s['codec_type']=='audio']
assert len(v)==1 and len(a)==1
assert v[0]['width']==1280 and v[0]['height']==720 and v[0]['avg_frame_rate']=='24/1'
assert int(v[0]['nb_frames'])==33120
assert abs(float(v[0]['duration'])-1380)<1/24
assert abs(float(a[0]['duration'])-1380)<.05
assert a[0]['tags'].get('language')=='eng'
assert len(probe['chapters'])==12
subtitles=[s for s in probe['streams'] if s['codec_type']=='subtitle']
assert len(subtitles)==1 and subtitles[0]['tags'].get('language')=='eng'
srt=(OUT/'YANA_04_EN_SUBTITLES.srt').read_text()
assert srt.count(' --> ')==138 and '00:23:00,000' in srt
import re
spoken=' '.join(' '.join(b.splitlines()[2:]) for b in re.split(r'\n\s*\n',srt.strip()))
source=json.loads((ROOT.parent/'voice/scripts/en-US.json').read_text())
assert spoken==' '.join(r['voice'] for r in source) and len(spoken.split())==3648
assert hashlib.sha256(Path('/workspace/work/yana/verified-release/YANA_04_My_Tieng_Anh.mp3').read_bytes()).hexdigest()=='7014702fdb86744e8ddbf8a74eb7ef176bbb4cb9865aaf4e0e7931e27ae0047c'

def pcm(path):
    b=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-ac','1','-ar','8000','-f','s16le','-'])
    return np.frombuffer(b,dtype='<i2').astype(np.float32)
reference=pcm('/workspace/work/yana/verified-release/YANA_04_My_Tieng_Anh.mp3')
actual=pcm(video)
comparisons=[]
for second in [5,105,205,305,405,505,605,705,805,905,1005,1105,1205,1305,1375]:
    c=second*8000;n=16000;pad=400
    r=reference[c:c+n].copy();r-=r.mean()
    x=actual[c-pad:c+n+pad].copy();x-=x.mean()
    corr=np.correlate(x,r,mode='valid');k=int(np.argmax(corr));match=x[k:k+n]
    similarity=float(np.dot(match,r)/(np.linalg.norm(match)*np.linalg.norm(r)+1e-12))
    lag=(k-pad)/8000
    assert abs(lag)<=.025,(second,lag)
    assert similarity>.92,(second,similarity)
    comparisons.append({'reference_seconds':second,'lag_seconds':lag,'waveform_correlation':round(similarity,6)})

log=ROOT/'full_decode_qa.log'
cmd=['ffmpeg','-hide_banner','-nostats','-threads','1','-i',str(video),'-map','0:v:0','-map','0:a:0',
     '-vf','blackdetect=d=0.5:pix_th=0.05:pic_th=0.98',
     '-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-']
with log.open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
raw=log.read_text();last=raw[raw.rfind('{'):raw.rfind('}')+1];loudness=json.loads(last)
assert float(loudness['input_tp'])<=-1.0
assert -17<float(loudness['input_i'])<-15
black=[line for line in raw.splitlines() if 'black_start:' in line]
assert not black,black
errors=[line for line in raw.splitlines() if any(t in line.lower() for t in ['error while decoding','corrupt decoded frame','invalid nal unit','non monotonically increasing'])]
assert not errors,errors

plan=json.loads((ROOT/'EDIT_PLAN.json').read_text())
downloads=json.loads((ROOT/'DOWNLOAD_RECEIPTS.json').read_text())
inventory=json.loads((ROOT/'inventory.json').read_text())
result={
 'status':'passed','final_file':video.name,'video_duration_seconds':float(v[0]['duration']),
 'container_duration_seconds':float(probe['format']['duration']),'audio_duration_seconds':float(a[0]['duration']),
 'video_frames':int(v[0]['nb_frames']),'width':1280,'height':720,'fps':24,
 'video_codec':v[0]['codec_name'],'audio_codec':a[0]['codec_name'],'audio_stream_count':1,
 'audio_language':'English','original_clip_audio_included':False,'music_added':False,
 'audio_input':'Original expressive YANA_04_My_Tieng_Anh.mp3, unchanged pitch and timing; loudness processing only','narration_style_id':'science-documentary-expressive-v1',
 'reference_voice_duration_seconds':len(reference)/8000,'reference_voice_sha256':hashlib.sha256(Path('/workspace/work/yana/verified-release/YANA_04_My_Tieng_Anh.mp3').read_bytes()).hexdigest(),'decoded_final_audio_seconds':len(actual)/8000,
 'waveform_alignment_checks':comparisons,'measured_loudness_lufs':float(loudness['input_i']),
 'measured_true_peak_dbtp':float(loudness['input_tp']),'measured_loudness_range_lu':float(loudness['input_lra']),
 'chapter_count':12,'subtitle_cues':138,'subtitle_mode':'Embedded optional English subtitles and separate SRT',
 'timeline_cues':138,'planned_shots':sum(len(p['segments']) for p in plan),'opening_30s_shots':12,
 'short_dissolves':sum(p['transition']=='dissolve' for p in plan),
 'source_uploads':len(downloads),'downloaded_uploads':len([d for d in downloads if 'path' in d]),
 'unique_downloaded_clips':len(inventory),'unique_source_clips_used':len({s['label'] for p in plan for s in p['segments'] if not s['label'].startswith('@')}),'science_graphic_count':len(list((ROOT/'graphics').glob('*.png'))),'exact_duplicate_files_removed':len([d for d in downloads if 'path' in d])-len(inventory),
 'source_transfer_limits':[d for d in downloads if 'error' in d], 'no_children_in_final_selected_scenes':True, 'manual_visual_scope':'Sampling and scene selection, not continuous viewing.',
 'source_note':'All133 uploads transferred;18 exact duplicates identified;115 unique sources inspected. Five missing prompt contexts covered by appropriate alternatives and explanatory graphics.',
 'science_graphics':'Natural Earth 1:110m modern coastlines/lakes, whole polygon rings preserved across the dateline; original NPS bathymetry context labels about 21,000 BP retained. Genetics graphics are explanatory schematics, not measured data, exact migration routes or universal ancestry proportions.',
 'full_decode_exit_code':0,'black_gaps_detected':black,'decode_errors_detected':errors,
 'visual_review':'All115 unique sources inspected using contact sheets;13 adult-group sources sampled at three times. Opening, graphics, chapters and ending sampled from rendered frames. No claim of continuous manual review of all23minutes.',
 'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'bytes':video.stat().st_size,
 'voices':'Existing separate-language voice assets are retained in release yana-video-04-23min. Only the existing English reference is included in this video.'
}
(OUT/'FINAL_VIDEO_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'status':'passed','seconds':result['video_duration_seconds'],'bytes':result['bytes'],'lufs':result['measured_loudness_lufs'],'true_peak':result['measured_true_peak_dbtp'],'alignment_checks':len(comparisons),'sha256':result['sha256']}),flush=True)
