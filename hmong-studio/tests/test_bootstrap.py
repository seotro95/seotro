from pathlib import Path
import subprocess
import sys

import pytest

import bootstrap


def info(version, executable='python.exe', command=None, bits=64):
    return {'version': version, 'executable': executable, 'command': command or (executable,), 'bits': bits}


def test_32bit_python_is_not_supported():
    assert not bootstrap.supported(info((3, 12, 10), bits=32))
    assert bootstrap.supported(info((3, 12, 10), bits=64))


def test_prefers_312_even_if_current_python_315(monkeypatch):
    commands = [('python315',), ('py', '-3.11'), ('py', '-3.12')]
    metadata = [info((3, 15, 0)), info((3, 11, 9)), info((3, 12, 10))]
    monkeypatch.setattr(bootstrap, 'interpreter_candidates', lambda: commands)
    monkeypatch.setattr(bootstrap, 'probe_python', lambda command: metadata[commands.index(command)])
    assert bootstrap.select_python()['version'] == (3, 12, 10)


def test_falls_back_to_supported_311_and_rejects_only_315(monkeypatch):
    monkeypatch.setattr(bootstrap, 'interpreter_candidates', lambda: [('python',)])
    monkeypatch.setattr(bootstrap, 'probe_python', lambda _: info((3, 11, 9)))
    assert bootstrap.select_python()['version'] == (3, 11, 9)
    monkeypatch.setattr(bootstrap, 'probe_python', lambda _: info((3, 15, 0)))
    with pytest.raises(bootstrap.BootstrapError, match='Python 3.12'):
        bootstrap.select_python()


def test_reuses_supported_existing_environment_without_external_interpreter(tmp_path, monkeypatch):
    folder = tmp_path / '.venv'
    folder.mkdir()
    monkeypatch.setattr(bootstrap, 'probe_python', lambda _: info((3, 10, 11)))
    monkeypatch.setattr(bootstrap, 'select_python', lambda: pytest.fail('should reuse existing venv'))
    assert bootstrap.prepare(tmp_path) == bootstrap.venv_python(folder)


def test_preserves_unsupported_venv_and_handles_space_in_path(tmp_path, monkeypatch):
    root = tmp_path / 'voi hmong'
    old = root / '.venv'
    old.mkdir(parents=True)
    (old / 'user-file.txt').write_text('keep this', encoding='utf-8')
    selected = info((3, 12, 10), command=('py', '-3.12'))
    monkeypatch.setattr(bootstrap, 'select_python', lambda: selected)
    reads = iter([info((3, 15, 0)), info((3, 12, 10))])
    monkeypatch.setattr(bootstrap, 'probe_python', lambda _: next(reads))
    calls = []
    def create(command, **kwargs):
        calls.append(command)
        Path(command[-1]).mkdir()
    monkeypatch.setattr(bootstrap.subprocess, 'run', create)
    assert bootstrap.prepare(root) == bootstrap.venv_python(old)
    assert calls == [['py', '-3.12', '-m', 'venv', str(old)]]
    backups = list(root.glob('.venv-backup-unsupported-*'))
    assert len(backups) == 1
    assert (backups[0] / 'user-file.txt').read_text() == 'keep this'


def test_check_only_and_missing_supported_python_do_not_touch_old_env(tmp_path, monkeypatch):
    old = tmp_path / '.venv'
    old.mkdir()
    (old / 'keep.txt').write_text('keep')
    monkeypatch.setattr(bootstrap, 'probe_python', lambda _: info((3, 15, 0)))
    monkeypatch.setattr(bootstrap, 'select_python', lambda: info((3, 12, 10)))
    bootstrap.prepare(tmp_path, check_only=True)
    assert (old / 'keep.txt').exists()
    assert not list(tmp_path.glob('.venv-backup-*'))
    def missing():
        raise bootstrap.BootstrapError(bootstrap.INSTALL_HELP)
    monkeypatch.setattr(bootstrap, 'select_python', missing)
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.prepare(tmp_path)
    assert (old / 'keep.txt').exists()


def test_backups_never_overwrite_and_failed_creation_keeps_user_files(tmp_path, monkeypatch):
    folder = tmp_path / '.venv'
    folder.mkdir()
    first = bootstrap.preserve_venv(folder)
    (first / 'keep.txt').write_text('first')
    folder.mkdir()
    second = bootstrap.preserve_venv(folder)
    assert first != second
    assert (first / 'keep.txt').read_text() == 'first'
    folder.mkdir()
    (folder / 'user.txt').write_text('second')
    monkeypatch.setattr(bootstrap, 'probe_python', lambda _: None)
    monkeypatch.setattr(bootstrap, 'select_python', lambda: info((3, 12, 10)))
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(bootstrap.subprocess, 'run', fail)
    with pytest.raises(bootstrap.BootstrapError, match='Khong tao duoc'):
        bootstrap.prepare(tmp_path)
    assert any((path / 'user.txt').exists() for path in tmp_path.glob('.venv-backup-*'))


def test_real_interpreter_probe_and_venv_creation_in_directory_with_spaces(tmp_path):
    if sys.version_info[:2] not in bootstrap.PREFERRED:
        pytest.skip('test runner requires supported Python')
    current = bootstrap.probe_python((sys.executable,))
    assert current['version'][:2] == sys.version_info[:2]
    root = tmp_path / 'Hmong Studio'
    root.mkdir()
    executable = bootstrap.prepare(root)
    assert executable.is_file()
    assert bootstrap.supported(bootstrap.probe_python((str(executable),)))
