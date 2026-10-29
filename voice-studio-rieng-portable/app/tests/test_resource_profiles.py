"""Quality settings stay independent from shared CPU/RAM reservations."""
from types import SimpleNamespace

import pytest

import hardware
from hardware import (bounded_settings, choose_execution_model, rendering_limits, rendering_presets,
                      resource_limits, resource_presets)


@pytest.mark.parametrize('physical,reserved',[(1,0),(2,0),(4,0),(8,1),(16,1),(24,2),(28,2)])
def test_smooth_reserves_cpu_only_on_larger_machines(physical,reserved):
    maximum=resource_limits(physical*2,physical,128,'vieneu_nano')
    smooth=resource_limits(physical*2,physical,128,'vieneu_nano','smooth')
    assert maximum['cpu_budget']==physical
    assert smooth['cpu_budget']==physical-reserved
    assert smooth['max_workers']<=smooth['cpu_budget']


@pytest.mark.parametrize('engine',['vieneu_nano','vieneu','voxcpm'])
@pytest.mark.parametrize('precision',['fp32','int8'])
def test_light_keeps_model_quality_with_one_small_team(engine,precision):
    modes=resource_presets(56,28,128,engine,'light',precision)
    for preset in modes.values():
        assert preset['nano_parallel']==1 and 1<=preset['nano_threads']<=2
    field='voxcpm_steps' if engine=='voxcpm' else 'nano_steps'
    assert [modes[mode][field] for mode in ('fast','balanced','quality')]==([4,8,10] if engine=='voxcpm' else [4,8,16])


def test_shared_nano_ram_budget_is_base_plus_per_sequence():
    assert resource_limits(56,28,3.5,'vieneu_nano',execution_model='shared')['max_workers']==4
    assert resource_limits(56,28,10,'vieneu_nano',execution_model='shared')['max_workers']==28
    assert resource_limits(56,28,2,'vieneu_nano',execution_model='shared')['max_workers']==1


def test_shared_turbo_budget_does_not_reserve_weights_per_worker():
    process=resource_limits(56,28,12,'vieneu')
    shared=resource_limits(56,28,12,'vieneu',execution_model='shared')
    assert process['max_workers']==3 and shared['max_workers']==15
    warm={'engine':'vieneu','model_memory':'shared','precision':'fp32','workers':4,'threads':1}
    assert hardware._resident_credit('vieneu',warm,'fp32')==5*1024**3
    assert hardware._resident_credit('vieneu',warm,'int8')==0
    assert hardware._resident_credit('vieneu',warm,'fp32','process')==0


def test_xeon_voxcpm_smooth_uses_a_uniform_team_inside_reserved_budget():
    limits=resource_limits(56,28,128,'voxcpm','smooth')
    fast=resource_presets(56,28,128,'voxcpm','smooth')['fast']
    assert limits['cpu_budget']==26 and limits['max_workers']==7
    assert (fast['nano_parallel'],fast['nano_threads'])==(5,5)
    assert fast['nano_parallel']*fast['nano_threads']<=limits['cpu_budget']


@pytest.mark.parametrize('profile',['maximum','smooth','light'])
@pytest.mark.parametrize('precision',['fp32','int8'])
@pytest.mark.parametrize('physical,ram',[(1,16),(4,32),(14,64),(28,128),(64,256)])
def test_voxcpm_quality_never_reduces_the_independent_resource_budget(profile,precision,physical,ram):
    limits=resource_limits(physical*2,physical,ram,'voxcpm',profile,precision)
    modes=resource_presets(physical*2,physical,ram,'voxcpm',profile,precision)
    teams={(mode['nano_parallel'],mode['nano_threads']) for mode in modes.values()}
    assert len(teams)==1
    for workers,threads in teams:
        assert workers<=limits['max_workers'] and threads<=limits['max_threads']
        assert workers*threads<=limits['cpu_budget']
        assert workers*(20 if precision=='int8' else 16)+4<=ram or workers==1
    assert [modes[mode]['voxcpm_steps'] for mode in ('fast','balanced','quality')]==[4,8,10]
    assert modes['fast']['audio_fit_backend']=='wsola'
    assert modes['balanced']['audio_fit_backend']==modes['quality']['audio_fit_backend']=='ffmpeg'


