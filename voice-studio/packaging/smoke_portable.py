"""Run with the relocated packaged interpreter, offline model flags enabled."""
import json
from pathlib import Path
import subprocess
import sys

app = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(app))
import numpy as np
import soundfile as sf
import httpx
from fastapi.testclient import TestClient
import app as studio
from worker import render

assert Path(sys.executable).parent.name == 'runtime', 'Must validate relocated bundled Python'
assert Path(sys.prefix).resolve() == Path(sys.executable).resolve().parent
for module in (np, sf, httpx):
    assert Path(sys.prefix).resolve() in Path(module.__file__).resolve().parents, 'Dependency resolved outside bundled runtime'
subprocess.run(['ffmpeg','-version'], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['ffprobe','-version'], check=True, stdout=subprocess.DEVNULL)
with TestClient(studio.app) as client:
    config=client.get('/api/config').json()
    assert config['nano_ready'] and len(config['subtitle_languages'])==52
    assert 'hi' in config['subtitle_languages']
    assert len([v for v in client.get('/api/voices').json()['voices'] if v['engine']=='qwen'])==9
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/static/studio-tools.js').status_code==200
    assert client.get('/static/video-preview.js').status_code==200
    assert client.get('/static/workspace.js').status_code==200
    assert 'workspace-all' in client.get('/').text
    assert any('ko' in v['languages'] for v in client.get('/api/voices').json()['voices'])
for engine, speaker in [('vieneu_nano','Minh Quân'), ('vieneu','Mai Anh')]:
    job = {'id': 'portable-check-'+engine, 'text': 'Xin chào, đây là kiểm tra gói phòng thu giọng nói.', 'engine': engine, 'speaker': speaker, 'voice_id': 'check', 'language': 'vi', 'quality': 'standard', 'format': 'wav', 'speed': 1, 'nano_steps': 8, 'nano_threads': 2, 'paragraph_pause': 0}
    render(job)
    audio = app/'.data/audio'/(job['id']+'.wav')
    samples, rate = sf.read(audio)
    assert len(samples)>rate and np.max(np.abs(samples))>.001
# Verify real speech fits the original subtitle windows in the relocated runtime.
aligned = dict(job, id='portable-check-aligned', engine='vieneu_nano', speaker='Minh Quân', input_format='srt', cue_fit='strict', max_cue_tempo=2, text='1\n00:00:01,000 --> 00:00:06,000\nXin chào.\n\n2\n00:00:08,000 --> 00:00:14,000\nCảm ơn.\n')
render(aligned)
report=json.loads((app/'.data/parts/portable-check-aligned/alignment.json').read_text(encoding='utf-8'))
assert report['sync_ok'] and len(report['cues'])==2
assert [row['start'] for row in report['cues']]==[1,8]
# Download formats must work with bundled FFmpeg and interpreter.
import uuid
export_id=uuid.uuid4().hex
for suffix in ('wav','srt'):
    import shutil
    shutil.copy2(app/'.data/audio'/('portable-check-aligned.'+suffix),app/'.data/audio'/(export_id+'.'+suffix))
(app/'.data/jobs'/(export_id+'.json')).write_text(json.dumps({'id':export_id,'status':'done','format':'wav'}),encoding='utf-8')
with TestClient(studio.app) as client:
    for extension in ('mp3','wav','txt','srt'):
        response=client.get(f'/api/jobs/{export_id}/export.{extension}')
        assert response.status_code==200 and len(response.content)>10
# Also exercise MP4 muxing from the bundled FFmpeg, preserving video.
from dubbing import inspect_video, mux_video
videos = app/'.data/videos'
videos.mkdir(exist_ok=True)
source = videos/'portable.source'
subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=blue:s=160x90:r=10:d=20','-c:v','libx264','-y','-f','mp4',str(source)], check=True)
(videos/'portable.json').write_text(json.dumps(inspect_video(source)), encoding='utf-8')
job = {'id': 'portable-check-vieneu_nano', 'video_id': 'portable','caption_cues':[{'start':0,'end':5,'text':'Video có phụ đề và voice'}],'logos':[{'x':10,'y':10,'w':20,'h':12,'mode':'color','color':'#ff0000'},{'x':80,'y':10,'w':20,'h':12,'mode':'color','color':'#00ff00'}]}
mux_video(job, app/'.data/audio'/(job['id']+'.wav'), app/'.data/parts'/job['id'], app/'.data', sf.info(app/'.data/audio'/(job['id']+'.wav')).duration)
assert inspect_video(app/'.data/audio'/(job['id']+'.mp4'))['has_audio']
# Exercise bundled speech recognition offline and a real logo filter.
from faster_whisper import WhisperModel
recognizer = WhisperModel(str(app/'.data/models/whisper-base'),device='cpu',compute_type='int8',cpu_threads=2)
segments, info = recognizer.transcribe(str(app/'.data/audio/portable-check-vieneu.wav'),language='vi',beam_size=1,vad_filter=True)
assert any(segment.text.strip() for segment in segments), 'Offline subtitle recognition returned no text'
from video_tasks import run
work=app/'.data/video_tasks/portable'
work.mkdir(parents=True)
path=work/'job.json'
path.write_text(json.dumps({'video_id':'portable','action':'render','cues':[{'start':0,'end':5,'text':'Phụ đề đã sửa trực tiếp'}],'logo':{'x':10,'y':10,'w':30,'h':20}}),encoding='utf-8')
run(path)
assert inspect_video(work/'output.mp4')['duration'] > 19
# A short proof must use the same styled captions, logo treatment and bundled voice audio.
path.write_text(json.dumps({'video_id':'portable','action':'preview','preview_start':1,'preview_seconds':2,'preview_voice_id':'portable-check-vieneu_nano','cues':[{'start':1,'end':3,'text':'Xem thử trước khi xuất'}],'caption_style':{'color':'#ffff00','bold':True,'position':'top'},'logos':[{'x':10,'y':10,'w':20,'h':12,'mode':'color','color':'#ff0000'}]}),encoding='utf-8')
run(path)
proof=inspect_video(work/'output.mp4')
assert proof['has_audio'] and abs(proof['duration']-2)<.2
# Compose a complete video with the ready WAV without synthesizing it again.
path.write_text(json.dumps({'video_id':'portable','action':'render','voice_job_id':'portable-check-vieneu_nano','cues':[{'start':0,'end':5,'text':'Workspace đã tạo voice'}]}),encoding='utf-8')
run(path)
assert inspect_video(work/'output.mp4')['has_audio']
# Verify actual UHD output with the relocated interpreter and bundled FFmpeg.
short=videos/'portable-4k.source'
subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=blue:s=160x90:r=5:d=0.4','-c:v','libx264','-f','mp4','-y',str(short)],check=True)
(videos/'portable-4k.json').write_text(json.dumps(inspect_video(short)),encoding='utf-8')
path.write_text(json.dumps({'video_id':'portable-4k','action':'export','export_resolution':'2160p','export_quality':'best'}),encoding='utf-8')
run(path)
meta=inspect_video(work/'output.mp4')
assert (meta['width'],meta['height'])==(3840,2160)
# Remove QA projects; retain model weights and ready markers only.
import shutil
for name in ('audio','parts','jobs','voices','videos','video_tasks'):
    shutil.rmtree(app/'.data'/name)
    (app/'.data'/name).mkdir()
print('PASS: packaged Windows Python, dependencies, offline Nano+Turbo, web API/static assets, FFmpeg and MP4 export.')
