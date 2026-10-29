"""Verify CUDA archive integrity and merging without a GPU or Windows driver."""
import hashlib
import io
from pathlib import Path
import zipfile

import pytest

import prepare_cuda


def archive_record(tmp_path, name, files):
    path = tmp_path / (name + '-archive.zip')
    with zipfile.ZipFile(path, 'w') as archive:
        for relative, contents in files.items():
            archive.writestr(name + '-archive/' + relative, contents)
    return path, {'name': name, 'path': path.name, 'size': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def test_component_merge_keeps_licenses_and_identical_shared_headers(tmp_path):
    first, one = archive_record(tmp_path, 'one', {'include/shared.h': 'shared', 'LICENSE': 'first license'})
    second, two = archive_record(tmp_path, 'two', {'include/shared.h': 'shared', 'bin/nvcc.exe': 'compiler', 'LICENSE': 'second license'})
    output = tmp_path / 'toolkit'
    prepare_cuda.merge_component(first, one, output)
    prepare_cuda.merge_component(second, two, output)
    assert (output / 'include/shared.h').read_text() == 'shared'
    assert (output / 'component-metadata/one/LICENSE').read_text() == 'first license'
    assert (output / 'component-metadata/two/LICENSE').read_text() == 'second license'


def test_conflicting_compiler_files_are_not_overwritten(tmp_path):
    first, one = archive_record(tmp_path, 'one', {'bin/nvcc.exe': 'first compiler'})
    second, two = archive_record(tmp_path, 'two', {'bin/nvcc.exe': 'changed compiler'})
    output = tmp_path / 'toolkit'
    prepare_cuda.merge_component(first, one, output)
    with pytest.raises(ValueError, match='Conflicting'):
        prepare_cuda.merge_component(second, two, output)
    assert (output / 'bin/nvcc.exe').read_text() == 'first compiler'


def test_corrupt_download_never_replaces_verified_archive(tmp_path):
    source, record = archive_record(tmp_path, 'one', {'bin/nvcc.exe': 'compiler'})
    directory = tmp_path / 'downloads'
    directory.mkdir()
    existing = directory / source.name
    existing.write_bytes(b'old incomplete download')
    with pytest.raises(ValueError, match='SHA256'):
        prepare_cuda.download(record, directory, opener=lambda *a, **k: io.BytesIO(b'corrupt'))
    assert existing.read_bytes() == b'old incomplete download'
    assert not list(directory.glob('*.tmp'))


@pytest.mark.parametrize('path', ('../escape', '/absolute', 'root-archive/../../escape', 'root-archive/back\\slash'))
def test_archive_paths_stay_inside_toolkit(tmp_path, path):
    archive = tmp_path / 'root-archive.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr(path, 'bad')
    with pytest.raises(ValueError, match='Unsafe'):
        prepare_cuda.merge_component(archive, {'name': 'root', 'path': archive.name}, tmp_path / 'toolkit')


def test_failed_preparation_has_no_partial_toolkit(tmp_path, monkeypatch):
    source, record = archive_record(tmp_path, 'one', {'bin/nvcc.exe': 'compiler'})
    monkeypatch.setattr(prepare_cuda, 'download', lambda *a: source)
    with pytest.raises(ValueError, match='incomplete'):
        prepare_cuda.prepare(tmp_path / 'toolkit', tmp_path / 'downloads', [record], ['include/cuda.h'])
    assert not (tmp_path / 'toolkit').exists()
    assert not list(tmp_path.glob('toolkit.*.tmp'))
