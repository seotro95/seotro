"""Bounded international pools and native benchmark inputs, without AI loading."""
from types import SimpleNamespace
import os

import pytest

from calibration import (BENCHMARK_LANGUAGES, NATIVE_SAMPLES, SAMPLES,
                         benchmark_sample_text, read_saved_presets, sample_text)
from hardware import rendering_presets, resource_presets
from language_catalog import CORE_LANGUAGES


def test_xeon_voxcpm_team_fits_physical_cpu_and_fp32_memory():
    modes=resource_presets(56,28,128,'voxcpm')
    assert modes['fast']['nano_parallel']==7
    assert modes['fast']['nano_threads']==4
    for preset in modes.values():
        assert preset['nano_parallel']*16+4<=128
        assert preset['nano_parallel']*preset['nano_threads']<=28
        assert 1<=preset['nano_parallel']<=8
        assert 1<=preset['nano_threads']<=8
        assert 'nano_steps' not in preset
    assert [modes[name]['voxcpm_steps'] for name in ('fast','balanced','quality')]==[4,8,10]
    assert modes['fast']['audio_fit_backend']=='wsola'


@pytest.mark.parametrize('available',[0,8,16,19,20,32,35])
def test_limited_ram_never_creates_multiple_voxcpm_models(available):
    assert resource_presets(56,28,available,'voxcpm')['fast']['nano_parallel']==1


def test_voxcpm_uses_physical_capacity_instead_of_hyperthreads():
    modes=resource_presets(56,4,512,'voxcpm')
    assert modes['fast']['nano_parallel']==2
    assert modes['fast']['nano_threads']==2
    assert resource_presets(1,1,128,'voxcpm')['fast']['nano_threads']==1


def test_nano_and_turbo_keep_existing_independent_budgets():
    nano=resource_presets(56,28,40,'vieneu_nano')
    turbo=resource_presets(56,28,40,'vieneu')
    assert nano['fast']['nano_parallel']==28
    assert turbo['fast']['nano_parallel']==12
    assert [nano[name]['nano_steps'] for name in ('fast','balanced','quality')]==[4,8,16]
    assert 'voxcpm_steps' not in nano['fast'] and 'voxcpm_steps' not in turbo['fast']


@pytest.mark.skipif(os.name!='posix',reason='Linux cgroup paths are platform-specific')
def test_detected_voxcpm_presets_respect_linux_cpu_and_memory_quotas(monkeypatch):
    import os
    import psutil
    from pathlib import Path

    original_is_file=Path.is_file
    original_read_text=Path.read_text
    values={'/sys/fs/cgroup/cpu.max':'400000 100000',
            '/sys/fs/cgroup/memory.max':str(32*1024**3),
            '/sys/fs/cgroup/memory.current':str(4*1024**3)}
    monkeypatch.setattr(os,'cpu_count',lambda:56)
    monkeypatch.setattr(os,'sched_getaffinity',lambda pid:set(range(56)),raising=False)
    monkeypatch.setattr(psutil,'cpu_count',lambda logical=False:28)
    monkeypatch.setattr(psutil,'Process',lambda:SimpleNamespace(cpu_affinity=lambda:list(range(56))))
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(available=128*1024**3))
    monkeypatch.setattr(Path,'is_file',lambda path:True if str(path) in values else original_is_file(path))
    monkeypatch.setattr(Path,'read_text',lambda path,*args,**kwargs:values[str(path)] if str(path) in values else original_read_text(path,*args,**kwargs))
    fast=rendering_presets('voxcpm')['fast']
    assert fast['nano_parallel']==1 and fast['nano_threads']==4


def test_native_benchmark_catalog_covers_all_core_languages_and_thai():
    assert set(BENCHMARK_LANGUAGES)==set(CORE_LANGUAGES)|{'th'}
    for language in BENCHMARK_LANGUAGES:
        text=benchmark_sample_text(language,1,'voxcpm')
        assert len(text.splitlines())==4
        assert '[pause=' not in text
        if language!='vi':
            assert 'Đây là đoạn đo số' not in text
            assert all(line in NATIVE_SAMPLES[language.split('-')[0]] for line in text.splitlines())


def test_voxcpm_benchmark_has_multiple_waves_without_unbounded_long_trials():
    assert len(benchmark_sample_text('th',1,'voxcpm').splitlines())==4
    assert len(benchmark_sample_text('ja',7,'voxcpm').splitlines())==14
    assert len(benchmark_sample_text('fr',8,'voxcpm').splitlines())==16
    assert len(benchmark_sample_text('en-US',128,'voxcpm').splitlines())==16
    assert benchmark_sample_text('en-US',2,'voxcpm')==benchmark_sample_text('en-GB',2,'voxcpm')


def test_vietnamese_calibration_samples_keep_existing_behavior():
    old='\n'.join(SAMPLES[i%len(SAMPLES)]+f' Đây là đoạn đo số {i+1}.' for i in range(12))
    assert sample_text(1)==old
    assert sample_text(1,'vi')==old
    assert benchmark_sample_text('vi',1,'vieneu_nano')==old
    assert len(sample_text(32).splitlines())==96


def test_unsupported_benchmark_language_does_not_fall_back_to_vietnamese():
    with pytest.raises(ValueError,match='ngôn ngữ'):
        benchmark_sample_text('xx',1,'voxcpm')


def test_voxcpm_does_not_read_or_reuse_onnx_calibration(tmp_path):
    (tmp_path/'calibration.json').write_text('{invalid json')
    defaults=resource_presets(56,28,128,'voxcpm')
    assert read_saved_presets(tmp_path,defaults,'voxcpm') is defaults


def test_resident_voxcpm_reservation_is_credited_once_and_capped(monkeypatch):
    import os
    import psutil
    from pathlib import Path
    monkeypatch.setattr(os,'cpu_count',lambda:56)
    monkeypatch.setattr(os,'sched_getaffinity',lambda pid:set(range(56)),raising=False)
    monkeypatch.setattr(psutil,'cpu_count',lambda logical=False:28)
    monkeypatch.setattr(psutil,'Process',lambda:SimpleNamespace(cpu_affinity=lambda:list(range(56))))
    monkeypatch.setattr(psutil,'virtual_memory',lambda:SimpleNamespace(available=8*1024**3,total=128*1024**3))
    original=Path.is_file
    monkeypatch.setattr(Path,'is_file',lambda path:False if str(path).startswith('/sys/fs/cgroup/') else original(path))
    resident={'engine':'voxcpm','precision':'fp32','workers':7,'threads':4}
    assert rendering_presets('voxcpm')['fast']['nano_parallel']==1
    assert rendering_presets('voxcpm',resident,resource_profile='maximum')['fast']['nano_parallel']==7
    assert rendering_presets('voxcpm',{**resident,'precision':'int8'})['fast']['nano_parallel']==1
    assert rendering_presets('voxcpm',{**resident,'workers':99})['fast']['nano_parallel']==1
    assert rendering_presets('voxcpm',{**resident,'engine':'vieneu'})['fast']['nano_parallel']==1
