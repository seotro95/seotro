"""Exercise runtime isolation and promotion without downloading AI dependencies."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

import clone_runtime as runtime


@pytest.fixture
def studio(tmp_path, monkeypatch):
    root = tmp_path / 'Hmong Studio nữ'
    root.mkdir()
    (root / 'requirements.txt').write_text('fastapi==0.115.0\n', encoding='utf-8')
    (root / 'requirements-cosy.txt').write_text('-r requirements.txt\ntorch==2.6.0\n', encoding='utf-8')
    legacy = root / '.venv' / 'Lib' / 'site-packages' / 'sympy'
    legacy.mkdir(parents=True)
    (legacy / 'locked-file.py').write_bytes(b'legacy package remains intact')
    for relative, data in (
        ('.data/clones/user-sample.mp3', b'personal voice sample'),
        ('.data/models/hmong-cosy/weights.pt', b'already downloaded model'),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    created = []

    class FakeBuilder:
        def __init__(self, **options):
            assert options == {'with_pip': True}

        def create(self, directory):
            directory = Path(directory)
            created.append(directory)
            executable = directory / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b'isolated interpreter placeholder')
            (directory / 'installed-package.txt').write_bytes(b'keep this runtime unchanged')

    monkeypatch.setattr(runtime.venv, 'EnvBuilder', FakeBuilder)
    commands = []

    def successful_run(command, command_root, log=None):
        assert Path(command_root) == root
        commands.append([str(part) for part in command])
        return 0

    monkeypatch.setattr(runtime, '_run', successful_run)
    return root, created, commands


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


def pointer_path(root):
    return root / '.data' / 'runtime' / 'clone-runtime.json'


def test_complete_install_selects_new_runtime_without_touching_legacy_or_samples(studio):
    root, created, commands = studio
    legacy = snapshot(root / '.venv')
    samples = snapshot(root / '.data' / 'clones')
    models = snapshot(root / '.data' / 'models')

    executable = runtime.install(root)

    assert len(created) == 1
    assert runtime.ENVIRONMENT.fullmatch(created[0].name)
    assert executable.is_relative_to(created[0])
    assert runtime.selected_python(root) == executable
    assert snapshot(root / '.venv') == legacy
    assert snapshot(root / '.data' / 'clones') == samples
    assert snapshot(root / '.data' / 'models') == models
    assert all(Path(command[0]).is_relative_to(created[0]) for command in commands)
    assert any(command[1:4] == ['-m', 'pip', 'install'] for command in commands)
    assert commands[-3][1:] == ['-m', 'pip', 'check']


@pytest.mark.parametrize('interrupted', [False, True], ids=['pip-file-lock', 'keyboard-interrupt'])
def test_failed_upgrade_keeps_old_runtime_pointer_and_retry_uses_fresh_directory(studio, monkeypatch, interrupted):
    root, created, commands = studio
    previous = runtime.install(root)
    previous_pointer = pointer_path(root).read_bytes()
    previous_files = snapshot(created[0])
    legacy = snapshot(root / '.venv')
    samples = snapshot(root / '.data' / 'clones')
    models = snapshot(root / '.data' / 'models')
    # A changed dependency set requires a fresh environment, even when the old
    # selected interpreter is still serving an existing Studio process.
    (root / 'requirements.txt').write_text('fastapi==0.116.0\n', encoding='utf-8')
    original_run = runtime._run

    def failed_pip(command, command_root, log=None):
        if list(command[1:4]) == ['-m', 'pip', 'install']:
            if interrupted:
                raise KeyboardInterrupt()
            raise subprocess.CalledProcessError(1, command, stderr='WinError 32: file is in use')
        return original_run(command, command_root, log)

    monkeypatch.setattr(runtime, '_run', failed_pip)
    expected = KeyboardInterrupt if interrupted else subprocess.CalledProcessError
    with pytest.raises(expected):
        runtime.install(root)

    failed_environment = created[-1]
    assert failed_environment != created[0]
    assert failed_environment.is_dir()
    assert pointer_path(root).read_bytes() == previous_pointer
    assert previous.is_file()
    assert snapshot(created[0]) == previous_files
    assert snapshot(root / '.venv') == legacy
    assert snapshot(root / '.data' / 'clones') == samples
    assert snapshot(root / '.data' / 'models') == models
    with pytest.raises(RuntimeError, match='install_clone_ai'):
        runtime.selected_python(root)

    monkeypatch.setattr(runtime, '_run', original_run)
    retry = runtime.install(root)

    assert len(created) == 3
    assert len(set(created)) == 3
    assert retry.is_relative_to(created[-1])
    assert runtime.selected_python(root) == retry
    assert failed_environment.is_dir()
    assert snapshot(created[0]) == previous_files
    assert snapshot(root / '.venv') == legacy
    assert snapshot(root / '.data' / 'clones') == samples
    assert snapshot(root / '.data' / 'models') == models


def test_ready_runtime_is_validated_and_reused_without_installing_packages(studio):
    root, created, commands = studio
    executable = runtime.install(root)
    pointer = pointer_path(root).read_bytes()
    installed = snapshot(created[0])
    commands.clear()

    assert runtime.install(root) == executable

    assert len(created) == 1
    assert pointer_path(root).read_bytes() == pointer
    assert snapshot(created[0]) == installed
    assert len(commands) == 3
    assert commands[0][1:] == ['-m', 'pip', 'check']
    assert all(command[0] == str(executable) for command in commands)
    assert all('install' not in command for command in commands)
    assert not any('prepare_clone_model.py' in command for command in commands)


def test_failed_validation_replaces_runtime_without_repairing_previous_packages(studio, monkeypatch):
    root, created, commands = studio
    previous = runtime.install(root)
    previous_files = snapshot(created[0])
    original_run = runtime._run

    def broken_previous(command, command_root, log=None):
        if Path(command[0]) == previous:
            assert list(command[1:]) == ['-m', 'pip', 'check']
            raise subprocess.CalledProcessError(1, command)
        return original_run(command, command_root, log)

    monkeypatch.setattr(runtime, '_run', broken_previous)
    replacement = runtime.install(root)

    assert len(created) == 2
    assert replacement != previous
    assert runtime.selected_python(root) == replacement
    assert snapshot(created[0]) == previous_files


def test_second_real_installer_process_is_rejected_and_lock_is_released(studio):
    root, _, _ = studio
    child_code = '''
import sys
import clone_runtime
try:
    with clone_runtime.installer_lock(sys.argv[1]):
        print('unexpectedly acquired lock')
        sys.exit(2)
except RuntimeError as exc:
    print(str(exc))
    sys.exit(0)
'''
    with runtime.installer_lock(root):
        child = subprocess.run(
            [sys.executable, '-c', child_code, str(root)],
            cwd=Path(runtime.__file__).parent, capture_output=True, text=True, timeout=15,
        )
        assert child.returncode == 0, child.stdout + child.stderr
        assert 'bo cai nhan ban khac' in child.stdout

    # A persistent lock file is fine; a completed/crashed installer must not
    # leave a stale "busy" flag that prevents the next real attempt.
    with runtime.installer_lock(root):
        pass


@pytest.mark.parametrize('environment', ['../outside', '/outside', '.venv', '.venv-clone-not-a-uuid'])
def test_runtime_pointer_cannot_select_arbitrary_environment(studio, environment):
    root, _, _ = studio
    folder = root / '.data' / 'runtime'
    folder.mkdir(parents=True)
    pointer_path(root).write_text(json.dumps({
        'schema': 1, 'environment': environment,
        'fingerprint': runtime.dependency_fingerprint(root),
    }), encoding='utf-8')

    with pytest.raises(RuntimeError, match='install_clone_ai'):
        runtime.selected_python(root)


def test_incomplete_environment_is_not_selected_and_serve_does_not_install(studio):
    root, created, commands = studio
    pending = root / '.venv-clone-123456789abc'
    pending.mkdir()

    with pytest.raises(RuntimeError, match='install_clone_ai'):
        runtime.serve(root)

    assert created == []
    assert commands == []


def test_serve_launches_full_app_under_exact_selected_interpreter_without_pip(studio):
    root, _, commands = studio
    selected = runtime.install(root)
    pointer = pointer_path(root).read_bytes()
    commands.clear()

    assert runtime.serve(root) == 0

    assert commands == [[str(selected), '-m', 'uvicorn', 'app:app', '--host',
                         '127.0.0.1', '--port', '8090', '--no-access-log']]
    assert pointer_path(root).read_bytes() == pointer


def test_one_click_launch_installs_then_reuses_runtime_and_stops_on_install_failure(studio, monkeypatch):
    root, created, commands = studio

    assert runtime.launch(root) == 0

    selected = runtime.selected_python(root)
    pointer = pointer_path(root).read_bytes()
    assert len(created) == 1
    assert any(command[1:4] == ['-m', 'pip', 'install'] for command in commands)
    assert commands[-1] == [str(selected), '-X', 'utf8', 'open_studio.py']
    assert all(command[0] == str(selected) for command in commands)
    commands.clear()

    assert runtime.launch(root) == 0

    assert len(created) == 1
    assert pointer_path(root).read_bytes() == pointer
    assert commands[-1] == [str(selected), '-X', 'utf8', 'open_studio.py']
    assert len(commands) == 4  # Validate three times, then serve; no pip mutation.
    assert all(command[1:4] != ['-m', 'pip', 'install'] for command in commands)
    assert not any('prepare_clone_model.py' in command for command in commands)
    commands.clear()

    def failed_install(root):
        raise RuntimeError('Installation did not finish')

    monkeypatch.setattr(runtime, 'install', failed_install)
    with pytest.raises(RuntimeError, match='Installation did not finish'):
        runtime.launch(root)

    assert commands == []  # No server/browser subprocess after installation failure.
    assert pointer_path(root).read_bytes() == pointer


def test_legacy_cpu_fingerprint_and_pointer_remain_compatible(studio):
    root, created, commands = studio
    digest = hashlib.sha256(b'hmong-clone-cpu-runtime-v1\0')
    for name in ('requirements.txt', 'requirements-cosy.txt'):
        digest.update(name.encode() + b'\0' + (root / name).read_bytes())
    digest.update(json.dumps(runtime.TORCH).encode())
    assert runtime.dependency_fingerprint(root) == digest.hexdigest()

    selected = runtime.install(root)
    record = json.loads(pointer_path(root).read_text(encoding='utf-8'))
    record.pop('profile')  # Runtime records shipped before GPU support.
    pointer_path(root).write_text(json.dumps(record), encoding='utf-8')
    previous = pointer_path(root).read_bytes()
    commands.clear()

    assert runtime.selected_python(root) == selected
    assert runtime.launch(root) == 0
    assert len(created) == 1
    assert pointer_path(root).read_bytes() == previous
    assert all(command[1:4] != ['-m', 'pip', 'install'] for command in commands)


def test_gpu_profile_is_isolated_validated_and_reused_by_normal_launcher(studio):
    root, created, commands = studio
    cpu = runtime.install(root)
    previous = snapshot(created[0])
    commands.clear()

    assert runtime.launch(root, profile='cu124') == 0

    gpu = runtime.selected_python(root)
    assert gpu != cpu
    assert snapshot(created[0]) == previous
    assert len(created) == 2
    record = json.loads(pointer_path(root).read_text(encoding='utf-8'))
    assert record['profile'] == 'cu124'
    assert record['fingerprint'] == runtime.dependency_fingerprint(root, 'cu124')
    assert record['fingerprint'] != runtime.dependency_fingerprint(root)
    torch_install = next(command for command in commands if '--index-url' in command)
    assert torch_install[-1] == 'https://download.pytorch.org/whl/cu124'
    assert all(command[0] == str(gpu) for command in commands)
    cuda_checks = [index for index, command in enumerate(commands) if runtime.CUDA_CHECK in command]
    model_download = next(index for index, command in enumerate(commands) if 'prepare_clone_model.py' in command)
    assert len(cuda_checks) == 2
    assert cuda_checks[0] < model_download < cuda_checks[1]
    assert 'torch.cuda.is_available()' in runtime.CUDA_CHECK
    assert 'torch.cuda.synchronize()' in runtime.CUDA_CHECK
    assert commands[-1] == [str(gpu), '-X', 'utf8', 'open_studio.py']

    pointer = pointer_path(root).read_bytes()
    commands.clear()
    assert runtime.launch(root) == 0
    assert runtime.selected_python(root) == gpu
    assert pointer_path(root).read_bytes() == pointer
    assert len(created) == 2
    assert any(runtime.CUDA_CHECK in command for command in commands)
    assert all(command[1:4] != ['-m', 'pip', 'install'] for command in commands)
    assert all(command[0] == str(gpu) for command in commands)


def test_missing_cuda_driver_keeps_cpu_runtime_selected_and_skips_model_download(studio, monkeypatch):
    root, created, commands = studio
    cpu = runtime.install(root)
    previous_pointer = pointer_path(root).read_bytes()
    previous_files = snapshot(created[0])
    original_run = runtime._run
    commands.clear()

    def no_cuda(command, command_root, log=None):
        if runtime.CUDA_CHECK in command:
            raise subprocess.CalledProcessError(1, command)
        return original_run(command, command_root, log)

    monkeypatch.setattr(runtime, '_run', no_cuda)
    with pytest.raises(subprocess.CalledProcessError):
        runtime.launch(root, profile='cu124')

    assert len(created) == 2
    assert pointer_path(root).read_bytes() == previous_pointer
    assert runtime.selected_python(root) == cpu
    assert snapshot(created[0]) == previous_files
    assert not any('prepare_clone_model.py' in command for command in commands)
    assert not any('open_studio.py' in command for command in commands)


def test_gpu_failure_at_final_validation_does_not_promote_runtime(studio, monkeypatch):
    root, created, commands = studio
    cpu = runtime.install(root)
    previous_pointer = pointer_path(root).read_bytes()
    original_run = runtime._run
    cuda_checks = 0

    def late_cuda_failure(command, command_root, log=None):
        nonlocal cuda_checks
        if runtime.CUDA_CHECK in command:
            cuda_checks += 1
            if cuda_checks == 2:
                raise subprocess.CalledProcessError(1, command)
        return original_run(command, command_root, log)

    monkeypatch.setattr(runtime, '_run', late_cuda_failure)
    with pytest.raises(subprocess.CalledProcessError):
        runtime.install(root, profile='cu124')

    assert cuda_checks == 2
    assert pointer_path(root).read_bytes() == previous_pointer
    assert runtime.selected_python(root) == cpu


def test_changed_dependencies_retain_gpu_profile_without_mutating_old_environment(studio):
    root, created, commands = studio
    gpu = runtime.install(root, profile='cu124')
    previous_files = snapshot(created[0])
    (root / 'requirements.txt').write_text('fastapi==0.116.0\n', encoding='utf-8')
    commands.clear()

    replacement = runtime.install(root)

    assert replacement != gpu
    assert snapshot(created[0]) == previous_files
    assert len(created) == 2
    assert runtime.selected_python(root) == replacement
    assert json.loads(pointer_path(root).read_text(encoding='utf-8'))['profile'] == 'cu124'
    assert next(command for command in commands if '--index-url' in command)[-1] == 'https://download.pytorch.org/whl/cu124'


@pytest.mark.parametrize('profile', ['cuda', 'cu128', None, [], {}])
def test_runtime_pointer_with_unknown_profile_is_not_selected(studio, profile):
    root, _, _ = studio
    runtime.install(root)
    record = json.loads(pointer_path(root).read_text(encoding='utf-8'))
    record['profile'] = profile
    pointer_path(root).write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(RuntimeError, match='install_clone_ai'):
        runtime.selected_python(root)


def test_runtime_profile_cannot_be_changed_without_matching_fingerprint(studio):
    root, created, commands = studio
    runtime.install(root)
    record = json.loads(pointer_path(root).read_text(encoding='utf-8'))
    record['profile'] = 'cu124'
    pointer_path(root).write_text(json.dumps(record), encoding='utf-8')

    with pytest.raises(RuntimeError, match='install_clone_ai'):
        runtime.selected_python(root)


def test_invalid_requested_profile_is_rejected_before_creating_an_environment(studio):
    root, created, commands = studio

    with pytest.raises(ValueError, match='khong duoc ho tro'):
        runtime.install(root, profile='cu128')

    assert created == []
    assert commands == []
    assert not pointer_path(root).exists()
