import importlib.util
from pathlib import Path

import pytest


def builder():
    file = Path(__file__).resolve().parents[1] / 'build_windows.py'
    spec = importlib.util.spec_from_file_location('portable_builder', file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_materialize_cache_retains_snapshot_contents_without_blob_dependency(tmp_path):
    module = builder()
    hub = tmp_path / 'hub'
    repo = hub / 'models--test--fixture'
    blob = repo / 'blobs/weights'
    blob.parent.mkdir(parents=True)
    blob.write_bytes(b'verified model fixture')
    snapshot = repo / 'snapshots/commit/model.onnx'
    snapshot.parent.mkdir(parents=True)
    try:
        snapshot.symlink_to(blob)
    except OSError:
        pytest.skip('Windows runner does not permit symlinks; ordinary snapshots are also supported')
    module.materialize_cache(hub)
    assert not snapshot.is_symlink()
    assert snapshot.read_bytes() == b'verified model fixture'
    assert not blob.parent.exists()


def test_materialize_cache_preserves_ordinary_windows_snapshot_files(tmp_path):
    hub = tmp_path / 'hub'
    snapshot = hub / 'models--test--fixture/snapshots/commit/model.onnx'
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b'ordinary windows snapshot')
    builder().materialize_cache(hub)
    assert snapshot.read_bytes() == b'ordinary windows snapshot'


def test_clean_qa_preserves_models_and_only_cleans_owned_data_root(tmp_path):
    data = tmp_path / 'new-build/app/.data'
    models = data / 'models'
    models.mkdir(parents=True)
    (models / 'vieneu_nano.ready').write_text('prepared')
    (data / 'voices').mkdir()
    (data / 'voices/qa.wav').write_bytes(b'qa reference')
    outside = tmp_path / 'user-recording.wav'
    outside.write_bytes(b'never touched')
    builder().clean_qa(data)
    assert (models / 'vieneu_nano.ready').read_text() == 'prepared'
    assert not list((data / 'voices').iterdir())
    assert outside.read_bytes() == b'never touched'


def test_portable_launcher_bat_always_uses_bundled_python(tmp_path):
    module = builder()
    module.write_launchers(tmp_path)
    content = (tmp_path / 'MO_TOOL.bat').read_text()
    assert 'runtime\\python.exe' in content and 'portable_launcher.py' in content
    assert 'pip install' not in content and 'py -3.12' not in content
    assert 'No Python' not in content  # No dependency checks or installers are launched.
