"""Private reference catalog validation uses generated audio, never user assets."""
import hashlib
import json
import math
import struct
import wave

import pytest

from voice_library import catalog_voices, resolve_reference, ReferenceValidationError


IDENT = 'a' * 32


def write_wav(path, seconds=4, rate=24000):
    path.parent.mkdir(parents=True, exist_ok=True)
    period = b''.join(struct.pack('<h', round(4000 * math.sin(2 * math.pi * index / 24))) for index in range(24))
    frames = round(seconds * rate)
    samples = (period * ((frames + 23) // 24))[:frames * 2]
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        audio.writeframes(samples)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def private_pack(tmp_path, monkeypatch):
    root = tmp_path / 'private library é'
    root.mkdir()
    reference = root / 'voices' / (IDENT + '.wav')
    digest = write_wav(reference)
    record = {'id': IDENT, 'name': 'Synthetic reference', 'language': 'en-US',
              'reference_audio': f'voices/{IDENT}.wav', 'reference_sha256': digest,
              'reference_frames': 96000, 'reference_sample_rate': 24000, 'duration': 4,
              'transcript': 'A private synthetic test transcript.', 'original_audio': 'originals/private.mp3'}
    manifest = root / 'manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'voices': [record]}), encoding='utf-8')
    monkeypatch.setenv('VOICE_STUDIO_VOICE_LIBRARY', str(root))
    return root, manifest, reference, record


def save_manifest(path, records):
    path.write_text(json.dumps({'schema_version': 1, 'voices': records}), encoding='utf-8')


def test_default_catalog_is_stable_readonly_and_does_not_expose_private_metadata(private_pack, tmp_path):
    root, _, reference, record = private_pack
    public = catalog_voices()
    assert public == catalog_voices()
    voice = public[0]
    assert voice['id'] == IDENT and voice['category'] == 'reference'
    assert voice['readonly'] is True and voice['is_default'] is True
    assert voice['engine'] == 'vieneu' and voice['languages'] == ['en-US', 'en-GB']
    assert voice['native_language'] == 'en' and voice['has_sample'] is True
    assert voice['sample_url'] == f'/api/voices/{IDENT}/sample' and voice['duration'] == 4
    assert not {'transcript', 'reference_audio', 'original_audio', 'reference_sha256'} & voice.keys()
    assert str(root) not in json.dumps(voice)
    path, metadata = resolve_reference(IDENT, tmp_path / 'data')
    assert path == reference.resolve() and metadata['transcript'] == record['transcript']


@pytest.mark.parametrize('language', ['ko', 'ru', 'ja', 'fr', 'es', 'th'])
def test_international_defaults_use_voxcpm_with_correct_native_language(private_pack, language):
    _, manifest, _, record = private_pack
    save_manifest(manifest, [{**record, 'language': language}])
    voice = catalog_voices()[0]
    assert voice['engine'] == 'voxcpm' and voice['languages'] == [language]
    assert voice['native_language'] == language


def test_missing_reference_remains_visible_without_private_path(private_pack, tmp_path):
    root, _, reference, _ = private_pack
    reference.unlink()
    voice = catalog_voices()[0]
    assert voice['id'] == IDENT and not voice['has_sample'] and voice['missing_reason']
    assert str(root) not in voice['missing_reason']
    with pytest.raises(FileNotFoundError):
        resolve_reference(IDENT, tmp_path / 'data')


def test_tampered_reference_is_visible_but_cannot_be_used(private_pack, tmp_path):
    _, _, reference, _ = private_pack
    content = bytearray(reference.read_bytes()); content[-1] ^= 1; reference.write_bytes(content)
    voice = catalog_voices()[0]
    assert not voice['has_sample'] and 'SHA256' in voice['missing_reason']
    with pytest.raises(ReferenceValidationError, match='SHA256'):
        resolve_reference(IDENT, tmp_path / 'data')


@pytest.mark.parametrize('relative', ['../outside.wav', '/outside.wav', 'C:/outside.wav', r'voices\outside.wav'])
def test_manifest_reference_cannot_escape_root(private_pack, tmp_path, relative):
    _, manifest, _, record = private_pack
    save_manifest(manifest, [{**record, 'reference_audio': relative}])
    assert not catalog_voices()[0]['has_sample']
    with pytest.raises(ReferenceValidationError):
        resolve_reference(IDENT, tmp_path / 'data')


def test_symlink_escape_cannot_be_used(private_pack, tmp_path):
    _, _, reference, _ = private_pack
    outside = tmp_path / 'outside.wav'; write_wav(outside)
    reference.unlink()
    try:
        reference.symlink_to(outside)
    except OSError:
        pytest.skip('Symlinks are unavailable in this test environment')
    assert not catalog_voices()[0]['has_sample']
    with pytest.raises(ReferenceValidationError):
        resolve_reference(IDENT, tmp_path / 'data')


def test_invalid_catalog_language_engine_or_identifier_is_not_exposed(private_pack):
    _, manifest, _, record = private_pack
    save_manifest(manifest, [{**record, 'language': 'xx'}, {**record, 'engine': 'qwen_clone'},
                             {**record, 'id': '../private'}, {**record, 'language': []},
                             {**record, 'engine': []}])
    assert catalog_voices() == []


@pytest.mark.parametrize('voice_id', ['../secret', 'A' * 32, 'a' * 31, 'a' * 33])
def test_invalid_requested_identifiers_are_rejected(private_pack, tmp_path, voice_id):
    with pytest.raises(ReferenceValidationError):
        resolve_reference(voice_id, tmp_path / 'data')


def test_editable_legacy_clone_is_supported_without_pack_hash(private_pack, tmp_path):
    data = tmp_path / 'data'; ident = 'b' * 32
    reference = data / 'voices' / (ident + '.wav'); write_wav(reference)
    (reference.with_suffix('.json')).write_text(json.dumps({'id': ident, 'name': 'Editable',
        'language': 'vi', 'languages': ['vi'], 'transcript': 'Editable reference.'}))
    path, metadata = resolve_reference(ident, data)
    assert path == reference.resolve() and metadata['engine'] == 'vieneu'
    assert not metadata['readonly'] and not metadata['is_default']
    assert metadata['transcript'] == 'Editable reference.'


def test_pcm_duration_and_truncation_are_checked(private_pack, tmp_path):
    _, manifest, reference, record = private_pack
    digest = write_wav(reference, seconds=2)
    save_manifest(manifest, [{**record, 'reference_sha256': digest}])
    assert not catalog_voices()[0]['has_sample']
    with pytest.raises(ReferenceValidationError, match='3 đến 30'):
        resolve_reference(IDENT, tmp_path / 'data')
    digest = write_wav(reference)
    reference.write_bytes(reference.read_bytes()[:-12])
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    save_manifest(manifest, [{**record, 'reference_sha256': digest}])
    with pytest.raises(ReferenceValidationError, match='thiếu hoặc hỏng'):
        resolve_reference(IDENT, tmp_path / 'data')


def test_missing_pack_is_empty_and_unknown_reference_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_VOICE_LIBRARY', str(tmp_path / 'missing'))
    assert catalog_voices() == []
    with pytest.raises(FileNotFoundError):
        resolve_reference(IDENT, tmp_path / 'data')


def test_raw_filesystem_errors_do_not_expose_private_paths(private_pack, monkeypatch):
    import voice_library
    root, _, _, _ = private_pack
    def missing(*args):
        raise FileNotFoundError(2, 'Missing', str(root / 'private.wav'))
    monkeypatch.setattr(voice_library, '_pack_reference', missing)
    voice = catalog_voices()[0]
    assert not voice['has_sample'] and str(root) not in voice['missing_reason']
