import hashlib
import json

import pytest

from verify_release import ReleaseIntegrityError, verify_package


def inventory(root, path='app/main.py', content=b'print("local")\n'):
    program = root / path
    program.parent.mkdir(parents=True, exist_ok=True)
    program.write_bytes(content)
    records = {path: {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}}
    manifest = root / 'release-files.json'
    manifest.write_text(json.dumps({'version': 1, 'files': records}))
    return program, manifest


def test_exact_files_validate_without_reading_private_data(tmp_path):
    inventory(tmp_path)
    (tmp_path / '.data').mkdir()
    (tmp_path / '.data/private.txt').write_text('Private script not in release')
    assert verify_package(tmp_path) == 1


@pytest.mark.parametrize('change', ['same_size', 'missing', 'truncated'])
def test_changed_file_is_rejected(tmp_path, change):
    path, _ = inventory(tmp_path)
    if change == 'missing':
        path.unlink()
    elif change == 'truncated':
        path.write_bytes(b'')
    else:
        path.write_bytes(b'X' * path.stat().st_size)
    with pytest.raises(ReleaseIntegrityError):
        verify_package(tmp_path)


@pytest.mark.parametrize('path', ['../outside.py', '/outside.py', 'C:/outside.py',
                                  'app\\outside.py', '.data/private.txt', '.venv/python.exe'])
def test_inventory_cannot_read_outside_release_or_private_data(tmp_path, path):
    _, manifest = inventory(tmp_path)
    content = json.loads(manifest.read_text())
    content['files'] = {path: next(iter(content['files'].values()))}
    manifest.write_text(json.dumps(content))
    with pytest.raises(ReleaseIntegrityError):
        verify_package(tmp_path)


def test_symlink_to_matching_file_is_rejected(tmp_path):
    path, _ = inventory(tmp_path)
    real = tmp_path / 'redirected.py'
    path.rename(real)
    path.symlink_to(real)
    with pytest.raises(ReleaseIntegrityError):
        verify_package(tmp_path)


def test_missing_manifest_does_not_prepare_environment(tmp_path, monkeypatch):
    import bootstrap
    from unittest.mock import Mock
    monkeypatch.setattr(bootstrap, '__file__', str(tmp_path / 'app/bootstrap.py'))
    prepare = Mock()
    monkeypatch.setattr(bootstrap, 'prepare', prepare)
    assert bootstrap.main([]) == 1
    prepare.assert_not_called()
