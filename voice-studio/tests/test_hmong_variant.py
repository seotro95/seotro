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
    assert cfg['hmong_steps']==16 and cfg['paragraph_pause']==0
    assert cfg['delivery']=='story' and cfg['emotion']=='warm'
    assert cfg['emotion_strength']==.65 and cfg['auto_rhythm'] is False and cfg['hmong_phrase_context'] is True
    assert cfg['hardware']=='unknown' and 'CHƯA KIỂM TRA' in cfg['hardware_label']
    assert 'do bạn cung cấp và xác nhận' in cfg['hmong_reference_note']
    assert cfg['languages']=={'mww':'Hmong Trắng · Hmoob Daw'}
    assert 'mww' not in cfg['recognition_languages']
    voices=c.get('/api/voices').json()['voices']
    assert {v['id'] for v in voices}=={'hmong-female','hmong-male'}
    assert all(v['engine']=='f5_hmong' and v['native_language']=='mww' for v in voices)
    assert all(v['reference_text_verified'] is True and 'do bạn cung cấp' in v['description'] for v in voices)
    response=c.post('/api/speech',json={'text':'Nyob zoo.','voice_id':'hmong-female','hmong_steps':8,'delivery':'review'})
    assert response.status_code==202,response.text
    assert response.json()['engine']=='f5_hmong' and response.json()['language']=='mww'
    assert c.post('/api/speech',json={'text':'Xin chào.','voice_id':'hmong-female','language':'vi'}).status_code==422
    assert c.post('/api/speech',json={'text':'Nyob zoo.','voice_id':'hmong-female','hmong_steps':12}).status_code==422
    assert c.get('/api/hmong/presets/hmong-female/sample').status_code==200
''')


def test_hmong_job_story_defaults_and_rpa_validation_before_queue(tmp_path):
    run_case(tmp_path, '''
from unittest.mock import patch
from fastapi.testclient import TestClient
import app
with TestClient(app.app) as c, patch.object(app,'model_ready',return_value=False), patch.object(app.executor,'submit') as submit:
    response=c.post('/api/speech',json={'text':'你好','voice_id':'hmong-male'})
    assert response.status_code==422 and 'RPA' in response.text,response.text
    submit.assert_not_called()
with TestClient(app.app) as c, patch.object(app,'model_ready',return_value=True), patch.object(app.executor,'submit'):
    response=c.post('/api/speech',json={'text':'Nyob zoo. Ua tsaug.','voice_id':'hmong-male'})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['hmong_steps']==16 and job['delivery']=='story' and job['paragraph_pause']==0
    assert job['emotion']=='warm' and job['emotion_strength']==.65 and job['auto_rhythm'] is False and job['hmong_phrase_context'] is True
    assert job['segment_plan']=='hmong-expression-v1' and job['total']==1 and job['quality']=='standard'
    response=c.post('/api/speech',json={'text':'Nyob zoo. Ua tsaug.','voice_id':'hmong-male','paragraph_pause':.3,'hmong_steps':4,'auto_rhythm':False})
    assert response.status_code==202,response.text
    assert response.json()['segment_plan']=='hmong-expression-v1' and response.json()['total']==2
    assert response.json()['hmong_steps']==4
''')


def test_hmong_expression_fields_and_inline_controls_are_validated_before_queue(tmp_path):
    run_case(tmp_path, '''
from unittest.mock import patch
from fastapi.testclient import TestClient
from narration import plan_segments
import app
with TestClient(app.app) as c, patch.object(app,'model_ready',return_value=True), patch.object(app.executor,'submit') as submit:
    base={'text':'Nyob zoo.','voice_id':'hmong-male'}
    for invalid in [{'emotion':'angry'},{'emotion_strength':-0.01},{'emotion_strength':1.01},{'emotion_strength':'NaN'},{'text':'[emotion=angry]Nyob zoo.'}]:
        response=c.post('/api/speech',json={**base,**invalid})
        assert response.status_code==422,response.text
    submit.assert_not_called()
    assert not list((app.DATA/'jobs').iterdir())
    text='Nyob zoo. [emotion=warm]**Ua tsaug.** [pause=0.5] Kuv tuaj.'
    response=c.post('/api/speech',json={**base,'text':text,'emotion':'suspense','emotion_strength':.8,'auto_rhythm':False})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['text']==text and job['segment_plan']=='hmong-expression-v1'
    assert job['emotion']=='suspense' and job['emotion_strength']==.8 and job['auto_rhythm'] is False
    segments=plan_segments(job)
    assert [(s.text,s.emotion) for s in segments if s.text]==[('Nyob zoo.','suspense'),('Ua tsaug.','warm'),('Kuv tuaj.','warm')]
    assert all('[emotion=' not in s.text and '[pause=' not in s.text and '**' not in s.text for s in segments)
    assert any(s.emphasis and s.text=='Ua tsaug.' for s in segments) and any(s.pause==.5 for s in segments)
    response=c.post('/api/speech',json={**base,'emotion':'joyful','emotion_strength':0,'auto_rhythm':False})
    assert response.status_code==202,response.text
    assert response.json()['emotion_strength']==0 and response.json()['auto_rhythm'] is False
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


def test_hmong_clone_rejects_unsupported_transcript_and_cleans_temporary_files(tmp_path):
    run_case(tmp_path, '''
from fastapi.testclient import TestClient
from hmong_assets import reference
import app
ref,_=reference('hmong-male')
with TestClient(app.app) as c:
    response=c.post('/api/voices/clone',data={'name':'Kuv lub suab','language':'mww','consent':'true','transcript':'Tiếng Việt'},files={'file':('sample.wav',ref.read_bytes())})
    assert response.status_code==422 and 'RPA' in response.text,response.text
    assert not list((app.DATA/'voices').iterdir())
''')


def test_missing_hmong_preset_is_actionable_and_never_queues_job(tmp_path):
    run_case(tmp_path, '''
from unittest.mock import patch
from fastapi.testclient import TestClient
import app
with TestClient(app.app) as c, patch('hmong_assets.reference',side_effect=FileNotFoundError('male.wav')), patch.object(app.executor,'submit') as submit:
    response=c.post('/api/speech',json={'text':'Nyob zoo.','voice_id':'hmong-male'})
    assert response.status_code==422 and 'ZIP' in response.text and 'assets/hmong' in response.text,response.text
    submit.assert_not_called()
    assert not list((app.DATA/'jobs').iterdir())
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
