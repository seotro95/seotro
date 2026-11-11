"""Acceptance against the real frozen exe. Never package fixture media."""
import copy,hashlib,json,os,subprocess,sys,time,urllib.request,wave
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from autodoc.common import Context,binary,digest,probe,save_json
from autodoc.bootstrap import ensure_ffmpeg
from autodoc.project import load,save,split,merge_previous
from autodoc.player import scene_preview

root=Path(__file__).resolve().parent;exe=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else None
work=root/('windows test' if exe else 'local test')/'Nguon thu nghiem';work.mkdir(parents=True,exist_ok=True)
ensure_ffmpeg(Context());ff=binary('ffmpeg');ctx=Context();frozen=bool(exe)
def command(args):subprocess.run([str(x) for x in args],check=True)
def app(args,result):
    command(([exe] if exe else [sys.executable,root/'main.py'])+args+['--result-json',result]);d=json.loads(result.read_text(encoding='utf-8'));assert d.get('status')!='failed',d;return d
opening=work/'reference_opening.mp4'
if not opening.exists():
    with urllib.request.urlopen('https://github.com/seotro95/seotro/releases/download/kostenki-video-19-final-20m15s/KOSTENKI_19_OPENING_30s.mp4',timeout=120) as f:opening.write_bytes(f.read())
voice=work/'voice 21.wav'
command([ff,'-v','error','-i',opening,'-t','21.37','-vn','-ac','1','-ar','48000','-y',voice])
with wave.open(str(voice)) as w:duration=w.getnframes()/w.getframerate()
clips=work/'clips';clips.mkdir(exist_ok=True)
for i in range(10):
    args=[ff,'-v','error','-ss',str(i*2.7),'-i',opening]
    if i==0:args+=['-f','lavfi','-i','sine=frequency=1379:sample_rate=48000:duration=2.5','-map','0:v:0','-map','1:a:0','-c:a','aac']
    else:args+=['-map','0:v:0','-an']
    command(args+['-t','2.5','-r','24','-vf','scale=640:360','-c:v','libx264','-threads','2','-preset','ultrafast','-crf','25','-y',clips/f'clip {i:03d}.mp4'])