def test_xeon_voxcpm_balanced_and_quality_use_available_cores_without_lowering_steps():
    smooth=resource_presets(56,28,128,'voxcpm','smooth')
    maximum=resource_presets(56,28,128,'voxcpm','maximum')
    assert (smooth['balanced']['nano_parallel'],smooth['balanced']['nano_threads'])==(5,5)
    assert (smooth['quality']['nano_parallel'],smooth['quality']['nano_threads'])==(5,5)
    assert (maximum['balanced']['nano_parallel'],maximum['balanced']['nano_threads'])==(7,4)
    assert (maximum['quality']['nano_parallel'],maximum['quality']['nano_threads'])==(7,4)
    assert smooth['balanced']['voxcpm_steps']==8 and smooth['quality']['voxcpm_steps']==10


def test_compact_voxcpm_budgets_cold_conversion_peak_instead_of_warm_ram():
    fp32=resource_limits(56,28,128,'voxcpm','maximum','fp32')
    compact=resource_limits(56,28,128,'voxcpm','maximum','int8')
    assert fp32['max_workers']==7 and compact['max_workers']==6
    assert resource_limits(56,28,23,'voxcpm',precision='int8')['memory_sufficient'] is False
    assert resource_limits(56,28,24,'voxcpm',precision='int8')['memory_sufficient'] is True
    assert resource_limits(56,28,19,'voxcpm')['memory_sufficient'] is False
    assert resource_limits(56,28,20,'voxcpm')['memory_sufficient'] is True


def test_compact_warm_backend_can_reuse_ram_below_cold_threshold(monkeypatch):
    monkeypatch.setattr(hardware,'_machine_resources',lambda *args:(56,28,10))
    warm={'engine':'voxcpm','precision':'int8','workers':1,'threads':4}
    assert rendering_limits('voxcpm',warm,precision='int8')['memory_sufficient'] is True
    assert rendering_limits('voxcpm',{**warm,'precision':'fp32'},precision='int8')['memory_sufficient'] is False
    assert rendering_limits('voxcpm',{**warm,'workers':99},precision='int8')['memory_sufficient'] is False


@pytest.mark.parametrize('bad',[True,0,-1,1.5,'4',None])
def test_explicit_tuning_rejects_invalid_integer_values(bad):
    limits={'cpu_budget':26,'max_workers':26,'max_threads':8}
    with pytest.raises(ValueError):bounded_settings({'nano_parallel':bad,'nano_threads':2},limits)
    with pytest.raises(ValueError):bounded_settings({'nano_parallel':2,'nano_threads':bad},limits)


def test_explicit_tuning_never_escapes_ram_cpu_or_light_limits():
    limits=resource_limits(56,28,3.5,'vieneu_nano','smooth',execution_model='shared')
    settings=bounded_settings({'nano_parallel':32,'nano_threads':8,'nano_steps':16},limits)
    assert settings['nano_parallel']==4 and settings['nano_threads']==6
    assert settings['nano_steps']==16
    assert settings['nano_parallel']*settings['nano_threads']<=26
    light=bounded_settings({'nano_parallel':32,'nano_threads':8},resource_limits(56,28,128,'vieneu','light'))
    assert light['nano_parallel']==1 and light['nano_threads']==2


def test_resident_credit_requires_matching_engine_precision_and_allocation():
    shared={'engine':'vieneu_nano','model_memory':'shared','workers':4,'threads':1}
    assert hardware._resident_credit('vieneu_nano',shared,'fp32')==2*1024**3
    assert hardware._resident_credit('vieneu_nano',{**shared,'model_memory':'process'},'fp32')==0
    compact={'engine':'voxcpm','precision':'int8','workers':2,'threads':4}
    assert hardware._resident_credit('voxcpm',compact,'int8')==16*1024**3
    assert hardware._resident_credit('voxcpm',compact,'fp32')==0
    assert hardware._resident_credit('voxcpm',{**compact,'threads':True},'int8')==0


