import json
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
import app
import hardware
from test_standalone_api import studio  # noqa: F401
from test_reference_voices_api import reference_catalog, KOREAN  # noqa: F401
from test_native_multilingual_api import installed
from test_native_worker import native_worker  # noqa: F401
from test_worker_optimization import worker, tones, write_pcm  # noqa: F401
from test_native_voxcpm_ui import run_javascript


@pytest.mark.parametrize('ram',[0,8,16,32,64,128])
@pytest.mark.parametrize('cores',[2,4,16,28])
def test_omni_cpu_teams_keep_steps_and_fit_real_cpu_ram(monkeypatch,ram,cores):
    monkeypatch.setattr(hardware,'_machine_resources',lambda *a,**kw:(cores*2,cores,ram))
    limits=hardware.native_omni_cpu_limits('maximum')
    presets=hardware.native_omni_cpu_presets('maximum')
    assert [presets[m]['omnivoice_steps'] for m in ['fast','balanced','quality']]==[8,16,16]
    for preset in presets.values():
        assert preset['nano_threads']*preset['nano_parallel']<=cores
        if preset['nano_parallel']>1:assert preset['nano_parallel']*6+4<=ram
        assert preset['nano_parallel']<=limits['max_workers']


def test_omni_cpu_api_honors_parallel_budget_without_changing_reference_or_quality(reference_catalog,monkeypatch):
    client,data,_,_=reference_catalog
    installed(monkeypatch,('cpu','cuda'))
    monkeypatch.setattr(app,'native_omni_cpu_limits',lambda profile:{'cpu_budget':4,'max_workers':2,'max_threads':4})
    monkeypatch.setattr(app,'native_omni_cpu_presets',lambda profile:{m:{'nano_parallel':2,'nano_threads':2,'omnivoice_steps':16} for m in ['fast','balanced','quality']})
    for device,workers in [('cpu',2),('cuda',1)]:
        result=client.post('/api/speech',json={'voice_id':KOREAN,'language':'ko','text':'안녕하세요.',
            'international_backend':'omnivoice','international_device':device,'omnivoice_steps':32,
            'nano_parallel':8,'nano_threads':2})
        assert result.status_code==202,result.text
        job=result.json()
        assert job['voice_id']==KOREAN and job['language']=='ko'
        assert job['omnivoice_steps']==32 and job['nano_parallel']==workers


def test_omni_cpu_cues_overlap_and_keep_original_subtitle_timeline(native_worker,tmp_path,monkeypatch):
    barrier=threading.Barrier(2);seen=set()
    def speak(text,path):
        seen.add(threading.get_ident());barrier.wait(timeout=10);write_pcm(path,tones([220],.1))
    monkeypatch.setattr(native_worker,'get_synthesizer',lambda job:speak)
    monkeypatch.setattr(native_worker,'create_render_pool',lambda workers,job:ThreadPoolExecutor(max_workers=workers))
    text='1\n00:00:00,000 --> 00:00:00,500\nBonjour.\n\n2\n00:00:01,000 --> 00:00:01,500\nBonsoir.'
    try:
        native_worker.render({'id':'omni-cpu','text':text,'input_format':'srt','engine':'voxcpm','international_backend':'omnivoice',
            'international_device':'cpu','omnivoice_steps':16,'nano_threads':2,'nano_parallel':2,
            'language':'fr','format':'wav','speed':1,'cue_fit':'strict'})
        result=json.loads((tmp_path/'parts/omni-cpu/result.json').read_text())
        assert len(seen)==2 and result['execution_settings']['workers']==2
        assert result['execution_settings']['omnivoice_steps']==16
        assert result['audio_seconds']==1.5
        assert json.loads((tmp_path/'parts/omni-cpu/alignment.json').read_text())['sync_ok']
    finally:native_worker.close_nano_pool()


def test_omni_cpu_ui_uses_server_team_instead_of_forcing_one_session():
    run_javascript(r'''
config={native_omni_cpu_limits_by_resource:{maximum:{max_workers:2,max_threads:4,cpu_budget:4}},
native_omni_cpu_rendering_presets_by_resource:{maximum:{balanced:{nano_parallel:2,nano_threads:2,omnivoice_steps:16}}}};
$('resource-profile').value='maximum';$('international-backend').value='omnivoice';$('international-device').value='cpu';
const voice={engine:'voxcpm'};
assert.equal(parallelLimit(voice),2);
assert.equal(renderingPresets(voice).balanced.omnivoice_steps,16);
assert.deepEqual(boundedRenderResources(voice,{nano_parallel:8,nano_threads:8}),{nano_parallel:2,nano_threads:2});
$('international-device').value='cuda';assert.equal(parallelLimit(voice),1);
''')
