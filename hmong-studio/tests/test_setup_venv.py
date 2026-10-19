import pytest
import setup_venv


def test_rebuild_preserves_old_environment_and_user_audio_then_reuses(tmp_path):
    root = tmp_path / 'Hmong Studio nữ'
    old = root / '.venv'
    old.mkdir(parents=True)
    (old / 'old-environment.txt').write_text('preserve me')
    data = root / '.data'
    data.mkdir()
    sample = data / 'reference.mp3'
    sample.write_bytes(b'user-audio-unchanged')
    python = setup_venv.ensure_venv(root)
    assert setup_venv.interpreter_info(python)
    backups = list(root.glob('.venv-backup-*'))
    assert len(backups) == 1
    assert (backups[0] / 'old-environment.txt').read_text() == 'preserve me'
    assert sample.read_bytes() == b'user-audio-unchanged'
    marker = python.parent / 'reuse-marker'
    marker.write_text('keep')
    assert setup_venv.ensure_venv(root) == python
    assert marker.read_text() == 'keep'
    assert len(list(root.glob('.venv-backup-*'))) == 1


def test_python315_is_rejected_before_touching_existing_environment(tmp_path, monkeypatch):
    old = tmp_path / '.venv'
    old.mkdir()
    marker = old / 'keep.txt'
    marker.write_text('original')
    monkeypatch.setattr(setup_venv.sys, 'version_info', (3, 15, 0))
    with pytest.raises(RuntimeError, match='3.10-3.12'):
        setup_venv.ensure_venv(tmp_path)
    assert marker.read_text() == 'original'
    assert not list(tmp_path.glob('.venv-backup-*'))
