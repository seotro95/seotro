"""Pinned public-model installer transport; synthetic files and mocked HTTP only."""
import hashlib
import io
import json
from pathlib import Path
import stat
import zipfile

import pytest
import public_modelpack as pack


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(name, data):
    return {'name': name, 'size': len(data), 'sha256': digest(data)}


@pytest.fixture
def modelpack(monkeypatch):
    files = {'config.json': b'{"architecture":"voxcpm2","dtype":"bfloat16"}',
             'model.safetensors': bytes(range(256))*12,
             'audiovae.safetensors': b'audio model fixture', 'tokenizer.json': b'{}',
             'LICENSE-APACHE-2.0.txt': b'Apache License fixture'}
    provenance = json.dumps({'repository': pack.REPOSITORY, 'revision': pack.REVISION,
                            'license': 'apache-2.0', 'weights_and_config_unchanged': True,
                            'files': [record(name, data) for name, data in files.items()]}, sort_keys=True).encode()
    files['MODEL_PROVENANCE.json'] = provenance
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in files.items():
            archive.writestr(pack.FOLDER+'/'+name, data)
    raw = output.getvalue()
    assets, parts = {}, []
    for index, start in enumerate(range(0, len(raw), 1000), 1):
        name = 'model.zip.part'+f'{index:03d}'
        assets[name] = raw[start:start+1000]
        parts.append(record(name, assets[name]))
    manifest = {'format': 'voice-studio-modelpack-chunks-v1', 'repository': pack.REPOSITORY,
                'revision': pack.REVISION, 'license': 'apache-2.0', 'unpacked_root': pack.FOLDER,
                'archive': {**record('model.zip', raw), 'chunks': parts}}
    assets[pack.MANIFEST_NAME] = json.dumps(manifest, sort_keys=True).encode()
    monkeypatch.setattr(pack, 'MANIFEST_SHA256', digest(assets[pack.MANIFEST_NAME]))
    monkeypatch.setattr(pack, 'PROVENANCE_SHA256', digest(provenance))
    requested = []
    def urlopen(request, timeout):
        assert request.full_url.startswith(pack.RELEASE_URL)
        name = request.full_url[len(pack.RELEASE_URL):]
        requested.append(name)
        return io.BytesIO(assets[name])
    monkeypatch.setattr(pack.urllib.request, 'urlopen', urlopen)
    return assets, manifest, files, requested


def test_download_extract_validate_and_second_run_is_offline(tmp_path, modelpack, monkeypatch):
    assets, manifest, files, requested = modelpack
    source = pack.ensure_model_source(tmp_path)
    assert source == tmp_path/'models'/pack.FOLDER
    assert {file.name: file.read_bytes() for file in source.iterdir()} == files
    assert len(requested) == 1+len(manifest['archive']['chunks'])
    assert not (source.parent/'model.zip').exists()
    monkeypatch.setattr(pack.urllib.request, 'urlopen', lambda *args, **kwargs: pytest.fail('network on second run'))
    assert pack.ensure_model_source(tmp_path) == source


def test_valid_cached_parts_are_reused_and_corrupt_part_is_replaced(tmp_path, modelpack):
    assets, manifest, _, requested = modelpack
    cache = pack._prepare_cache(tmp_path)
    for name, data in assets.items():
        (cache/name).write_bytes(data)
    corrupted = manifest['archive']['chunks'][1]['name']
    (cache/corrupted).write_bytes(b'wrong length')
    pack.ensure_model_source(tmp_path)
    assert requested == [corrupted]


def test_failed_download_leaves_valid_parts_for_retry_and_no_model(tmp_path, modelpack):
    assets, manifest, _, _ = modelpack
    name = manifest['archive']['chunks'][1]['name']
    original = assets[name]
    assets[name] = b'x'*len(original)
    with pytest.raises(ValueError, match='SHA256'):
        pack.ensure_model_source(tmp_path)
    cache = pack._cache(tmp_path)
    assert (cache/manifest['archive']['chunks'][0]['name']).is_file()
    assert not (cache/name).exists()
    assert not list(cache.glob('*.partial-*'))
    assert not (tmp_path/'models'/pack.FOLDER).exists()
    assets[name] = original
    assert pack.ensure_model_source(tmp_path).is_dir()


def test_manifest_pin_rejects_modified_metadata_before_parts(tmp_path, modelpack):
    assets, _, _, requested = modelpack
    assets[pack.MANIFEST_NAME] += b' '
    with pytest.raises(ValueError, match='SHA256'):
        pack.ensure_model_source(tmp_path)
    assert requested == [pack.MANIFEST_NAME]