def test_restricted_logical_affinity_does_not_become_physical_capacity(monkeypatch):
    import os
    import psutil
    from pathlib import Path
    monkeypatch.setattr(os,'cpu_count',lambda:56)
    monkeypatch.setattr(os,'sched_getaffinity',lambda pid:set(range(6)),raising=False)
    monkeypatch.setattr(psutil,'Process',lambda:SimpleNamespace(cpu_affinity=lambda:list(range(6))))
    monkeypatch.setattr(psutil,'cpu_count',lambda logical=False:28)
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(available=128*1024**3,total=128*1024**3))
    original=Path.is_file
    monkeypatch.setattr(Path,'is_file',lambda path:False if str(path).startswith('/sys/fs/cgroup/') else original(path))
    limits=rendering_limits('vieneu_nano',resource_profile='maximum')
    assert limits['cpu_budget']==3 and limits['max_workers']==3


@pytest.mark.parametrize('function',[resource_presets,resource_limits])
def test_unknown_profile_or_precision_is_rejected(function):
    with pytest.raises(ValueError):function(56,28,128,resource_profile='turbo')
    with pytest.raises(ValueError):function(56,28,128,precision='fp16')


def execution_machine(monkeypatch,physical,available_gb):
    """Control capacity while retaining production reservation calculations."""
    def resources(engine,resident=None,precision='fp32',execution_model='shared'):
        credit=hardware._resident_credit(engine,resident,precision,execution_model)/1024**3
        return physical*2,physical,available_gb+credit
    monkeypatch.setattr(hardware,'_machine_resources',resources)


@pytest.mark.parametrize('engine',['vieneu_nano','vieneu'])
@pytest.mark.parametrize('physical,profile',[
    (2,'maximum'),(4,'maximum'),(8,'maximum'),
    (8,'smooth'),(28,'maximum'),(28,'smooth'),(28,'light'),
])
def test_auto_execution_keeps_shared_weights_until_the_machine_is_measured(monkeypatch,engine,physical,profile):
    execution_machine(monkeypatch,physical,128)
    assert choose_execution_model(engine,profile)=='shared'


@pytest.mark.parametrize('engine,available',[
    ('vieneu_nano',11.49),('vieneu_nano',11.5),('vieneu',25.49),('vieneu',25.5),
])
def test_available_ram_alone_does_not_prove_a_faster_execution_model(monkeypatch,engine,available):
    execution_machine(monkeypatch,28,available)
    assert choose_execution_model(engine,'maximum')=='shared'


@pytest.mark.parametrize('engine',['vieneu_nano','vieneu'])
@pytest.mark.parametrize('profile',['maximum','smooth','light'])
@pytest.mark.parametrize('selection',['process','shared'])
def test_explicit_onnx_execution_is_honored_without_changing_the_resource_profile(monkeypatch,engine,profile,selection):
    execution_machine(monkeypatch,2,3)
    assert choose_execution_model(engine,profile,selection)==selection
    # Explicit process selection does not bypass the low-memory/CPU hard caps.
    limits=rendering_limits(engine,resource_profile=profile,execution_model=selection)
    assert limits['max_workers']<=2 and limits['cpu_budget']<=2
    if profile=='light':assert limits['max_workers']==1


@pytest.mark.parametrize('engine',['voxcpm','qwen','qwen_clone','system'])
@pytest.mark.parametrize('selection',['auto','process','shared'])
def test_non_onnx_engines_keep_their_isolated_process_backend(engine,selection):
    assert choose_execution_model(engine,cpu_execution=selection)=='process'


@pytest.mark.parametrize('engine,available', [('vieneu_nano',2),('vieneu',4)])
def test_matching_warm_process_team_does_not_replace_a_measured_choice(monkeypatch,engine,available):
    execution_machine(monkeypatch,28,available)
    warm={'engine':engine,'model_memory':'process','precision':'fp32','workers':8,'threads':1}
    assert choose_execution_model(engine,'maximum')=='shared'
    assert choose_execution_model(engine,'maximum',resident=warm)=='shared'
    for changed in ({'engine':'other'},{'model_memory':'shared'},
                    {'precision':'int8'},{'workers':True},{'threads':True}):
        assert choose_execution_model(engine,'maximum',resident={**warm,**changed})=='shared'


