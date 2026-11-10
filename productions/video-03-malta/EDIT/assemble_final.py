import csv,json,shutil,subprocess
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery'
voice=R.parent/'voice/verified-en/MALTA_03_My_Tieng_Anh.mp3'
rows=list(csv.DictReader(open(R.parent/'package/CHAPTERS_12.csv')))
checks=[]
for i in range(1,121):
 p=R/'scenes'/f'{i:03d}.mp4'
 j=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
 v=[s for s in j['streams'] if s['codec_type']=='video'];a=[s for s in j['streams'] if s['codec_type']=='audio']
 assert len(v)==1 and not a,(i,'Unexpected audio or missing video')
 assert int(v[0]['nb_frames'])==240 and abs(float(j['format']['duration'])-10)<1/24
 checks.append({'cue':i,'frames':240,'seconds':10,'audio_streams':0})
(R/'SCENE_VERIFICATION.json').write_text(json.dumps(checks,indent=2))
shutil.copy(R.parent/'country-final-details/TIMING/en-US.srt',O/'MALTA_03_EN_SUBTITLES.srt')
meta=';FFMETADATA1\ntitle=A 24,000-Year-Old Child Changed America\'s Ancestry Story\nartist=Malta Science Documentary\ncomment=Illustrative reconstructions and explanatory diagrams. Source clip audio removed. English narration only.\n'
for row in rows:meta+=f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(row['start_seconds'])*1000}\nEND={int(row['end_seconds'])*1000}\ntitle={row['title_en']}\n"
(R/'chapters.ffmetadata').write_text(meta)
measurement=(R/'loudness_measurement.log').read_text();m=json.loads(measurement[measurement.rfind('{'):measurement.rfind('}')+1])
af=(f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json,aresample=48000,atrim=duration=1200,asetpts=PTS-STARTPTS")
# Concat silent scene outputs and map the existing English reference as the ONLY audio input.
cmd=['ffmpeg','-hide_banner','-nostats','-y','-f','concat','-safe','0','-i',str(R/'concat.txt'),'-i',str(voice),'-i',str(O/'MALTA_03_EN_SUBTITLES.srt'),'-i',str(R/'chapters.ffmetadata'),'-map','0:v:0','-map','1:a:0','-map','2:0','-map_metadata','3','-map_chapters','3','-c:v','copy','-af',af,'-c:a','aac','-b:a','160k','-ar','48000','-c:s','mov_text','-metadata:s:a:0','language=eng','-metadata:s:a:0','title=English narration','-metadata:s:s:0','language=eng','-metadata:s:s:0','title=Optional English subtitles','-disposition:s:0','0','-t','1200','-movflags','+faststart',str(O/'MALTA_03_EN_FINAL_20m_720p.mp4')]
(R/'FINAL_EXPORT_COMMAND.json').write_text(json.dumps(cmd,indent=2))
with (R/'final_export.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run(['ffmpeg','-v','warning','-y','-i',str(O/'MALTA_03_EN_FINAL_20m_720p.mp4'),'-t','30','-map','0:v:0','-map','0:a:0','-c','copy','-map_chapters','-1','-movflags','+faststart',str(O/'MALTA_03_OPENING_30s.mp4')],check=True)
print('20-minute master and 30-second opening exported',flush=True)
