"""The light runtime keeps voice/text/quality and enforces physical budgets."""
from unittest.mock import Mock

import pytest
import app
from hardware import resource_presets, resource_limits
from test_standalone_api import studio  # noqa: F401
from test_reference_voices_api import reference_catalog, prepared_international_model, THAI


def xeon(monkeypatch):
    monkeypatch.setattr(app,'effective_rendering_presets',lambda engine='vieneu_nano',resource_profile='smooth',precision='fp32',cpu_execution='auto':
        resource_presets(56,28,128,engine,resource_profile,precision,execution_model='shared'))
    monkeypatch.setattr(app,'rendering_limits',lambda engine='vieneu_nano',resident=None,resource_profile='smooth',precision='fp32',execution_model='shared':
        resource_limits(56,28,128,engine,resource_profile,precision,execution_model='shared'))


@pytest.mark.parametrize('profile,workers,threads',[('maximum',28,1),('smooth',26,1),('light',1,2)])
def test_resource_profiles_keep_nano_voice_text_steps_and_bound_explicit_tuning(studio,monkeypatch,profile,workers,threads):
    client,data=studio
    xeon(monkeypatch)
    monkeypatch.setattr(app.executor,'submit',Mock())
    (data/'models/vieneu_nano.ready').touch()
    text='Một lời đọc đầy đủ để kiểm tra.'
    response=client.post('/api/speech',json={'voice_id':'nano-minhquan','text':text,
        'render_mode':'quality','nano_steps':16,'nano_parallel':32,'nano_threads':8,'resource_profile':profile})
    assert response.status_code==202,response.text
    job=response.json()
    assert job['text']==text and job['voice_id']=='nano-minhquan' and job['nano_steps']==16
    assert job['model_memory']=='shared' and job['resource_profile']==profile
    assert (job['nano_parallel'],job['nano_threads'])==(workers,threads)


def test_int8_is_explicit_preserves_international_voice_and_rejects_insufficient_ram(reference_catalog,monkeypatch):
    client,data,root,submit=reference_catalog
    prepared_international_model(data,monkeypatch)
    xeon(monkeypatch)
    body={'voice_id':THAI,'language':'th','text':'สวัสดีครับ ยินดีต้อนรับ',
          'render_mode':'quality','voxcpm_steps':10,'international_precision':'int8','resource_profile':'light'}
    response=client.post('/api/speech',json=body)
    assert response.status_code==202,response.text
    job=response.json()
    assert job['voice_id']==THAI and job['international_precision']=='int8' and job['voxcpm_steps']==10
    assert job['model_memory']=='process' and (job['nano_parallel'],job['nano_threads'])==(1,2)
    submit.reset_mock()
    monkeypatch.setattr(app,'rendering_limits',lambda *args,**kwargs:{'memory_sufficient':False})
    rejected=client.post('/api/speech',json=body)
    assert rejected.status_code==503 and '24 GB' in rejected.json()['detail']
    submit.assert_not_called()


def test_configuration_exposes_independent_resource_and_precision_budgets(studio):
    client,_=studio
    config=client.get('/api/config').json()
    assert {item['id'] for item in config['resource_profiles']}=={'maximum','smooth','light'}
    for profile in ('maximum','smooth','light'):
        assert set(config['rendering_presets_by_resource'][profile])=={'vieneu_nano','vieneu','voxcpm'}
        assert set(config['voxcpm_int8_rendering_presets_by_resource'][profile])=={'fast','balanced','quality'}
    assert config['version']=='1.10.0'
