"""Exercise runtime isolation and promotion without downloading AI dependencies."""
import json
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