def test_nano_process_reservation_matches_its_legacy_fp32_budget():
    warm={'engine':'vieneu_nano','model_memory':'process','workers':8,'threads':1}
    assert hardware._resident_credit('vieneu_nano',warm,'fp32','process')==10*1024**3
    assert hardware._resident_credit('vieneu_nano',warm,'int8','process')==0


@pytest.mark.parametrize('selection',[None,True,1,[],{},'threads','AUTO'])
def test_invalid_execution_selector_is_rejected(selection):
    with pytest.raises(ValueError):choose_execution_model('vieneu',cpu_execution=selection)


def test_execution_chooser_rejects_invalid_profile_and_precision():
    with pytest.raises(ValueError):choose_execution_model('vieneu',resource_profile='unknown')
    with pytest.raises(ValueError):choose_execution_model('vieneu',precision='fp16')


def execution_choice_file(tmp_path,engine='vieneu',memory='process',workers=8,process_speed=8.,shared_speed=4.):
    import json
    import os
    record={'model_memory':memory,'nano_steps':4,
            'settings':{'nano_parallel':workers,'nano_threads':1},
            'measurements':{'shared':{'realtime_multiplier':shared_speed},
                            'process':{'realtime_multiplier':process_speed}}}
    saved={'logical_cores':os.cpu_count(),'execution_choices':{f'{engine}:smooth:fast:fp32':record}}
    (tmp_path/'calibration.json').write_text(json.dumps(saved))
    return saved


@pytest.mark.parametrize('engine',['vieneu_nano','vieneu'])
def test_automatic_execution_uses_a_measured_in_budget_winner(tmp_path,monkeypatch,engine):
    execution_machine(monkeypatch,28,128)
    execution_choice_file(tmp_path,engine)
    assert choose_execution_model(engine,data=tmp_path)=='process'
    # Changing the profile, quality mode or precision needs its own comparison.
    assert choose_execution_model(engine,'maximum',data=tmp_path)=='shared'
    assert choose_execution_model(engine,data=tmp_path,render_mode='quality')=='shared'
    assert choose_execution_model(engine,data=tmp_path,precision='int8')=='shared'
    assert choose_execution_model(engine,cpu_execution='shared',data=tmp_path)=='shared'


def test_automatic_choice_rechecks_current_ram_and_compatible_resident_team(tmp_path,monkeypatch):
    execution_machine(monkeypatch,28,4)
    execution_choice_file(tmp_path)
    assert choose_execution_model('vieneu',data=tmp_path)=='shared'
    warm={'engine':'vieneu','model_memory':'process','precision':'fp32','workers':8,'threads':1}
    assert choose_execution_model('vieneu',resident=warm,data=tmp_path)=='process'
    assert choose_execution_model('vieneu',resident={**warm,'precision':'int8'},data=tmp_path)=='shared'


@pytest.mark.parametrize('change',[
    {'logical_cores':-1}, {'model_memory':'unknown'}, {'nano_steps':16},
    {'settings':{'nano_parallel':True,'nano_threads':1}},
    {'settings':{'nano_parallel':28,'nano_threads':2}},
    {'measurements':{'shared':{'realtime_multiplier':4},'process':{'realtime_multiplier':4.1}}},
    {'measurements':{'shared':{'realtime_multiplier':4},'process':{'realtime_multiplier':float('nan')}}},
])
def test_invalid_or_noisy_automatic_records_keep_shared_weights(tmp_path,monkeypatch,change):
    import json
    execution_machine(monkeypatch,28,128)
    saved=execution_choice_file(tmp_path)
    if 'logical_cores' in change:saved.update(change)
    else:saved['execution_choices']['vieneu:smooth:fast:fp32'].update(change)
    (tmp_path/'calibration.json').write_text(json.dumps(saved))
    assert choose_execution_model('vieneu',data=tmp_path)=='shared'


@pytest.mark.parametrize('contents',['null','[]','{}','{"execution_choices":[]}','not JSON'])
def test_corrupt_automatic_execution_file_is_ignored(tmp_path,contents):
    (tmp_path/'calibration.json').write_text(contents)
    assert choose_execution_model('vieneu',data=tmp_path)=='shared'
