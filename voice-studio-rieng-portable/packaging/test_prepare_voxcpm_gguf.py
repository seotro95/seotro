"""Preparation verifies provenance and preserves a previous native install."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


spec = importlib.util.spec_from_file_location('prepare_voxcpm_gguf_test_target',
                                             Path(__file__).with_name('prepare_voxcpm_gguf.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / 'public-original'
    root.mkdir()
    values = {'model.safetensors': b'original model tensors', 'audiovae.pth': b'original VAE tensors',
              'config.json': b'{"architecture":"voxcpm2","dtype":"bfloat16"}',
              'tokenizer.json': b'{}', 'tokenizer_config.json': b'{}', 'special_tokens_map.json': b'{}',
              'README.md': b'Public model card', 'LICENSE-APACHE-2.0.txt': b'Public model license'}
    files = []
    for name, value in values.items():
        (root / name).write_bytes(value)
        files.append({'name': name, 'size': len(value), 'sha256': hashlib.sha256(value).hexdigest()})
    provenance = {'repository': prepare.MODEL_REPOSITORY, 'revision': prepare.MODEL_REVISION, 'files': files}
    path = root / 'MODEL_PROVENANCE.json'
    path.write_text(json.dumps(provenance))
    monkeypatch.setattr(prepare, 'PROVENANCE_SHA256', prepare.sha256(path))
    return root


@pytest.fixture
def converter(tmp_path):
    folder = tmp_path / 'native-cpu'
    folder.mkdir()
    tool = folder / 'audiocpp_gguf'
    tool.write_bytes(b'locally built pinned converter')
    manifest = {'revision': prepare.NATIVE_REVISION, 'families': ['omnivoice', 'voxcpm2'],
                'device': 'cpu', 'sha256': {}, 'tools_sha256': {tool.name: prepare.sha256(tool)}}
    (folder / 'native-build.json').write_text(json.dumps(manifest))
    return tool


@pytest.fixture
def fake_conversion(monkeypatch):
    calls = []
    def vae(source, destination):
        destination.write_bytes(b'exact synthetic VAE conversion')
        return {'tensor_count': 1, 'sha256': prepare.sha256(destination), 'tensor_roundtrip_exact': True}
    def run(command, **kwargs):
        calls.append(command)
        if '--output' in command:
            Path(command[command.index('--output') + 1]).write_bytes(b'GGUFsynthetic quantized model')
    monkeypatch.setattr(prepare, 'convert_vae', vae)
    monkeypatch.setattr(prepare.subprocess, 'run', run)
    return calls


def test_verified_source_requires_exact_files_and_untouched_originals(source):
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    root, files = prepare.verify_source(source)
    assert root == source and files['model.safetensors']['sha256'] == prepare.sha256(source / 'model.safetensors')
    assert before == {p.name: p.read_bytes() for p in source.iterdir()}
    (source / 'audiovae.pth').write_bytes(b'corrupt replacement')
    with pytest.raises(ValueError, match='SHA256/size mismatch'):
        prepare.verify_source(source)


def test_wrong_provenance_is_not_accepted_as_local_checkpoint(source):
    (source / 'MODEL_PROVENANCE.json').write_text('{"repository":"unverified"}')
    with pytest.raises(ValueError, match='provenance SHA256'):
        prepare.verify_source(source)


def test_converter_hash_and_native_families_must_match(converter):
    prepare.verify_converter(converter)
    converter.write_bytes(b'a different binary')
    with pytest.raises(ValueError, match='pinned VoxCPM2'):
        prepare.verify_converter(converter)


def test_success_marker_matches_gguf_and_reuses_verified_output(source, converter, fake_conversion, tmp_path):
    data = tmp_path / 'studio-data'
    source_before = {p.name: p.read_bytes() for p in source.iterdir()}
    record = prepare.prepare(source, converter, data)
    model = data / 'models' / prepare.MODEL_DIRECTORY / prepare.MODEL_FILENAME
    marker = data / 'models' / prepare.MARKER_NAME
    assert model.read_bytes().startswith(b'GGUF')
    assert json.loads(marker.read_text()) == record
    assert record['sha256'] == prepare.sha256(model)
    assert record['audio_vae_safetensors']['tensor_roundtrip_exact']
    assert record['original_weights_and_config_unchanged']
    assert record['target_30x_guaranteed'] is False
    for name in ('README.md', 'LICENSE-APACHE-2.0.txt', 'MODEL_PROVENANCE.json'):
        assert (model.parent / name).read_bytes() == (source / name).read_bytes()
    command = fake_conversion[0]
    assert command[command.index('--type') + 1] == 'q8_0'
    assert command[command.index('--family') + 1] == 'voxcpm2'
    assert any(value.startswith('weights=') for value in command)
    assert any(value.startswith('audiovae_weights=') for value in command)
    assert source_before == {p.name: p.read_bytes() for p in source.iterdir()}
    assert prepare.prepare(source, converter, data)['already_prepared'] is True
    assert len(fake_conversion) == 2  # convert + inspect, never repeated for a ready model.
    assert not list((data / 'models').glob('voxcpm-native-convert-*'))


def test_failed_converter_keeps_previous_model_and_marker(source, converter, fake_conversion, tmp_path, monkeypatch):
    data = tmp_path / 'studio'
    old_model = data / 'models' / prepare.MODEL_DIRECTORY / prepare.MODEL_FILENAME
    old_model.parent.mkdir(parents=True)
    old_model.write_bytes(b'previous model')
    old_marker = data / 'models' / prepare.MARKER_NAME
    old_marker.write_bytes(b'previous marker')
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(prepare.subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        prepare.prepare(source, converter, data)
    assert old_model.read_bytes() == b'previous model'
    assert old_marker.read_bytes() == b'previous marker'


def test_marker_commit_failure_restores_model_and_old_marker(tmp_path, monkeypatch):
    model = tmp_path / 'models/native/model.gguf'
    marker = tmp_path / 'models/model.ready'
    model.parent.mkdir(parents=True)
    model.write_bytes(b'previous model')
    marker.write_bytes(b'previous marker')
    license_file = model.parent / 'LICENSE-APACHE-2.0.txt'
    license_file.write_bytes(b'previous license')
    converted = tmp_path / 'converted.gguf'
    converted.write_bytes(b'GGUFnew')
    original_replace = prepare.os.replace
    def fail_marker(source, destination):
        if Path(destination) == marker:
            raise OSError('simulated full disk during marker commit')
        original_replace(source, destination)
    monkeypatch.setattr(prepare.os, 'replace', fail_marker)
    with pytest.raises(OSError, match='full disk'):
        prepare._install(converted, model, marker, {'sha256': prepare.sha256(converted)},
                         {'LICENSE-APACHE-2.0.txt': b'new public license'})
    assert model.read_bytes() == b'previous model'
    assert marker.read_bytes() == b'previous marker'
    assert license_file.read_bytes() == b'previous license'
    assert not list(tmp_path.rglob('*.tmp')) and not list(tmp_path.rglob('*.backup'))


def test_derived_vae_roundtrip_is_tensor_exact_and_weights_only(tmp_path, monkeypatch):
    torch = pytest.importorskip('torch')
    safetensors = pytest.importorskip('safetensors.torch')
    checkpoint = tmp_path / 'audiovae.pth'
    tensors = {'a': torch.arange(8, dtype=torch.float32).reshape(2, 4), 'b': torch.ones(3, dtype=torch.int64)}
    torch.save({'state_dict': tensors}, checkpoint)
    before = checkpoint.read_bytes()
    real_load = torch.load
    seen = []
    def checked_load(*args, **kwargs):
        seen.append(kwargs)
        return real_load(*args, **kwargs)
    monkeypatch.setattr(torch, 'load', checked_load)
    destination = tmp_path / 'derived.safetensors'
    report = prepare.convert_vae(checkpoint, destination)
    restored = safetensors.load_file(str(destination))
    assert report['tensor_count'] == 2 and report['tensor_roundtrip_exact']
    assert seen == [{'map_location': 'cpu', 'weights_only': True}]
    assert checkpoint.read_bytes() == before
    for name, tensor in tensors.items():
        assert restored[name].dtype == tensor.dtype and torch.equal(restored[name], tensor)
