import json
import wave
from unittest.mock import Mock

import pytest
import calibration
from hardware import resource_presets
from test_standalone_api import studio  # noqa: F401
import app


def test_dual_xeon_56_threads_128gb_is_not_capped_to_eight_models():
    modes=resource_presets(56,28,120)
    assert (modes['fast']['nano_parallel'],modes['fast']['nano_threads'])==(28,1)
    assert (modes['balanced']['nano_parallel'],modes['balanced']['nano_threads'])==(14,2)
    assert (modes['quality']['nano_parallel'],modes['quality']['nano_threads'])==(7,4)
    assert resource_presets(128,64,120)['fast']['nano_parallel']==32
    assert resource_presets(56,28,2)['fast']['nano_parallel']==1
    assert resource_presets(56,28,120,'vieneu')['fast']['nano_parallel']==28
    assert resource_presets(56,28,12,'vieneu')['fast']['nano_parallel']==3


def test_nano_calibration_never_overrides_turbo_memory_budget(tmp_path):
    import os
    record={'nano_steps':4,'selected':{'settings':{'nano_parallel':8,'nano_threads':1}}}
    saved={'logical_cores':os.cpu_count(),'profiles':{'fast':record,'vieneu:fast':{
        'nano_steps':4,'selected':{'settings':{'nano_parallel':2,'nano_threads':2}}}}}
    (tmp_path/'calibration.json').write_text(json.dumps(saved))
    nano=calibration.read_saved_presets(tmp_path,resource_presets(56,28,12))
    turbo=calibration.read_saved_presets(tmp_path,resource_presets(56,28,12,'vieneu'),'vieneu')
    assert nano['fast']['nano_parallel']==8
    assert turbo['fast']['nano_parallel']==2


def test_resident_turbo_team_is_not_memory_budgeted_twice(tmp_path):
    import os
    saved={'logical_cores':os.cpu_count(),'profiles':{'vieneu:fast':{
        'nano_steps':4,'precision':'fp32','selected':{'settings':{'nano_parallel':28,'nano_threads':1}}}}}
    (tmp_path/'calibration.json').write_text(json.dumps(saved))
    # Models consume RAM after calibration, so the free-RAM-only budget falls.
    defaults=resource_presets(56,28,60,'vieneu')
    assert defaults['fast']['nano_parallel']<28
    assert calibration.read_saved_presets(tmp_path,defaults,'vieneu')['fast']['nano_parallel']<28
    resident={'engine':'vieneu','workers':28,'threads':1,'precision':'fp32'}
    warm=calibration.read_saved_presets(tmp_path,resource_presets(56,28,60,'vieneu'),'vieneu',resident)
    assert warm['fast']['nano_parallel']==28
    cold=calibration.read_saved_presets(tmp_path,resource_presets(56,28,60,'vieneu'),'vieneu',{**resident,'precision':'int8'})
    assert cold['fast']['nano_parallel']<28


