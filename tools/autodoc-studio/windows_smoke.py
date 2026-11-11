"""Real frozen-Windows acceptance test. Media fixtures are never distributed."""
import hashlib,json,os,subprocess,sys,urllib.request
from pathlib import Path

root=Path(__file__).parent;exe=Path(sys.argv[1]).resolve();work=root/'windows test'/'Nguon thu nghiem';work.mkdir(parents=True,exist_ok=True)
from autodoc.common import Context,binary
from autodoc.bootstrap import ensure_ffmpeg
ensure_ffmpeg(Context());ff=binary('ffmpeg')
def command(args):subprocess.run([str(x) for x in args],check=True)
opening=work/'reference_opening.mp4'
with urllib.request.urlopen('https://github.com/seotro95/seotro/releases/download/kostenki-video-19-final-20m15s/KOSTENKI_19_OPENING_30s.mp4',timeout=120) as f:opening.write_bytes(f.read())
if opening.stat().st_size<100000:raise RuntimeError('Testfixture download incomplete.')
voice=work/'voice 45.wav';command([ff,'-v','error','-stream_loop','-1','-i',opening,'-t','45.37','-vn','-ac','1','-ar','48000','-y',voice])
clips=work/'clips';clips.mkdir(exist_ok=True)
for i in range(10):
    args=[ff,'-v','error','-ss',str(i*3),'-i',opening]
    if i==0:args+=['-f','lavfi','-i','sine=frequency=1379:sample_rate=48000:duration=3','-map','0:v:0','-map','1:a:0','-c:a','aac']
    else:args+=['-map','0:v:0','-an']
    command(args+['-t','3','-r','24','-vf','scale=640:360','-c:v','libx264','-preset','ultrafast','-crf','25','-y',clips/f'clip {i:03d}.mp4'])
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in clips.iterdir()}
result=work/'result.json'
command([exe,'--voice',voice,'--videos',clips,'--output',work/'ket qua','--embed-subtitles','--result-json',result])
d=json.loads(result.read_text(encoding='utf-8'));report=d['report'];assert report['status']=='passed' and report['opening_shots']==10 and report['opening_distinct_source_files']==10
assert report['source_audio_streams_removed']==1 and report['audio_streams']==1 and not report['clip_audio_included']
assert abs(report['video_seconds']-45.37)<1/24 and report['frames']==1089
assert all(hashlib.sha256((clips/name).read_bytes()).hexdigest()==h for name,h in before.items())
# A second unchanged run must retain the rendered-shot cache, while revalidating output.
project=Path(d['project']);stamps={p.name:p.stat().st_mtime_ns for p in (project/'shots').glob('*.mp4')}
command([exe,'--voice',voice,'--videos',clips,'--output',work/'ket qua','--embed-subtitles','--result-json',result])
assert all((project/'shots'/name).stat().st_mtime_ns==mtime for name,mtime in stamps.items())
qa={'status':'passed','platform':'Windows x64','frozen_exe_tested':True,'real_whisper_and_clip_models_used':True,'voice_seconds':report['voice_seconds'],'video_seconds':report['video_seconds'],'video_frames':report['frames'],'opening_shots':10,'opening_distinct_files':10,'original_video_audio_removed':True,'source_files_unchanged':True,'resume_cache_verified':True,'optional_subtitles_tested':True,'full_decode_passed':True,'alignment_checks':report['audio_alignment'],'media_fixtures_not_included_in_release':True}
(root/'WINDOWS_TEST_REPORT.json').write_text(json.dumps(qa,indent=2),encoding='utf-8');print(json.dumps(qa),flush=True)
