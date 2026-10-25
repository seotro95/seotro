"""Installer selection and nonblocking hardware reporting without downloading wheels."""
from types import SimpleNamespace
from unittest.mock import Mock
import json
import subprocess
import sys

import pytest

import hardware
import setup_runtime


def installed_pair(monkeypatch, version):
    monkeypatch.setattr(setup_runtime, 'package_version', lambda name: version)
    install = Mock()
    monkeypatch.setattr(setup_runtime, 'pip', install)
    return install


@pytest.mark.parametrize('cuda,cap,name,wheel', [
    ('12.4', '8.6', 'NVIDIA RTX 3090', 'cu124'),
    ('12.2', '7.5', 'NVIDIA RTX 2080', 'cu118'),
    ('11.7', '7.5', 'NVIDIA RTX 2080', None),
    ('13.0', '12.0', 'NVIDIA RTX 5090', None),
    ('12.4', '3.5', 'NVIDIA Tesla K20', None),
])
def test_wheel_matches_driver_and_supported_gpu(monkeypatch, cuda, cap, name, wheel):
    monkeypatch.setattr(hardware.shutil, 'which', lambda _: '/mock/nvidia-smi')
    responses = iter([
        SimpleNamespace(stdout='Driver Version: 999 CUDA Version: ' + cuda, returncode=0),
        SimpleNamespace(stdout=name + ', ' + cap + '\n', returncode=0),
    ])
    monkeypatch.setattr(hardware.subprocess, 'run', lambda *a, **k: next(responses))
    result = hardware.detect_nvidia()
    assert result['detected']
    assert result['wheel'] == wheel
    if wheel is None:
        assert result['reason']


def test_old_smi_query_falls_back_to_gpu_name(monkeypatch):
    monkeypatch.setattr(hardware.shutil, 'which', lambda _: '/mock/nvidia-smi')
    responses = iter([
        SimpleNamespace(stdout='CUDA Version: 12.4', returncode=0),
        SimpleNamespace(stdout='', returncode=1),
        SimpleNamespace(stdout='NVIDIA GeForce RTX 5090\n', returncode=0),
    ])
    monkeypatch.setattr(hardware.subprocess, 'run', lambda *a, **k: next(responses))
    result = hardware.detect_nvidia()
    assert result['detected'] and result['wheel'] is None
    assert 'Blackwell' in result['reason']


def test_auto_upgrades_cpu_pair_on_supported_nvidia(monkeypatch):
    install = installed_pair(monkeypatch, '2.6.0+cpu')
    monkeypatch.setattr(hardware, 'detect_nvidia', lambda: {'wheel': 'cu124', 'detected': True})
    monkeypatch.setattr(hardware, 'probe_torch', lambda: {'cuda_available': True})
    setup_runtime.prepare_torch()
    install.assert_called_once()
    args = install.call_args.args
    assert 'https://download.pytorch.org/whl/cu124' in args
    assert '--force-reinstall' in args
    assert args[:2] == ('torch==2.6.0', 'torchaudio==2.6.0')


@pytest.mark.parametrize('version', ['2.6.0+cpu', '2.6.0+cu124'])
def test_explicit_cpu_preserves_matched_install_without_gpu_probe(monkeypatch, version):
    install = installed_pair(monkeypatch, version)
    detection, probe = Mock(), Mock()
    monkeypatch.setattr(hardware, 'detect_nvidia', detection)
    monkeypatch.setattr(hardware, 'probe_torch', probe)
    setup_runtime.prepare_torch(cpu=True)
    install.assert_not_called()
    detection.assert_not_called()
    probe.assert_not_called()


def test_existing_working_cuda_not_reinstalled(monkeypatch):
    install = installed_pair(monkeypatch, '2.6.0+cu124')
    monkeypatch.setattr(hardware, 'probe_torch', lambda: {'cuda_build': '12.4', 'cuda_available': True})
    setup_runtime.prepare_torch(gpu=True)
    install.assert_not_called()


def test_explicit_gpu_rejects_installed_but_unusable_cuda(monkeypatch):
    install = installed_pair(monkeypatch, '2.6.0+cu124')
    monkeypatch.setattr(hardware, 'probe_torch', lambda: {'cuda_available': False, 'reason': 'Driver is unavailable'})
    with pytest.raises(RuntimeError, match='Driver is unavailable'):
        setup_runtime.prepare_torch(gpu=True)
    install.assert_not_called()


