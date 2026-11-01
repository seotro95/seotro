"""Turbo variants reuse validated samples and preserve native-language jobs."""
import json
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import app
import voice_library as library
from test_voice_library import private_pack, save_manifest  # noqa: F401
from test_reference_voices_api import reference_catalog, default_voices  # noqa: F401
from test_standalone_api import studio  # noqa: F401


@pytest.mark.parametrize('language', sorted(library.CATALOG_LANGUAGES))
def test_variants_preserve_original_and_resolve_to_exact_same_audio(private_pack, tmp_path, language):
    root, manifest, reference, record = private_pack
    save_manifest(manifest, [{**record, 'language': language}])
    original, variant = library.catalog_voices()
    assert original['id'] == record['id']
    assert original['languages'] == (['en-US', 'en-GB'] if language.startswith('en-') else [language])
    assert variant['engine'] == 'vieneu' and variant['languages'] == ['vi', 'en-US', 'en-GB']
    assert variant['source_voice_id'] == original['id']
    assert variant['id'] == library.turbo_variant_id(original['id']) != original['id']
    assert variant['name'].endswith(' · Turbo Việt/Anh')
    assert variant['native_language'] == language.split('-')[0]
    path, metadata = library.resolve_reference(variant['id'], tmp_path / 'data')
    assert path == reference.resolve()
    assert metadata['engine'] == 'vieneu' and metadata['transcript'] == record['transcript']
    assert variant['readonly'] and variant['is_default'] and variant['has_sample']
    assert str(root) not in json.dumps(variant)
    assert not {'transcript', 'reference_audio', 'reference_sha256', 'original_audio'} & variant.keys()
    assert len(list(root.rglob('*.wav'))) == 1


@pytest.mark.parametrize('damage', ['missing', 'corrupt', 'escape'])
def test_variant_enforces_original_hash_and_containment(private_pack, tmp_path, damage):
    root, manifest, reference, record = private_pack
    if damage == 'missing':
        reference.unlink()
    elif damage == 'corrupt':
        reference.write_bytes(reference.read_bytes() + b'changed')
    else:
        save_manifest(manifest, [{**record, 'reference_audio': '../outside.wav'}])
    assert all(not voice['has_sample'] for voice in library.catalog_voices())
    with pytest.raises((FileNotFoundError, library.ReferenceValidationError)):
        library.resolve_reference(library.turbo_variant_id(record['id']), tmp_path / 'data')


@pytest.mark.parametrize('source', ['a' * 32, 'b' * 32, 'c' * 32])
@pytest.mark.parametrize('language', ['vi', 'en-US', 'en-GB'])
def test_turbo_variant_api_queues_reference_with_no_preset_fallback(reference_catalog, source, language):
    client, data, root, submit = reference_catalog
    (data / 'models' / 'vieneu.ready').touch()
    ident = library.turbo_variant_id(source)
    voice = default_voices(client)[ident]
    assert voice['ready'] and voice['engine'] == 'vieneu'
    assert client.get(f'/api/voices/{ident}/sample').content == (root / 'voices' / f'{source}.wav').read_bytes()
    assert client.delete(f'/api/voices/{ident}').status_code == 403
    response = client.post('/api/speech', json={'voice_id': ident, 'language': language, 'text': 'Hello. Xin chào.'})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['voice_id'] == ident and job['speaker'] is None and job['engine'] == 'vieneu'
    submit.assert_called_once_with(app.run_job, job['id'])
    assert not (data / 'voices' / f'{ident}.json').exists()


@pytest.mark.parametrize('language', ['ko', 'ru', 'ja', 'fr', 'es', 'th'])
def test_turbo_variant_never_claims_foreign_language_support(reference_catalog, language):
    client, data, _, submit = reference_catalog
    (data / 'models' / 'vieneu.ready').touch()
    ident = library.turbo_variant_id('b' * 32)
    response = client.post('/api/speech', json={'voice_id': ident, 'language': language, 'text': 'Example.'})
    assert response.status_code == 422
    submit.assert_not_called()


def test_worker_encodes_selected_variant_instead_of_a_stock_voice(reference_catalog, monkeypatch, tmp_path):
    import turbo_reference
    _, data, root, _ = reference_catalog
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(data))
    worker = importlib.import_module('worker')
    model = Mock()
    monkeypatch.setattr(worker, 'DATA', data)
    monkeypatch.setitem(sys.modules, 'local_vieneu', SimpleNamespace(LocalVieneu=Mock(return_value=model)))
    prepared = {'speaker_emb': object(), 'codes': object()}
    encode = Mock(return_value=prepared)
    monkeypatch.setattr(turbo_reference, 'prepared_turbo_voice', encode)
    ident = library.turbo_variant_id('b' * 32)
    synthesize = worker.load_synthesizer({'engine': 'vieneu', 'voice_id': ident, 'speaker': None,
                                        'quality': 'standard', 'nano_threads': 2})
    synthesize('Xin chào.', tmp_path / 'out.wav')
    assert encode.call_args.args[:3] == (model, (root/'voices'/('b'*32 + '.wav')).resolve(), data)
    model.infer.assert_called_once_with('Xin chào.', voice=prepared)
