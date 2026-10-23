"""GPU setup must remain separate, explicit and verified by actual CUDA work."""
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import hmong_acceleration as acceleration
import hmong_launcher


@pytest.fixture
def home(tmp_path, monkeypatch):
    base = tmp_path / 'studio with spaces'
    base.mkdir()
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path / 'personal data'))
    monkeypatch.delenv('HMOOB_DEVICE', raising=False)
    return base


def ready_runtime(base):
    runtime = acceleration.runtime_directory(base)
    runtime.mkdir(parents=True)
    (runtime / 'pyvenv.cfg').write_text('include-system-site-packages = true\n')
    python = acceleration.runtime_python(runtime)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text('isolated interpreter fixture')
    record = {'schema': 1, 'identity': acceleration._identity(base), 'runtime': str(runtime),
              'torch_version': acceleration.TORCH_VERSION, 'gpu': 'Test NVIDIA GPU'}
    (acceleration.data_directory(base) / acceleration.MARKER_NAME).write_text(json.dumps(record))
    return runtime, python, record


def test_no_gpu_preflight_performs_no_install_or_filesystem_mutation(home, monkeypatch):
    monkeypatch.setattr(acceleration.shutil, 'which', lambda name: None)
    monkeypatch.setattr(acceleration.venv, 'EnvBuilder', lambda **kwargs: pytest.fail('No venv before GPU preflight'))
    monkeypatch.setattr(acceleration.subprocess, 'run', lambda *a, **kw: pytest.fail('No commands or downloads'))
    with pytest.raises(RuntimeError, match='nvidia-smi'):
        acceleration.install_cuda(home)
    assert not acceleration.data_directory(home).exists()


def test_driver_without_gpu_fails_before_creating_runtime(home, monkeypatch):
    monkeypatch.setattr(acceleration.shutil, 'which', lambda name: '/tools/nvidia-smi')
    monkeypatch.setattr(acceleration.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(returncode=1, stdout='', stderr='No devices'))
    with pytest.raises(RuntimeError, match='Driver NVIDIA'):
        acceleration.install_cuda(home)
    assert not acceleration.data_directory(home).exists()


def test_cpu_override_and_existing_child_do_not_probe_or_relaunch(home, monkeypatch):
    runtime, _, _ = ready_runtime(home)
    monkeypatch.setattr(acceleration, '_probe', lambda *a, **kw: pytest.fail('No extra GPU process'))
    monkeypatch.setenv('HMOOB_DEVICE', 'cpu')
    assert acceleration.preferred_interpreter(home) is None
    monkeypatch.delenv('HMOOB_DEVICE')
    monkeypatch.setattr(acceleration.sys, 'prefix', str(runtime))
    assert acceleration.preferred_interpreter(home) is None


def test_valid_identity_requires_real_probe_before_selection(home, monkeypatch):
    runtime, python, _ = ready_runtime(home)
    calls = []
    monkeypatch.setattr(acceleration, '_probe', lambda executable, **kw: calls.append((executable, kw)))
    assert acceleration.preferred_interpreter(home) == python
    assert calls == [(python, {'runtime': runtime})]
    status = acceleration.runtime_status(home)
    assert status['installed'] and status['identity_valid'] and status['throughput_verified'] is False


def test_move_or_python_change_does_not_reuse_saved_runtime(home, monkeypatch, capsys):
    _, _, record = ready_runtime(home)
    record['identity']['application'] = str(home / 'old location')
    marker = acceleration.data_directory(home) / acceleration.MARKER_NAME
    marker.write_text(json.dumps(record))
    monkeypatch.setattr(acceleration, '_probe', lambda *a, **kw: pytest.fail('Do not execute stale runtime'))
    assert acceleration.preferred_interpreter(home) is None
    assert 'install_hmong_cuda.bat' in capsys.readouterr().out
    assert acceleration.runtime_status(home)['identity_valid'] is False


def test_auto_gpu_failure_falls_back_and_explicit_cuda_is_actionable(home, monkeypatch, capsys):
    ready_runtime(home)
    def failed(*a, **kw):
        raise RuntimeError('GPU unavailable')
    monkeypatch.setattr(acceleration, '_probe', failed)
    assert acceleration.preferred_interpreter(home) is None
    assert 'Dùng Python hiện tại' in capsys.readouterr().out
    with pytest.raises(RuntimeError, match='install_hmong_cuda.bat'):
        acceleration.preferred_interpreter(home, 'cuda')


