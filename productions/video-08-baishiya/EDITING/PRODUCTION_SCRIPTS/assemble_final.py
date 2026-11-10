import csv,json,shutil,subprocess
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery'
voice=R/'input/BAISHIYA_08_My_Tieng_Anh.mp3'
rows=list(csv.DictReader(open(R/'input/CHAPTERS_12.csv')))
checks=[]
for i in range(1,135):
 p=R/'scenes'/f'{i:03d}.mp4'
 j=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
 v=[s for s in j['streams'] if s['codec_type']=='video'];a=[s for s in j['streams'] if s['codec_type']=='audio']
 assert len(v)==1 and not a,(i,'Unexpected audio or missing video')
 assert int(v[0]['nb_frames'])==240 and abs(float(j['format']['duration'])-10)<1/24
 checks.append({'cue':i,'frames':240,'seconds':10,'audio_streams':0})
(R/'SCENE_VERIFICATION.json').write_text(json.dumps(checks,indent=2))
shutil.copy(R/'input/en-US.srt',O/'BAISHIYA_08_EN_SUBTITLES.srt')
meta=';FFMETADATA1\ntitle=Baishiya: The Survival Story Hidden in Broken Bones\nartist=Baishiya Science Documentary\ncomment=Illustrative reconstructions and explanatory diagrams. Source clip audio removed. English narration only.\n'
for row in rows:meta+=f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(row['start_seconds'])*1000}\nEND={int(row['end_seconds'])*1000}\ntitle={row['title_en']}\n"
(R/'chapters.ffmetadata').write_text(meta)
with (R/'loudness_measurement.log').open('w') as f:subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(voice),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],stdout=f,stderr=subprocess.STDOUT,check=True)
measurement=(R/'loudness_measurement.log').read_text();m=json.loads(measurement[measurement.rfind('{'):measurement.rfind('}')+1])
af=(f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json,aresample=48000,atrim=duration=1340,asetpts=PTS-STARTPTS")
# Concat silent scene outputs and map the existing English reference as the ONLY audio input.
cmd=['ffmpeg','-hide_banner','-nostats','-y','-f','concat','-safe','0','-i',str(R/'concat.txt'),'-i',str(voice),'-i',str(O/'BAISHIYA_08_EN_SUBTITLES.srt'),'-i',str(R/'chapters.ffmetadata'),'-map','0:v:0','-map','1:a:0','-map','2:0','-map_metadata','3','-map_chapters','3','-c:v','copy','-af',af,'-c:a','aac','-b:a','160k','-ar','48000','-c:s','mov_text','-metadata:s:a:0','language=eng','-metadata:s:a:0','title=English narration','-metadata:s:s:0','language=eng','-metadata:s:s:0','title=Optional English subtitles','-disposition:s:0','0','-t','1340','-movflags','+faststart',str(O/'BAISHIYA_08_EN_FINAL_22m20s_720p.mp4')]
(R/'FINAL_EXPORT_COMMAND.json').write_text(json.dumps(cmd,indent=2))
# Only regenerable rendered intermediates are removed after their timestamps have
# been muxed, retaining a sixty-second safety window. All uploaded sources remain intact.
cleanup=[]
with (R/'final_export.log').open('w') as f:
 progress_cmd=cmd[:1]+['-progress','pipe:1','-stats_period','0.5']+cmd[1:]
 proc=subprocess.Popen(progress_cmd,stdout=subprocess.PIPE,stderr=f,text=True)
 for line in proc.stdout:
  if not line.startswith('out_time_us='):continue
  try:second=int(line.split('=',1)[1])/1000000
  except ValueError:continue
  for n in range(1,135):
   candidate=R/'scenes'/f'{n:03d}.mp4'
   if n*10+60<second and candidate.exists():
    assert candidate.resolve().parent==(R/'scenes').resolve()
    candidate.unlink();cleanup.append(n)
 assert proc.wait()==0,'Final mux failed; original sources and unconsumed intermediates retained.'
final=O/'BAISHIYA_08_EN_FINAL_22m20s_720p.mp4'
verification=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(final)]))
assert int(next(s for s in verification['streams'] if s['codec_type']=='video')['nb_frames'])==32160
for n in range(1,135):
 candidate=R/'scenes'/f'{n:03d}.mp4'
 if candidate.exists():candidate.unlink();cleanup.append(n)
(R/'RENDER_INTERMEDIATE_CLEANUP.json').write_text(json.dumps({'regenerable_scene_numbers':cleanup,'original_source_media_removed':False,'safety_window_seconds':60},indent=2))
subprocess.run(['ffmpeg','-v','warning','-y','-i',str(O/'BAISHIYA_08_EN_FINAL_22m20s_720p.mp4'),'-t','30','-map','0:v:0','-map','0:a:0','-c','copy','-map_chapters','-1','-movflags','+faststart',str(O/'BAISHIYA_08_OPENING_30s.mp4')],check=True)
print('22-minute-20-second master and 30-second opening exported',flush=True)
