"""Check privacy boundaries and launcher configuration without downloading models."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest

PACKAGING = Path(__file__).resolve().parents[1] / 'packaging'
sys.path.insert(0, str(PACKAGING))
spec = importlib.util.spec_from_file_location('build_hmong_windows', PACKAGING / 'build_hmong_windows.py')
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


def source_fixture(root):
    root.mkdir()
    for name in ('app.py', 'worker.py', 'hmong_engine.py', 'hmong_f5.py', 'hmong_reference.py', 'hmong_assets.py',
                 'prepare_hmong.py', 'hmong_launcher.py', 'studio_variant.py'):
        (root / name).write_text('# app\n', encoding='utf-8')
    for name in ('static/app.js', 'assets/hmong/female.wav', 'assets/hmong/male.wav',
                 'assets/hmong/source-female.mp3', 'assets/hmong/source-male.mp3',
                 'assets/hmong/voices.json', '.data/voices/personal.wav',
                 '.data/models/private.bin', '.venv/Lib/private.py', 'assets/private.wav', '.env'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')


def test_source_copy_includes_only_approved_assets(tmp_path):
    source = tmp_path / 'source'
    source_fixture(source)
    output = tmp_path / 'output'
    packaging.copy_source(output, source)
    assert (output / 'static/app.js').read_bytes() == b'fixture'
    assert (output / 'assets/hmong/female.wav').is_file()
    assert (output / 'assets/hmong/male.wav').is_file()
    assert (output / 'assets/hmong/source-female.mp3').is_file()
    assert (output / 'assets/hmong/source-male.mp3').is_file()
    assert not (output / '.data').exists()
    assert not (output / '.venv').exists()
    assert not (output / '.env').exists()
    assert not (output / 'assets/private.wav').exists()


def test_archive_has_valid_crc_and_matching_sha256(tmp_path):
    root = tmp_path / 'Voice-Studio-Hmong-1.1.0'
    root.mkdir()
    (root / 'hello.txt').write_bytes(b'relocatable')
    archive = tmp_path / 'bundle.zip'
    digest = packaging.archive_package(root, archive)
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert Path(str(archive) + '.sha256').read_text().strip() == digest + '  bundle.zip'
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert bundle.read(root.name + '/hello.txt') == b'relocatable'


def test_environment_and_batch_keep_data_in_hmong_package(tmp_path, monkeypatch):
    monkeypatch.setenv('PYTHONHOME', 'unrelated-python')
    monkeypatch.setenv('PYTHONPATH', 'unrelated-packages')
    monkeypatch.setenv('HF_HUB_OFFLINE', '1')
    environment = packaging.build_environment(tmp_path, offline=False)
    assert 'PYTHONHOME' not in environment and 'PYTHONPATH' not in environment
    assert 'HF_HUB_OFFLINE' not in environment
    assert environment['VOICE_STUDIO_VARIANT'] == 'hmong'
    assert environment['VOICE_STUDIO_DATA_DIR'] == str(tmp_path / 'voice-studio-hmong/.data')
    assert environment['HMOOB_MODEL_DIR'] == str(tmp_path / 'voice-studio-hmong/.data/models')
    assert packaging.build_environment(tmp_path, offline=True)['HF_HUB_OFFLINE'] == '1'
    packaging.write_launcher(tmp_path)
    batch = (tmp_path / 'MO_VOICE_STUDIO_HMONG.bat').read_bytes()
    assert b'\r\n' in batch
    assert b'VOICE_STUDIO_VARIANT=hmong' in batch
    assert b'VOICE_STUDIO_DATA_DIR=%~dp0voice-studio-hmong\\.data' in batch
    assert b'hmong_launcher.py" %*' in batch


def test_source_copy_refuses_linked_assets(tmp_path):
    source = tmp_path / 'source'
    source_fixture(source)
    try:
        (source / 'assets/hmong/external').symlink_to(source / '.env')
    except OSError:
        pytest.skip('Symlink permission unavailable on this host')
    with pytest.raises(ValueError, match='Linked application assets'):
        packaging.copy_source(tmp_path / 'output', source)
