"""A model receipt or an edited Vocos config cannot authorize Python loading."""
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import urllib.request

import pytest

import cloning_engine as engine
import model_files
import setup_voice


@pytest.fixture
def pinned_files(tmp_path, monkeypatch):
    root = tmp_path / 'official-copy'
    records = {}
    contents = {}
    for index, relative in enumerate(model_files.MODEL_FILES):
        data = ('official fixture ' + str(index)).encode()
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        records[relative] = {
            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'url': 'https://huggingface.co/example/model/resolve/' + 'a' * 40 + '/' + relative,
        }
        contents[relative] = data
    monkeypatch.setattr(model_files, 'PINNED_MODELS', records)
    monkeypatch.setattr(setup_voice, 'PINNED_MODELS', records)
    monkeypatch.setattr(model_files, '_integrity_cache', {})
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path / 'data'))
    settings = {'checkpoint': str(root / model_files.MODEL_FILES[0]),
                'vocab': str(root / model_files.MODEL_FILES[1]),
                'vocoder': str(root / 'vocos'), 'model': 'F5TTS_Base', 'device': 'cpu'}
    return root, settings, records, contents


def test_release_files_are_verified_without_local_receipt_and_cached(pinned_files, monkeypatch):
    root, settings, _, _ = pinned_files
    hash_file = Mock(wraps=model_files._sha256)
    monkeypatch.setattr(model_files, '_sha256', hash_file)
    first = model_files.verify_models(root)
    assert model_files.verify_model_paths(settings) == first
    assert model_files.verify_models(root) == first
    assert hash_file.call_count == 4
    # A corrupt local receipt is ignored; release-owned records are authoritative.
    (root / 'verified-models.json').write_text('{not even JSON')
    assert model_files.verify_models(root) == first
    assert hash_file.call_count == 4


def test_forged_local_manifest_cannot_allow_changed_config(pinned_files):
    root, _, records, _ = pinned_files
    config = root / 'vocos/config.yaml'
    changed = b'x' * config.stat().st_size
    config.write_bytes(changed)
    forged = {key: dict(value) for key, value in records.items()}
    forged['vocos/config.yaml']['sha256'] = hashlib.sha256(changed).hexdigest()
    (root / 'verified-models.json').write_text(json.dumps({'files': forged}))
    with pytest.raises(model_files.EngineError, match='vocos/config.yaml'):
        model_files.verify_models(root)


@pytest.mark.parametrize('relative', model_files.MODEL_FILES)
@pytest.mark.parametrize('damage', ['missing', 'wrong-size', 'wrong-hash'])
def test_missing_or_changed_release_file_is_refused(pinned_files, relative, damage):
    root, settings, _, _ = pinned_files
    model_files.verify_models(root)
    path = root / relative
    if damage == 'missing':
        path.unlink()
    elif damage == 'wrong-size':
        path.write_bytes(b'broken')
    else:
        before = path.stat()
        path.write_bytes(b'x' * before.st_size)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(model_files.EngineError, match='SHA-256'):
        model_files.verify_model_paths(settings)


def test_override_paths_are_checked_instead_of_default_directory(pinned_files, tmp_path):
    root, settings, _, _ = pinned_files
    # Existing official files may be stored in unrelated, user-selected folders.
    moved_checkpoint = tmp_path / 'separate weights.safetensors'
    moved_vocab = tmp_path / 'separate vocab.txt'
    Path(settings['checkpoint']).replace(moved_checkpoint)
    Path(settings['vocab']).replace(moved_vocab)
    settings.update(checkpoint=str(moved_checkpoint), vocab=str(moved_vocab))
    assert model_files.verify_model_paths(settings)
    with pytest.raises(model_files.EngineError):
        model_files.verify_models(root)
    moved_vocab.write_bytes(b'not the release vocabulary')
    with pytest.raises(model_files.EngineError, match='vocab.txt'):
        model_files.verify_model_paths(settings)