@pytest.mark.parametrize('engine',['vieneu_nano','vieneu'])
def test_calibration_measures_selects_saves_and_preserves_user_files(tmp_path,monkeypatch,engine):
    for folder in ('audio','parts'): (tmp_path/folder).mkdir()
    unrelated=tmp_path/'audio/user-recording.wav';unrelated.write_bytes(b'user data')
    modes=resource_presets(4,4,16)
    monkeypatch.setattr(calibration,'rendering_presets',lambda selected_engine:modes)
    clock=[0.]
    monkeypatch.setattr(calibration.time,'perf_counter',lambda:clock[0])
    calls={};settings_seen=[]
    def render(job):
        workers=job['nano_parallel'];settings_seen.append(workers)
        calls[workers]=calls.get(workers,0)+1
        clock[0]+={2:(.08,.02),3:(.09,.03),4:(.12,.04)}[workers][(calls[workers]-1)%2]
        path=tmp_path/'parts'/job['id'];path.mkdir()
        with wave.open(str(tmp_path/'audio'/f"{job['id']}.wav"),'wb') as f:
            f.setparams((1,2,24000,0,'NONE','not compressed'));f.writeframes(b'\x00\x20'*9600)
        (tmp_path/'audio'/f"{job['id']}.srt").write_text('1\n00:00:00,000 --> 00:00:00,400\nMẫu đo.')
        (path/'result.json').write_text(json.dumps({'completed':2,'total':2,'audio_seconds':.4,'spoken_audio_seconds':.4,'duration_limited':False}))
    close=Mock()
    job={'id':'a'*32,'text':calibration.sample_text(4),'nano_steps':4,'render_mode':'fast','engine':engine}
    calibration.calibrate(job,render,close,tmp_path)
    result=json.loads((tmp_path/'parts'/job['id']/'result.json').read_text())
    report=result['calibration_report']
    assert report['selected']['settings']=={'nano_parallel':2,'nano_threads':2}
    assert len(report['candidates'])==3 and report['estimate_only']
    assert settings_seen==[2,2,3,3,4,4,2]
    assert unrelated.read_bytes()==b'user data'
    assert (tmp_path/'audio'/f"{job['id']}.wav").exists()
    assert not list((tmp_path/'parts').glob('*-measure-*'))
    assert not list((tmp_path/'audio').glob('*-measure-*'))
    assert close.call_count==1
    saved=calibration.read_saved_presets(tmp_path,resource_presets(4,4,16),engine)
    assert saved['fast']['nano_parallel']==2


def test_calibration_cancel_does_not_touch_other_outputs(tmp_path,monkeypatch):
    ident='c'*32;work=tmp_path/'parts'/ident;work.mkdir(parents=True)
    (work/'cancel.flag').touch()
    render=Mock();close=Mock()
    with pytest.raises(InterruptedError):calibration.calibrate({'id':ident,'render_mode':'fast'},render,close,tmp_path)
    render.assert_not_called()
    assert not (tmp_path/'calibration.json').exists()


def test_forced_stop_cleanup_only_removes_own_calibration_trials(tmp_path):
    ident='a'*32
    owned=ident+'-measure-'+'b'*32
    other='c'*32+'-measure-'+'d'*32
    for name in (owned,other,ident+'-measure-my-recording'):
        (tmp_path/'parts'/name).mkdir(parents=True)
        (tmp_path/'audio').mkdir(exist_ok=True)
        (tmp_path/'audio'/(name+'.wav')).write_bytes(b'keep unless owned')
    calibration.cleanup_measurements(tmp_path,ident)
    assert not (tmp_path/'parts'/owned).exists()
    assert not (tmp_path/'audio'/(owned+'.wav')).exists()
    assert (tmp_path/'audio'/(other+'.wav')).exists()
    assert (tmp_path/'audio'/(ident+'-measure-my-recording.wav')).exists()


def test_calibration_endpoint_accepts_nano_and_turbo_and_rejects_other_models(studio,monkeypatch):
    client,data=studio
    monkeypatch.setattr(app.executor,'submit',Mock())
    (data/'models/vieneu_nano.ready').touch();(data/'models/vieneu.ready').touch()
    response=client.post('/api/calibrate',json={'voice_id':'nano-minhquan','render_mode':'fast'})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['calibration'] is True and job['nano_steps']==4
    assert len(job['text'])>1000 and job['paragraph_pause']==0
    turbo=client.post('/api/calibrate',json={'voice_id':'vi-maianh','render_mode':'fast'})
    assert turbo.status_code==202,turbo.text
    assert turbo.json()['engine']=='vieneu' and turbo.json()['speaker']=='Mai Anh'
    assert turbo.json()['calibration'] is True and turbo.json()['quality']=='standard'
    assert client.post('/api/calibrate',json={'voice_id':'qw-ryan'}).status_code==422
