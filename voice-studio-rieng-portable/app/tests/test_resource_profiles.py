"""Quality settings stay independent from shared CPU/RAM reservations."""
from types import SimpleNamespace

import pytest

import hardware
from hardware import (bounded_settings, rendering_limits, rendering_presets,
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