def test_mutation_during_hashing_is_not_cached(pinned_files, monkeypatch):
    root, _, _, _ = pinned_files
    original = model_files._sha256

    def changing_hash(path):
        value = original(path)
        if path.name == 'pytorch_model.bin':
            config = root / 'vocos/config.yaml'
            config.write_bytes(b'x' * config.stat().st_size)
        return value

    monkeypatch.setattr(model_files, '_sha256', changing_hash)
    with pytest.raises(model_files.EngineError, match='thay đổi'):
        model_files.verify_models(root)
    assert not model_files._integrity_cache


@pytest.mark.parametrize('after_first_load', [False, True])
def test_corrupt_config_never_reaches_f5_constructor(pinned_files, monkeypatch, after_first_load):
    root, settings, _, _ = pinned_files
    factory = Mock(return_value=SimpleNamespace(device='cpu'))
    monkeypatch.setitem(__import__('sys').modules, 'torch', Mock())
    monkeypatch.setitem(__import__('sys').modules, 'f5_tts', Mock())
    monkeypatch.setitem(__import__('sys').modules, 'f5_tts.api', SimpleNamespace(F5TTS=factory))
    monkeypatch.setattr(engine, '_model', None)
    monkeypatch.setattr(engine, '_model_key', None)
    if after_first_load:
        assert engine._load_model(settings) is factory.return_value
    config = root / 'vocos/config.yaml'
    before = config.stat()
    config.write_bytes(b'x' * before.st_size)
    os.utime(config, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(engine.CloningError, match='vocos/config.yaml'):
        engine._load_model(settings)
    assert factory.call_count == int(after_first_load)


def test_installer_uses_only_release_urls_not_remote_metadata(pinned_files, tmp_path, monkeypatch):
    _, _, records, contents = pinned_files
    target = tmp_path / 'fresh-install'
    downloaded = []
    by_url = {records[relative]['url']: data for relative, data in contents.items()}

    def open_url(request, timeout):
        downloaded.append(request.full_url)
        return io.BytesIO(by_url[request.full_url])

    monkeypatch.setattr(setup_voice.urllib.request, 'build_opener', lambda *args: SimpleNamespace(open=open_url))
    setup_voice.install(target)
    assert downloaded == list(by_url)
    assert model_files.verify_models(target)
    receipt = json.loads((target / 'verified-models.json').read_text())
    assert receipt['release'] == setup_voice.MODEL_RELEASE
    assert all('/resolve/' in url and '/api/' not in url and '/main/' not in url for url in downloaded)


def test_existing_pinned_files_are_reused_without_network(pinned_files, monkeypatch):
    root, _, _, _ = pinned_files
    opener = Mock(side_effect=AssertionError('must not access network'))
    monkeypatch.setattr(setup_voice.urllib.request, 'build_opener', opener)
    setup_voice.install(root)
    opener.assert_not_called()


@pytest.mark.parametrize('body', [b'wrong-size', b'fail'])
def test_wrong_download_never_replaces_destination_or_leaves_partial(tmp_path, monkeypatch, body):
    destination = tmp_path / 'config.yaml'
    destination.write_bytes(b'old')
    monkeypatch.setattr(setup_voice.urllib.request, 'build_opener',
                        lambda *args: SimpleNamespace(open=lambda *args, **kwargs: io.BytesIO(body)))
    with pytest.raises(setup_voice.SetupError):
        setup_voice._download('https://huggingface.co/fixed', destination, 4, hashlib.sha256(b'good').hexdigest())
    assert destination.read_bytes() == b'old'
    assert not list(tmp_path.glob('*.part'))


def test_https_cannot_be_downgraded_during_model_download(tmp_path):
    with pytest.raises(setup_voice.SetupError, match='HTTPS'):
        setup_voice._download('http://huggingface.co/fixed', tmp_path / 'file', 1, '0' * 64)
    handler = setup_voice._HTTPSRedirectHandler()
    with pytest.raises(setup_voice.SetupError, match='HTTPS'):
        handler.redirect_request(urllib.request.Request('https://huggingface.co/fixed'),
                                 None, 302, 'redirect', {}, 'http://cdn.example/file')