def test_external_working_cuda_interpreter_is_supported_without_marker(home, monkeypatch):
    calls = []
    monkeypatch.setattr(acceleration, '_probe', lambda executable, **kw: calls.append(executable))
    assert acceleration.preferred_interpreter(home, 'cuda') is None
    assert calls == [acceleration.sys.executable]
    assert not acceleration.data_directory(home).exists()


def test_unreadable_marker_warns_before_staying_in_current_python(home, capsys):
    data = acceleration.data_directory(home)
    data.mkdir()
    (data / acceleration.MARKER_NAME).write_text('{incomplete')
    assert acceleration.preferred_interpreter(home) is None
    assert 'install_hmong_cuda.bat' in capsys.readouterr().out


def test_pip_environment_cannot_redirect_installation_or_disable_tls(monkeypatch):
    for name in ('PIP_TARGET', 'PIP_PREFIX', 'PIP_USER', 'PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL', 'PIP_TRUSTED_HOST'):
        monkeypatch.setenv(name, 'do not use this')
    monkeypatch.setenv('PIP_CERT', '/configured/company-ca.pem')
    environment = acceleration._pip_environment()
    assert environment['PIP_CONFIG_FILE'] == os.devnull
    assert environment['PIP_CERT'] == '/configured/company-ca.pem'
    assert not any(name in environment for name in ('PIP_TARGET', 'PIP_PREFIX', 'PIP_USER', 'PIP_EXTRA_INDEX_URL', 'PIP_TRUSTED_HOST'))


def test_probe_rejects_cpu_torch_loaded_from_outside_venv(home, monkeypatch):
    runtime = acceleration.runtime_directory(home)
    details = {'prefix': str(runtime), 'torch_version': acceleration.TORCH_VERSION,
               'torchaudio_version': acceleration.TORCH_VERSION, 'cuda_version': '12.8',
               'gpu': 'GPU', 'gpu_tensor_test': True, 'f5_version': '1.1.22',
               'torch_file': str(home / 'cpu-packages' / 'torch' / '__init__.py'),
               'torchaudio_file': str(runtime / 'Lib' / 'site-packages' / 'torchaudio' / '__init__.py')}
    monkeypatch.setattr(acceleration.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout=json.dumps(details), stderr=''))
    with pytest.raises(RuntimeError, match='outside'):
        acceleration._probe(acceleration.runtime_python(runtime), runtime=runtime)


def fake_builder(events):
    class Builder:
        def __init__(self, **kwargs):
            events.append(('venv', kwargs))
        def create(self, runtime):
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / 'pyvenv.cfg').write_text('test venv')
            python = acceleration.runtime_python(runtime)
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text('test Python')
    return Builder


def test_install_keeps_cpu_and_personal_data_and_marks_ready_only_after_probe(home, monkeypatch):
    data = acceleration.data_directory(home)
    data.mkdir()
    personal = data / 'saved-project.json'
    personal.write_text('keep my project')
    events = []
    monkeypatch.setattr(acceleration, '_preflight', lambda: events.append(('preflight',)))
    monkeypatch.setattr(acceleration.venv, 'EnvBuilder', fake_builder(events))
    def run(command, **kwargs):
        events.append(('command', command, kwargs))
        assert command[0] == str(acceleration.runtime_python(acceleration.runtime_directory(home)))
        assert not (data / acceleration.MARKER_NAME).exists(), 'Not ready before actual GPU probe'
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(acceleration.subprocess, 'run', run)
    def probe(executable, **kwargs):
        events.append(('probe', executable))
        assert not (data / acceleration.MARKER_NAME).exists()
        return {'gpu': 'Verified NVIDIA', 'cuda_version': '12.8'}
    monkeypatch.setattr(acceleration, '_probe', probe)
    record = acceleration.install_cuda(home)
    assert events[0] == ('preflight',)
    assert ('venv', {'system_site_packages': True, 'with_pip': True}) in events
    commands = [event[1] for event in events if event[0] == 'command']
    assert commands[0][1:] == ['-m', 'pip', 'install', '--upgrade', '--no-cache-dir',
        'torch==2.8.0+cu128', 'torchaudio==2.8.0+cu128', '--index-url', acceleration.CUDA_INDEX]
    assert commands[1][1:] == ['-m', 'pip', 'check']
    assert events[-1][0] == 'probe'
    assert personal.read_text() == 'keep my project'
    assert record['throughput_verified'] is False and record['gpu_tensor_test'] is True
    assert acceleration.runtime_status(home)['identity_valid'] is True
    inherited = (acceleration._site_packages(acceleration.runtime_directory(home)) /
                 'hmong_cpu_dependencies.pth').read_text().splitlines()
    assert inherited and all(Path(path).is_absolute() and not path.startswith('import ') for path in inherited)