def test_auto_keeps_cpu_and_explicit_gpu_explains_unsupported_device(monkeypatch):
    install = installed_pair(monkeypatch, '2.6.0+cpu')
    monkeypatch.setattr(hardware, 'detect_nvidia', lambda: {'wheel': None, 'reason': 'Blackwell needs newer PyTorch'})
    setup_runtime.prepare_torch()
    with pytest.raises(RuntimeError, match='Blackwell'):
        setup_runtime.prepare_torch(gpu=True)
    install.assert_not_called()


def test_explicit_gpu_checks_runtime_after_install(monkeypatch):
    install = installed_pair(monkeypatch, '2.6.0+cpu')
    monkeypatch.setattr(hardware, 'detect_nvidia', lambda: {'wheel': 'cu124'})
    monkeypatch.setattr(hardware, 'probe_torch', lambda: {'cuda_available': False, 'reason': 'GPU cannot execute a CUDA kernel'})
    with pytest.raises(RuntimeError, match='CUDA kernel'):
        setup_runtime.prepare_torch(gpu=True)
    install.assert_called_once()


def test_probe_recovers_from_timeout_and_reads_marker_after_warning(monkeypatch):
    def timeout(*a, **k):
        assert k['timeout'] == 15
        raise subprocess.TimeoutExpired(a[0], 15)
    monkeypatch.setattr(hardware.subprocess, 'run', timeout)
    assert hardware.probe_torch()['cuda_available'] is False
    payload = {'cuda_available': True, 'device_name': 'GPU name'}
    monkeypatch.setattr(hardware.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout='warning\nHMONG_HARDWARE=' + json.dumps(payload)))
    assert hardware.probe_torch() == payload


def test_probe_rejects_driver_enumeration_without_working_kernel(monkeypatch):
    class BrokenCuda:
        @staticmethod
        def is_available(): return True
        @staticmethod
        def get_device_capability(_): return (8, 6)
        @staticmethod
        def get_device_name(_): return 'NVIDIA GPU'
    def fail_kernel(*a, **k):
        raise RuntimeError('no kernel image is available')
    fake = SimpleNamespace(cuda=BrokenCuda(), ones=fail_kernel, backends=SimpleNamespace(mps=None),
                           version=SimpleNamespace(cuda='12.4'), __version__='2.6.0+cu124')
    monkeypatch.setitem(sys.modules, 'torch', fake)
    lines = []
    exec(hardware._TORCH_PROBE, {'print': lines.append})
    result = json.loads(lines[-1].removeprefix('HMONG_HARDWARE='))
    assert result['cuda_available'] is False
    assert result['reason']


def test_status_never_claims_unsupported_blackwell_is_ready():
    result = hardware._make_report('auto', 4, {'detected': True}, {
        'cuda_available': True, 'capability': [12, 0], 'torch_version': '2.6.0+cu124'})
    assert result['device'] == 'cpu'
    assert result['cuda_available'] is False
    assert 'Blackwell' in result['reason']


def test_hardware_report_is_nonblocking_and_starts_only_one_probe(monkeypatch):
    monkeypatch.setattr(hardware, '_reports', {})
    monkeypatch.setattr(hardware, '_pending', set())
    thread = Mock()
    monkeypatch.setattr(hardware.threading, 'Thread', thread)
    first = hardware.hardware_info()
    second = hardware.hardware_info()
    assert first['probing'] and second['probing']
    assert thread.call_count == 1
    thread.return_value.start.assert_called_once()
    key = next(iter(hardware._pending))
    hardware._reports[key] = (hardware.time.monotonic(), {'device': 'cuda', 'probing': False})
    assert hardware.hardware_info() == {'device': 'cuda', 'probing': False}
    assert thread.call_count == 1


@pytest.mark.parametrize('flag,expected', [('--cpu', 'cpu'), ('--gpu', 'auto')])
def test_launcher_device_flags_apply_before_importing_app(tmp_path, monkeypatch, flag, expected):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path))
    import launch
    monkeypatch.setenv('HMONG_F5_DEVICE', 'cuda')
    listener = Mock()
    listener.getsockname.return_value = ('127.0.0.1', 12345)
    context = Mock(__enter__=Mock(return_value=listener), __exit__=Mock(return_value=False))
    monkeypatch.setattr(launch.socket, 'socket', lambda *a: context)
    monkeypatch.setattr(launch.threading, 'Thread', Mock())
    uvicorn = SimpleNamespace(Server=Mock(), Config=Mock())
    monkeypatch.setitem(sys.modules, 'uvicorn', uvicorn)
    monkeypatch.setitem(sys.modules, 'app', SimpleNamespace(app=object()))
    launch.main([flag])
    assert launch.os.environ['HMONG_F5_DEVICE'] == expected
    uvicorn.Server.return_value.run.assert_called_once_with(sockets=[listener])
