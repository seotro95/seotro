"""Exercise selected international voices and bounded resources through HTTP."""
from unittest.mock import Mock

import pytest
import app
from hardware import resource_presets, resource_limits
from test_reference_voices_api import (reference_catalog, prepared_international_model,
                                       KOREAN, THAI, ENGLISH)
from test_standalone_api import studio  # noqa: F401


def xeon_resources(monkeypatch):
    monkeypatch.setattr(app,'effective_rendering_presets',lambda engine='vieneu_nano',resource_profile='smooth',precision='fp32',cpu_execution='auto':resource_presets(56,28,128,engine,resource_profile,precision))
    monkeypatch.setattr(app,'rendering_limits',lambda engine='vieneu_nano',resident=None,resource_profile='smooth',precision='fp32',execution_model='process':resource_limits(56,28,128,engine,resource_profile,precision))


@pytest.mark.parametrize('ident,language',[(KOREAN,'ko'),(THAI,'th')])
def test_native_benchmark_preserves_voice_and_applies_international_fast_mode(reference_catalog,monkeypatch,ident,language):
    client,data,root,submit=reference_catalog
    prepared_international_model(data,monkeypatch)
    xeon_resources(monkeypatch)
    response=client.post('/api/benchmark',json={'voice_id':ident,'language':language,'render_mode':'fast','resource_profile':'maximum'})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['voice_id']==ident and job['engine']=='voxcpm'
    assert job['language']==language and 'Đây là đoạn đo' not in job['text']
    assert job['voxcpm_steps']==4 and job['nano_parallel']==7 and job['nano_threads']==4
    assert len(job['text'].splitlines())==14 and job['paragraph_pause']==0
    submit.assert_called_once()


def test_explicit_international_resources_are_bounded_without_voice_switch(reference_catalog,monkeypatch):
    client,data,root,_=reference_catalog
    prepared_international_model(data,monkeypatch)
    xeon_resources(monkeypatch)
    response=client.post('/api/speech',json={'voice_id':KOREAN,'language':'ko','text':'안녕하세요.',
        'render_mode':'fast','resource_profile':'maximum','voxcpm_steps':10,'nano_parallel':32,'nano_threads':8})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['voice_id']==KOREAN and job['engine']=='voxcpm' and job['speaker'] is None
    assert job['voxcpm_steps']==10 and job['nano_parallel']==7 and job['nano_threads']==4
    assert client.post('/api/speech',json={'voice_id':KOREAN,'language':'ko','text':'안녕하세요.','voxcpm_steps':6}).status_code==422


def test_english_reference_benchmark_stays_on_turbo(reference_catalog,monkeypatch):
    client,data,root,_=reference_catalog
    (data/'models/vieneu.ready').touch()
    response=client.post('/api/benchmark',json={'voice_id':ENGLISH,'language':'en-US','render_mode':'fast'})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['voice_id']==ENGLISH and job['engine']=='vieneu'
    assert 'The morning light' in job['text'] and 'Đây là đoạn đo' not in job['text']


def test_warm_credit_requires_live_matching_worker_pid(studio,monkeypatch):
    import json
    from types import SimpleNamespace
    client,data=studio
    monkeypatch.setattr(app,'warm_worker',SimpleNamespace(pid=12345,poll=lambda:None,wait=Mock()))
    monkeypatch.setattr(app,'stop_worker',Mock())
    calls=[]
    def presets(engine='vieneu_nano',resident=None,**kwargs):
        calls.append(resident)
        return resource_presets(56,28,128,engine)
    monkeypatch.setattr(app,'rendering_presets',presets)
    state={'pid':54321,'engine':'voxcpm','workers':7,'threads':4,'precision':'fp32'}
    (data/'warm-model.json').write_text(json.dumps(state))
    app.effective_rendering_presets('voxcpm')
    assert calls[-1] is None
    state['pid']=12345
    (data/'warm-model.json').write_text(json.dumps(state))
    app.effective_rendering_presets('voxcpm')
    assert calls[-1]==state
    monkeypatch.setattr(app,'warm_worker',None)
