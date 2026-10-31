from unittest.mock import Mock
from test_standalone_api import studio  # noqa: F401
import pytest
import app
from performance import speed_report
from hardware import rendering_presets


def test_srt_silence_does_not_satisfy_speech_speed_goal():
    report=speed_report(3600,100,spoken_seconds=500)
    assert report['realtime_multiplier']==5
    assert report['target_30x_met_on_sample'] is False
    assert report['excluded_silence_seconds']==3100
    assert report['measurement_audio_seconds']==500


def test_hardware_presets_are_bounded_and_explicit():
    modes=rendering_presets()
    assert set(modes)=={'fast','balanced','quality'}
    assert [modes[n]['nano_steps'] for n in ('fast','balanced','quality')]==[4,8,16]
    assert all(1<=m['nano_parallel']<=32 and 1<=m['nano_threads']<=4 for m in modes.values())
    assert modes['fast']['audio_fit_backend']=='wsola'
    assert modes['balanced']['audio_fit_backend']=='ffmpeg'


def ready_system(monkeypatch):
    monkeypatch.setattr(app.executor,'submit',Mock())
    monkeypatch.setattr(app,'installed_voices',lambda:[{'id':'test-system','name':'Test','engine':'system','speaker':'Test','languages':['vi']}])


def test_mode_defaults_and_explicit_tuning(studio,monkeypatch):
    client,data=studio;ready_system(monkeypatch)
    response=client.post('/api/speech',json={'voice_id':'test-system','text':'Xin chào bạn.','render_mode':'fast','delivery':'story'})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['nano_steps']==4 and job['audio_fit_backend']=='wsola'
    assert job['paragraph_pause']==.5
    explicit=client.post('/api/speech',json={'voice_id':'test-system','text':'Xin chào bạn.','render_mode':'fast','nano_steps':8,'nano_parallel':1,'nano_threads':2,'audio_fit_backend':'ffmpeg','paragraph_pause':0})
    assert explicit.status_code==202,explicit.text
    job=explicit.json()
    assert job['nano_steps']==8 and job['nano_parallel']==1 and job['audio_fit_backend']=='ffmpeg'
    assert job['paragraph_pause']==0


def test_real_benchmark_uses_text_and_normal_queue(studio,monkeypatch):
    client,data=studio
    monkeypatch.setattr(app.executor,'submit',Mock())
    (data/'models/vieneu_nano.ready').touch()
    response=client.post('/api/benchmark',json={'voice_id':'nano-minhquan','render_mode':'balanced','delivery':'documentary'})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['input_format']=='txt' and '[pause=' not in job['text']
    assert len(job['text'])>500 and job['paragraph_pause']==0
    assert job['status']=='queued' and job['render_mode']=='balanced'
    assert (data/'jobs'/f"{job['id']}.json").exists()
    assert client.post('/api/benchmark',json={'voice_id':'nano-minhquan','language':'en-US'}).status_code==422


def test_genres_expose_real_bundled_speakers(studio):
    client,data=studio
    config=client.get('/api/config').json()
    assert config['version']=='1.12.0'
    assert {'review','horror','fairytale','documentary','ad'}<={p['id'] for p in config['delivery_profiles']}
    voices=client.get('/api/voices').json()['voices']
    assert len({v['speaker'] for v in voices if v.get('engine')=='vieneu_nano'})==11
    assert any(v.get('speaker')=='Ngọc Huyền' and v.get('engine')=='vieneu' for v in voices)


def test_turbo_uses_its_own_resource_budget_without_changing_mai_anh(studio,monkeypatch):
    client,data=studio
    monkeypatch.setattr(app.executor,'submit',Mock())
    monkeypatch.setattr(app,'supports_int8',lambda:False)
    monkeypatch.setattr(app,'rendering_limits',lambda *args,**kwargs:{'max_workers':28,'max_threads':8,'cpu_budget':28})
    monkeypatch.setattr(app,'effective_rendering_presets',lambda engine='vieneu_nano',*args,**kwargs:{
        'fast':{'nano_steps':4,'nano_parallel':6 if engine=='vieneu' else 28,'nano_threads':2,'audio_fit_backend':'wsola'}})
    (data/'models/vieneu.ready').touch()
    response=client.post('/api/speech',json={'voice_id':'vi-maianh','text':'Xin chào.','render_mode':'fast'})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['engine']=='vieneu' and job['speaker']=='Mai Anh'
    assert job['nano_parallel']==6 and job['nano_threads']==2 and job['quality']=='standard'


def test_missing_warm_model_snapshot_during_render_does_not_break_config(studio,monkeypatch):
    from types import SimpleNamespace
    client,data=studio
    with monkeypatch.context() as scoped:
        scoped.setattr(app,'warm_worker',SimpleNamespace(pid=999999,poll=lambda:None))
        scoped.setattr(app,'system_info',lambda **kwargs:{'cpu':'test'})
        assert not (data/'warm-model.json').exists()
        assert client.get('/api/config').status_code==200
        assert client.get('/api/system-info').status_code==200