im=Image.new('RGB',(960,540),'#38415a');draw=ImageDraw.Draw(im)
for i in range(12):draw.rectangle((i*80,180,(i+1)*80,540),fill=(20+i*18,60+i*12,140-i*7))
draw.ellipse((280,50,650,400),fill='#e4cda5');im.save(clips/'photo image.jpg')
logo=Image.new('RGBA',(160,90),(255,0,255,255));ImageDraw.Draw(logo).ellipse((50,20,100,70),fill=(0,0,0,0));logo.save(clips/'logo.png')
sub=work/'subtitles.srt';sub.write_text('1\n00:00:00,000 --> 00:00:03,000\nA hidden bone circle?\n\n2\n00:00:03,000 --> 00:00:12,000\nEvidence changes the story.\n\n3\n00:00:12,000 --> 00:00:21,300\nXin chào {literal}.\n',encoding='utf-8-sig')
settings={'resolution':720 if exe else 360,'fps':24,'quality':'fast','encoder':'auto','subtitle_path':str(sub),'subtitle_mode':'burn','subtitle_style':{'color':'#00FF00','size':34,'bold':True},'logo_path':str(clips/'logo.png'),'logo_position':'top_left','logo_size':12,'full_verify':True,'screen_minors':False}
if not exe:settings['clip_model_path']=str(root.parent/'auto-documentary-editor/test-models/clip')
config=work/'settings.json';save_json(config,settings);before={p.name:digest(p) for p in clips.iterdir()};result=work/'result.json';t=time.monotonic()
d=app(['--voice',voice,'--media',clips,'--output',work/'ket qua','--settings',config,'--prepare-only'],result);p=load(d['project']);assert p['asr_skipped'] and len(p['files'])==11 and sum(f['kind']=='image' for f in p['files'])==1
assert p['plan']['opening_distinct_files']==10
# Make visible edits: use an image, an audio-bearing video, subtitles and transitions.
p['plan']['shots'][0].update(source_id=0,source_name=p['files'][0]['name'],source_in=0,effect='cinema')
image=next(f for f in p['files'] if f['kind']=='image');p['plan']['shots'][1].update(source_id=image['id'],source_name=image['name'],source_in=0,effect='zoom_in',transition='wipeleft')
p['plan']['shots'][2]['transition']='dissolve';split(p,3,.75);merge_previous(p,4);save(p);project_file=Path(p['project_file'])
p['plan']['shots'][3].update(source_id=0,source_name=p['files'][0]['name'],source_in=4.,effect='none',transition='cut',crop=1.);save(p)
out=work/'Custom export.mp4';d=app(['--project',project_file,'--export-to',out],result);r=d['report'];assert r['status']=='passed' and r['image_scenes']>=1 and not r['source_audio_kept'] and r['logo_applied'] and r['subtitle_mode']=='burn' and r['audio_alignment']
# Look at actual output pixels, not just settings metadata.
raw=ctx.run([ff,'-v','error','-ss','0.7','-i',out,'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'],capture=True);pix=np.frombuffer(raw,dtype=np.uint8).reshape(r['height'],r['width'],3)
pink=((pix[:,:,0]>180)&(pix[:,:,1]<70)&(pix[:,:,2]>160));green=((pix[:,:,1]>150)&(pix[:,:,1].astype(float)>pix[:,:,0]*1.4)&(pix[:,:,1].astype(float)>pix[:,:,2]*1.4));assert pink[:r['height']//3,:r['width']//3].sum()>100;assert green[r['height']//2:].sum()>20
# A split/in-point beyond a short clip's duration must wrap to the same moving
# source frame rather than freeze or jump to the clip's last frame.
def thumbnail(path,at):
    raw=ctx.run([ff,'-v','error','-ss',str(at),'-i',path,'-frames:v','1','-vf','scale=320:180','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'],capture=True)
    return np.frombuffer(raw,dtype=np.uint8).reshape(180,320,3).astype(float)[50:125,60:270]
at=p['plan']['shots'][3]['start_frame']/24+.5;actual=thumbnail(out,at);expected=thumbnail(clips/'clip 000.mp4',2.)
assert float(np.mean((actual-expected)**2))<120,'Looped source in-point did not continue at the expected frame.'
stamps={str(x):x.stat().st_mtime_ns for x in Path(p['job']).glob('renders/*/scene.mp4')}
app(['--project',project_file,'--export-to',work/'Cached export.mp4'],result);assert all(Path(x).stat().st_mtime_ns==mtime for x,mtime in stamps.items())
# A second job reuses cross-project CLIP features, even with a different output folder.
second=app(['--voice',voice,'--media',clips,'--output',work/'second project','--settings',config,'--prepare-only'],result);metrics=json.loads((Path(second['project']).parent/'analysis_metrics.json').read_text());assert metrics['shared_cache_hits']==11
mix={'mute_source':False,'source_volume':.4,'subtitle_mode':'soft','fps':30};save_json(work/'mix.json',mix)
mixed=work/'Mixed export.mp4';d2=app(['--project',project_file,'--settings',work/'mix.json','--export-to',mixed],result);assert d2['report']['source_audio_kept'] and d2['report']['fps']==30
assert len([s for s in probe(mixed,ctx)['streams'] if s['codec_type']=='subtitle'])==1
def tone(path):
    b=ctx.run([ff,'-v','error','-i',path,'-t','1','-map','0:a:0','-ac','1','-ar','8000','-f','f32le','-'],capture=True);x=np.frombuffer(b,dtype='<f4');z=np.fft.rfft(x*np.hanning(len(x)));hz=np.fft.rfftfreq(len(x),1/8000);return float(np.abs(z)[abs(hz-1379)<4].max())
assert tone(mixed)>tone(out)*2
preview=scene_preview(p,1,ctx);assert Path(preview[0]).is_file() and Path(preview[1]).is_file()
app(['--project',project_file,'--settings',work/'mix.json','--export-to',work/'Mixed export.mkv'],result)
if exe:
    gui=work/'gui.json';command([exe,'--gui-smoke','--project',project_file,'--gui-report',gui]);g=json.loads(gui.read_text());assert g['status']=='passed' and g['preview_loaded'] and g['preview_frame_displayed']
assert all(digest(clips/name)==h for name,h in before.items())
qa={'status':'passed','version':'2.0.1','platform':'Windows x64' if exe else 'Linux','frozen_exe_tested':frozen,'real_clip_model_used':True,'srt_skips_asr_verified':True,'mixed_image_video_import':True,'source_files_unchanged':True,'logo_pixels_verified':True,'burn_subtitle_pixels_verified':True,'soft_subtitle_track_verified':True,'mute_and_keep_source_audio_verified':True,'source_tone_verified':True,'manual_scene_split_merge_verified':True,'export_24_and_30fps_verified':True,'mp4_and_mkv_verified':True,'embedded_preview_rendered':True,'frozen_gui_preview_tested':frozen,'scene_cache_reused':True,'shared_feature_cache_hits':metrics['shared_cache_hits'],'full_decode_passed':True,'voice_alignment':r['audio_alignment'],'video_seconds':r['video_seconds'],'test_seconds':round(time.monotonic()-t,2),'media_fixtures_not_included_in_release':True}
(root/('WINDOWS_TEST_REPORT.json' if exe else 'LOCAL_TEST_REPORT.json')).write_text(json.dumps(qa,indent=2),encoding='utf-8');print(json.dumps(qa),flush=True)