@pytest.mark.parametrize('failure', ['pip', 'check', 'probe'])
def test_failed_repair_never_leaves_ready_marker_or_changes_saved_data(home, monkeypatch, failure):
    _, _, _ = ready_runtime(home)
    data = acceleration.data_directory(home)
    saved = data / 'saved-voice.wav'
    saved.write_bytes(b'original voice')
    monkeypatch.setattr(acceleration, '_preflight', lambda: None)
    monkeypatch.setattr(acceleration.venv, 'EnvBuilder', fake_builder([]))
    def run(command, **kwargs):
        failed = (failure == 'pip' and 'install' in command) or (failure == 'check' and 'check' in command)
        return SimpleNamespace(returncode=1 if failed else 0)
    monkeypatch.setattr(acceleration.subprocess, 'run', run)
    monkeypatch.setattr(acceleration, '_probe', lambda *a, **kw:
                        (_ for _ in ()).throw(RuntimeError('GPU failed')))
    with pytest.raises(RuntimeError):
        acceleration.install_cuda(home)
    assert saved.read_bytes() == b'original voice'
    assert not (data / acceleration.MARKER_NAME).exists()


def test_installation_lock_rejects_another_installer_and_releases(home):
    data = acceleration.data_directory(home)
    data.mkdir()
    with acceleration._installation_lock(data):
        with pytest.raises(RuntimeError, match='cửa sổ khác'):
            with acceleration._installation_lock(data):
                pytest.fail('Concurrent installation must not enter')
    with acceleration._installation_lock(data):
        pass


def test_launcher_handoff_forwards_all_flags_before_dependency_checks(home, monkeypatch):
    import bundle_check
    monkeypatch.setattr(bundle_check, 'validate_bundle', lambda root: None)
    monkeypatch.setattr(hmong_launcher, 'BASE', home)
    python = home / 'gpu env' / 'python.exe'
    monkeypatch.setattr(acceleration, 'preferred_interpreter', lambda root: python)
    monkeypatch.setattr(hmong_launcher, 'check_dependencies', lambda: pytest.fail('CPU deps not used after handoff'))
    calls = []
    monkeypatch.setattr(hmong_launcher.subprocess, 'call', lambda command, **kwargs:
                        calls.append((command, kwargs)) or 17)
    assert hmong_launcher.main(['--check', '--no-browser']) == 17
    assert calls[0][0] == [str(python), str(home / 'hmong_launcher.py'), '--check', '--no-browser']
    assert 'PYTHONHOME' not in calls[0][1]['env'] and 'PYTHONPATH' not in calls[0][1]['env']


def test_explicit_install_flag_does_not_launch_or_prepare_models(home, monkeypatch):
    import bundle_check
    monkeypatch.setattr(bundle_check, 'validate_bundle', lambda root: None)
    monkeypatch.setattr(hmong_launcher, 'BASE', home)
    calls = []
    monkeypatch.setattr(acceleration, 'install_cuda', lambda root: calls.append(root))
    monkeypatch.setattr(acceleration, 'preferred_interpreter', lambda root: pytest.fail('Installer must not relaunch first'))
    monkeypatch.setattr(hmong_launcher, 'check_dependencies', lambda: pytest.fail('No model/dependency work before GPU installer'))
    assert hmong_launcher.main(['--install-cuda']) == 0
    assert calls == [home]


@pytest.mark.parametrize('flag', ['--check', '--setup-only'])
def test_install_flag_cannot_override_offline_or_model_setup_action(flag, monkeypatch):
    monkeypatch.setattr(acceleration, 'install_cuda', lambda root: pytest.fail('Conflicting actions must not install'))
    with pytest.raises(SystemExit) as result:
        hmong_launcher.main([flag, '--install-cuda'])
    assert result.value.code == 2
