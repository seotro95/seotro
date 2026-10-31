"""Native Q8 teams honor physical CPU/RAM independently of voice quality."""
import pytest

import hardware


def machine(monkeypatch, logical=56, physical=28, available_gb=100):
    calls = []
    def resources(engine, resident=None, precision='fp32', execution_model='shared'):
        calls.append((engine, resident, precision, execution_model))
        return logical, physical, available_gb
    monkeypatch.setattr(hardware, '_machine_resources', resources)
    return calls


@pytest.mark.parametrize('profile,expected,cpu', [
    ('maximum', (7, 4), 28), ('smooth', (6, 4), 26), ('light', (1, 2), 2),
])
def test_dual_xeon_uses_twenty_eight_physical_cores_without_changing_steps(monkeypatch, profile, expected, cpu):
    calls = machine(monkeypatch)
    limits = hardware.native_voxcpm_cpu_limits(profile)
    modes = hardware.native_voxcpm_cpu_presets(profile)
    assert limits['cpu_budget'] == cpu and limits['memory_sufficient']
    assert {(mode['nano_parallel'], mode['nano_threads']) for mode in modes.values()} == {expected}
    assert [modes[name]['voxcpm_steps'] for name in ('fast', 'balanced', 'quality')] == [4, 8, 10]
    assert modes['fast']['audio_fit_backend'] == 'wsola'
    assert modes['balanced']['audio_fit_backend'] == modes['quality']['audio_fit_backend'] == 'ffmpeg'
    assert all(call == ('voxcpm_native', None, 'fp32', 'process') for call in calls)


@pytest.mark.parametrize('physical,logical,ram', [
    (1, 2, 10), (2, 4, 16), (4, 8, 32), (14, 28, 64),
    (28, 56, 100), (64, 128, 256), (128, 256, 512),
])
@pytest.mark.parametrize('profile', ['maximum', 'smooth', 'light'])
def test_every_native_team_fits_physical_cpu_and_six_gib_per_model(monkeypatch, physical, logical, ram, profile):
    machine(monkeypatch, logical, physical, ram)
    limits = hardware.native_voxcpm_cpu_limits(profile)
    for mode in hardware.native_voxcpm_cpu_presets(profile).values():
        workers, threads = mode['nano_parallel'], mode['nano_threads']
        assert 1 <= workers <= limits['max_workers'] <= 8
        assert 1 <= threads <= limits['max_threads'] <= 8
        assert workers * threads <= limits['cpu_budget'] <= physical
        assert workers * 6 + 4 <= ram
        if profile == 'light':
            assert workers == 1 and threads <= 2


@pytest.mark.parametrize('ram,sufficient,workers', [(0, False, 1), (9.9, False, 1),
                                                  (10, True, 1), (15.99, True, 1),
                                                  (16, True, 2), (22, True, 3)])
def test_ram_admission_reserves_system_space_and_caps_workers(monkeypatch, ram, sufficient, workers):
    machine(monkeypatch, available_gb=ram)
    limits = hardware.native_voxcpm_cpu_limits('maximum')
    assert limits['memory_sufficient'] is sufficient
    assert limits['max_workers'] == workers
    assert limits['per_worker_memory_budget_gb'] == 6
    assert limits['memory_reserve_gb'] == 4 and limits['minimum_available_gb'] == 10
    assert limits['available_memory_gb'] == ram


@pytest.mark.parametrize('ram', [None, True, float('nan'), float('inf'), -10])
def test_unknown_or_invalid_memory_does_not_admit_native_load(monkeypatch, ram):
    machine(monkeypatch, available_gb=ram)
    limits = hardware.native_voxcpm_cpu_limits()
    assert not limits['memory_sufficient'] and limits['max_workers'] == 1


def test_four_cpu_cloud_can_explicitly_run_two_two_thread_models(monkeypatch):
    machine(monkeypatch, logical=8, physical=4, available_gb=32)
    limits = hardware.native_voxcpm_cpu_limits('maximum')
    assert limits['max_workers'] >= 2 and limits['cpu_budget'] == 4
    assert hardware.bounded_settings({'nano_parallel': 2, 'nano_threads': 2}, limits) == {
        'nano_parallel': 2, 'nano_threads': 2}


def test_logical_threads_never_double_physical_native_budget(monkeypatch):
    machine(monkeypatch, logical=56, physical=28, available_gb=100)
    limits = hardware.native_voxcpm_cpu_limits('maximum')
    assert limits['cpu_budget'] == 28 and limits['max_workers'] == 8
    bounded = hardware.bounded_settings({'nano_parallel': 8, 'nano_threads': 8}, limits)
    assert bounded['nano_parallel'] * bounded['nano_threads'] <= 28


def test_restricted_affinity_native_budget_uses_existing_machine_detection(monkeypatch):
    machine(monkeypatch, logical=6, physical=3, available_gb=32)
    limits = hardware.native_voxcpm_cpu_limits('maximum')
    assert limits['cpu_budget'] == 3
    assert hardware.native_voxcpm_cpu_presets('maximum')['balanced']['nano_threads'] == 3


@pytest.mark.parametrize('function', [hardware.native_voxcpm_cpu_limits, hardware.native_voxcpm_cpu_presets])
def test_unknown_profile_does_not_silently_choose_a_native_team(function):
    with pytest.raises(ValueError):
        function('turbo')