def test_existing_source_refuses_changed_file_and_changed_provenance(tmp_path, modelpack):
    _, _, files, _ = modelpack
    source = pack.ensure_model_source(tmp_path)
    weight = source/'model.safetensors'
    weight.write_bytes(b'x'*len(files[weight.name]))
    with pytest.raises(ValueError, match='SHA256'):
        pack.ensure_model_source(tmp_path)
    metadata = json.loads((source/'MODEL_PROVENANCE.json').read_text())
    for item in metadata['files']:
        if item['name'] == weight.name:item['sha256'] = digest(weight.read_bytes())
    (source/'MODEL_PROVENANCE.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='nguồn model'):
        pack.ensure_model_source(tmp_path)


def test_whole_archive_hash_is_also_checked(tmp_path, modelpack):
    assets, manifest, _, _ = modelpack
    cache = pack._prepare_cache(tmp_path)
    for name, data in assets.items():(cache/name).write_bytes(data)
    manifest['archive']['sha256'] = '0'*64
    with pytest.raises(ValueError, match='đầy đủ'):
        pack._verify_archive(cache, manifest['archive'])


@pytest.mark.parametrize('filename,mode', [('../escape', None), ('voxcpm2-original/../../escape', None),
    ('voxcpm2-original/C:escape', None), ('voxcpm2-original/CON.txt', None),
    ('voxcpm2-original/link', stat.S_IFLNK|0o777)])
def test_unsafe_zip_names_or_links_never_escape(tmp_path, modelpack, filename, mode):
    _, manifest, _, _ = modelpack
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        entry = zipfile.ZipInfo(filename)
        if mode is not None:entry.external_attr = mode << 16
        archive.writestr(entry, b'bad path')
    raw = output.getvalue()
    cache = pack._prepare_cache(tmp_path)
    (cache/'unsafe.zip.part001').write_bytes(raw)
    manifest['archive'] = {**record('unsafe.zip', raw), 'chunks': [record('unsafe.zip.part001', raw)]}
    with pytest.raises(ValueError):
        pack._extract(cache, manifest, tmp_path/'models')
    assert not (tmp_path/'escape').exists()
    assert not (tmp_path/'models'/pack.FOLDER).exists()
    assert not list((tmp_path/'models').glob('.voxcpm2-extract-*'))


def test_zip_crc_is_checked_during_extraction(tmp_path, modelpack):
    assets, manifest, files, _ = modelpack
    raw = bytearray(b''.join(assets[part['name']] for part in manifest['archive']['chunks']))
    where = raw.index(files['model.safetensors'])
    raw[where+100] ^= 1
    cache = pack._prepare_cache(tmp_path)
    name = 'bad-crc.zip.part001'
    (cache/name).write_bytes(raw)
    manifest['archive'] = {**record('bad-crc.zip', raw), 'chunks': [record(name, raw)]}
    with pytest.raises(zipfile.BadZipFile, match='CRC'):
        pack._extract(cache, manifest, tmp_path/'models')
    assert not (tmp_path/'models'/pack.FOLDER).exists()


def test_cleanup_only_after_success_and_only_known_parts(tmp_path, modelpack):
    _, manifest, _, _ = modelpack
    pack.ensure_model_source(tmp_path)
    cache = pack._cache(tmp_path)
    other = cache/'unrelated-personal-file.txt';other.write_text('preserve')
    assert pack.cleanup_download_parts(tmp_path) is False
    assert all((cache/part['name']).exists() for part in manifest['archive']['chunks'])
    marker = tmp_path/'models/voxcpm.ready'
    marker.write_text(json.dumps({'repository': pack.REPOSITORY, 'revision': pack.REVISION, 'verified_thai_frames': 2399}))
    assert pack.cleanup_download_parts(tmp_path) is False
    marker.write_text(json.dumps({'repository': pack.REPOSITORY, 'revision': pack.REVISION, 'verified_thai_frames': 2400}))
    assert pack.cleanup_download_parts(tmp_path) is True
    assert all(not (cache/part['name']).exists() for part in manifest['archive']['chunks'])
    assert other.read_text() == 'preserve'
    assert (cache/pack.MANIFEST_NAME).exists()
    assert (tmp_path/'models'/pack.FOLDER/'model.safetensors').exists()


def test_cache_symlinks_are_rejected(tmp_path):
    outside = tmp_path/'outside';outside.mkdir()
    (tmp_path/'models').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='liên kết'):
        pack._prepare_cache(tmp_path)
    assert not (outside/'_public-modelpack').exists()
