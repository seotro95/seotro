"""Variant routing tests; actual inference is exercised by portable smoke."""
import os
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]

def run_case(tmp_path, code):
    env = dict(os.environ, VOICE_STUDIO_VARIANT='hmong', VOICE_STUDIO_DATA_DIR=str(tmp_path))
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, text=True, capture_output=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr

def test_hmong_config_cannot_fall_back_to_vietnamese(tmp_path):
    run_case(tmp_path, '''
from unittest.mock import patch
from fastapi.testclient import TestClient
import app
with TestClient(app.app) as c, patch.object(app,'model_ready',lambda engine:engine=='f5_hmong'), patch.object(app.executor,'submit'):
    cfg=c.get('/api/config').json()
    assert cfg['variant']=='hmong' and cfg['default_language']=='mww'
    assert cfg['languages']=={'mww':'Hmong Trắng · Hmoob Daw'}
    assert 'mww' not in cfg['recognition_languages']
    voices=c.get('/api/voices').json()['voices']
    assert {v['id'] for v in voices}=={'hmong-female','hmong-male'}
    assert all(v['engine']=='f5_hmong' and v['native_language']=='mww' for v in voices)
    response=c.post('/api/speech',json={'text':'Nyob zoo.','voice_id':'hmong-female','hmong_steps':8,'delivery':'review'})
    assert response.status_code==202,response.text
    assert response.json()['engine']=='f5_hmong' and response.json()['language']=='mww'
    assert c.post('/api/speech',json={'text':'Xin chào.','voice_id':'hmong-female','language':'vi'}).status_code==422
    assert c.post('/api/speech',json={'text':'Nyob zoo.','voice_id':'hmong-female','hmong_steps':12}).status_code==422
    assert c.get('/api/hmong/presets/hmong-female/sample').status_code==200
''')

def test_hmong_clone_requires_words_and_bounded_reference(tmp_path):
    run_case(tmp_path, '''
from fastapi.testclient import TestClient
from hmong_assets import reference
import app,io,wave
ref,text=reference('hmong-male')
with TestClient(app.app) as c:
    data={'name':'Kuv lub suab','language':'mww','consent':'true'}
    assert c.post('/api/voices/clone',data=data,files={'file':('sample.wav',ref.read_bytes())}).status_code==422
    data['transcript']=text
    response=c.post('/api/voices/clone',data=data,files={'file':('sample.wav',ref.read_bytes())})
    assert response.status_code==201,response.text
    assert response.json()['engine']=='f5_hmong' and response.json()['transcript']==text
    buf=io.BytesIO()
    with wave.open(buf,'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000);audio.writeframes(b'\\x00\\x20'*24000*9)
    assert c.post('/api/voices/clone',data=data,files={'file':('long.wav',buf.getvalue())}).status_code==422
''')

def test_manual_hmong_captions_are_independent_from_asr(tmp_path):
    run_case(tmp_path, '''
from unittest.mock import patch
from fastapi.testclient import TestClient
import app,json
ident='a'*32
(app.DATA/'videos'/(ident+'.json')).write_text(json.dumps({'duration':10,'width':320,'height':240}))
with TestClient(app.app) as c,patch.object(app.executor,'submit'):
    response=c.put('/api/videos/'+ident+'/editor',json={'language':'mww','cues':[{'start':0,'end':2,'text':'Nyob zoo.'}]})
    assert response.status_code==200,response.text
    assert 'Nyob zoo.' in c.get('/api/videos/'+ident+'/editor/export.srt').text
    response=c.post('/api/video-tasks',json={'action':'subtitles','video_id':ident,'source_language':'mww'})
    assert response.status_code==422 and 'Hmong' in response.text,response.text
    response=c.post('/api/video-tasks',json={'action':'translate_text','text':'Nyob zoo.','source_language':'mww','target_language':'vi'})
    assert response.status_code==202,response.text
''')


def test_hmong_phase_callback_preserves_completed_chunk_progress(tmp_path, monkeypatch):
    """Exercise callback persistence only; this does not simulate/validate F5 inference."""
    import importlib
    import numpy as np
    from state_io import read_progress, write_progress

    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    progress_path = tmp_path / 'progress.json'
    write_progress(progress_path, {'completed': 7, 'total': 20, 'progress': 31,
                                   'audio_seconds': 42.5, 'phase': 'Before callback'})
    class CallbackProbe:
        def set_progress_callback(self, callback):
            self.callback = callback
        def synthesize(self, *args, **kwargs):
            self.callback('Đang nạp lõi F5-Hmong…')
            self.callback('Đang tạo âm thanh…')
            return np.array([0.1, -0.1], dtype='float32'), 24000
    monkeypatch.setattr(worker, '_hmong_model_instance', CallbackProbe())
    synthesize = worker.load_synthesizer({'engine': 'f5_hmong', 'speaker': 'hmong-female',
                                        'voice_id': 'hmong-female', 'hmong_steps': 16})
    synthesize('Nyob zoo.', tmp_path / 'raw.wav')
    progress = read_progress(progress_path)
    assert progress['completed'] == 7 and progress['total'] == 20
    assert progress['progress'] == 31 and progress['audio_seconds'] == 42.5
    assert progress['phase'] == 'Đang tạo âm thanh…'
