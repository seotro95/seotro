import csv,hashlib,json,subprocess,shutil
from pathlib import Path
R=Path(__file__).parent;O=R/'delivery';O.mkdir(exist_ok=True)
plan=json.loads((R/'EDIT_PLAN.json').read_text());checks=[]
for item in plan:
 p=R/'scenes'/f"{item['cue']:03d}.mp4";j=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(p)]))
 assert not any(s['codec_type']=='audio' for s in j['streams'])
 v=next(s for s in j['streams'] if s['codec_type']=='video');assert int(v['nb_frames'])==round(item['duration']*24),(item['cue'],v['nb_frames'])
 checks.append({'cue':item['cue'],'frames':int(v['nb_frames']),'audio_streams':0})
(R/'SCENE_VERIFICATION.json').write_text(json.dumps(checks,indent=2))
voice=R/'input/KOSTENKI_19_My_Tieng_Anh.mp3'
assert hashlib.file_digest(voice.open('rb'),'sha256').hexdigest()=='84efbd7b1f7fa1a08940d793d9fdac88a645ee8267643280ba7240a781f16c5a'
shutil.copyfile(R/'input/en-US.srt',O/'KOSTENKI_19_EN_SUBTITLES.srt')
meta=';FFMETADATA1\ntitle=Kostenki: The House That Remains a Question\ncomment=Original illustrative visuals and modern teaching models. English narration only. All clip audio removed.\n'
for row in csv.DictReader((R/'input/CHAPTERS_12.csv').open(encoding='utf-8-sig')):meta+=f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(row['start_seconds'])*1000}\nEND={int(row['end_seconds'])*1000}\ntitle={row['title_en']}\n"
(R/'chapters.ffmetadata').write_text(meta)
raw=(R/'loudness_measurement.log').read_text();m=json.loads(raw[raw.rfind('{'):raw.rfind('}')+1])
af=f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000,atrim=duration=1215,asetpts=PTS-STARTPTS"
cmd=['ffmpeg','-hide_banner','-nostats','-y','-f','concat','-safe','0','-i',str(R/'concat.txt'),'-i',str(voice),'-i',str(O/'KOSTENKI_19_EN_SUBTITLES.srt'),'-i',str(R/'chapters.ffmetadata'),'-map','0:v:0','-map','1:a:0','-map','2:0','-map_metadata','3','-map_chapters','3','-c:v','copy','-af',af,'-c:a','aac','-b:a','160k','-ar','48000','-c:s','mov_text','-metadata:s:a:0','language=eng','-metadata:s:a:0','title=English narration only','-metadata:s:s:0','language=eng','-metadata:s:s:0','title=Optional English subtitles','-disposition:s:0','0','-t','1215','-movflags','+faststart',str(O/'KOSTENKI_19_EN_FINAL_20m15s_720p.mp4')]
(R/'FINAL_EXPORT_COMMAND.json').write_text(json.dumps(cmd,indent=2))
with (R/'final_export.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
(R/'opening_concat.txt').write_text(''.join(f"file '{(R/'scenes'/f'{i:03d}.mp4').as_posix()}'\n" for i in range(1,4)))
opening=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(R/'opening_concat.txt'),'-i',str(voice),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',af,'-c:a','aac','-b:a','160k','-ar','48000','-t','30','-map_chapters','-1','-movflags','+faststart',str(O/'KOSTENKI_19_OPENING_30s.mp4')]
subprocess.run(opening,check=True)
print('Exported1215seconds mainEnglish and30second10shot opening',flush=True)
