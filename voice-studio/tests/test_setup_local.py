"""Installation must target the interpreter that will actually launch the app."""
import sys

import pytest

import setup_local


def configured(monkeypatch, root, arguments):
    monkeypatch.setattr(setup_local, 'BASE', root)
    monkeypatch.setattr(setup_local.shutil, 'which', lambda name: '/tools/' + name)
    monkeypatch.setattr(sys, 'argv', ['setup_local.py', *arguments])
    monkeypatch.setattr(sys, 'version_info', (3, 12, 0))
    monkeypatch.delenv('VOICE_STUDIO_VENV', raising=False)
    commands = []
    monkeypatch.setattr(setup_local, 'run', lambda command: commands.append([str(part) for part in command]))
    return commands


def test_existing_local_environment_is_reused_and_vietnamese_prepared_once(tmp_path, monkeypatch):
    root = tmp_path / 'voice-studio'
    executable = root / '.venv' / ('Scripts/python.exe' if setup_local.os.name == 'nt' else 'bin/python')
    executable.parent.mkdir(parents=True)
    executable.touch()
    data = root / '.data' / 'voices' / 'keep.wav'
    data.parent.mkdir(parents=True)
    data.write_bytes(b'personal sample')
    commands = configured(monkeypatch, root, [])
    setup_local.main()
    assert all(command[0] == str(executable) for command in commands)
    assert not any('venv' in command for command in commands)
    preparations = [command for command in commands if str(root / 'prepare_models.py') in command]
    assert preparations == [[str(executable), str(root / 'prepare_models.py'), 'vi']]
    assert not any('torch==2.6.0' in command for command in commands)
    assert data.read_bytes() == b'personal sample'


def test_optional_portable_installs_into_its_runtime_and_does_not_repeat_vi(tmp_path, monkeypatch):
    root = tmp_path / 'portable' / 'voice-studio'
    root.mkdir(parents=True)
    executable = root.parent / 'runtime' / 'python.exe'
    executable.parent.mkdir()
    executable.touch()
    commands = configured(monkeypatch, root, ['--international', '--portable'])
    monkeypatch.setattr(sys, 'executable', str(executable))
    setup_local.main()
    assert all(command[0] == str(executable) for command in commands)
    assert not any('venv' in command for command in commands)
    assert [command[-1] for command in commands if str(root / 'prepare_models.py') in command] == ['qwen', 'qwen_clone']
    assert not (root / '.venv').exists()


def test_portable_flag_cannot_install_into_unrelated_system_python(tmp_path, monkeypatch):
    commands = configured(monkeypatch, tmp_path / 'voice-studio', ['--international', '--portable'])
    with pytest.raises(RuntimeError, match='runtime/python.exe'):
        setup_local.main()
    assert commands == []
