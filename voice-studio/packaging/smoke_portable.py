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
    assert client.get('/api/config').json()['nano_ready']
    assert client.get('/static/app.js').status_code == 200
for engine, speaker in [('vieneu_nano','Minh Quân'), ('vieneu','Mai Anh')]:
    job = {'id': 'portable-check-'+engine, 'text': 'Xin chào, đây là kiểm tra gói phòng thu giọng nói.', 'engine': engine, 'speaker': speaker, 'voice_id': 'check', 'language': 'vi', 'quality': 'standard', 'format': 'wav', 'speed': 1, 'nano_steps': 8, 'nano_threads': 2, 'paragraph_pause': 0}
    render(job)
    audio = app/'.data/audio'/(job['id']+'.wav')
    samples, rate = sf.read(audio)
    assert len(samples)>rate and np.max(np.abs(samples))>.001
# Also exercise MP4 muxing from the bundled FFmpeg, preserving video.
from dubbing import inspect_video, mux_video
videos = app/'.data/videos'
videos.mkdir(exist_ok=True)
source = videos/'portable.source'
subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=blue:s=160x90:r=10:d=20','-c:v','libx264','-y','-f','mp4',str(source)], check=True)
(videos/'portable.json').write_text(json.dumps(inspect_video(source)), encoding='utf-8')
job = {'id': 'portable-check-vieneu_nano', 'video_id': 'portable'}
mux_video(job, app/'.data/audio'/(job['id']+'.wav'), app/'.data/parts'/job['id'], app/'.data', sf.info(app/'.data/audio'/(job['id']+'.wav')).duration)
assert inspect_video(app/'.data/audio'/(job['id']+'.mp4'))['has_audio']
# Remove QA projects; retain model weights and ready markers only.
import shutil
for name in ('audio','parts','jobs','voices','videos'):
    shutil.rmtree(app/'.data'/name)
    (app/'.data'/name).mkdir()
print('PASS: packaged Windows Python, dependencies, offline Nano+Turbo, web API/static assets, FFmpeg and MP4 export.')
