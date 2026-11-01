"""Catalog readiness reflects complete runtimes/models without exposing references."""
import json

import pytest

import app
import fast_multilingual
import native_transcript
import qwen_backend
from test_reference_voices_api import reference_catalog, KOREAN
from test_standalone_api import studio, sine_wave  # noqa: F401


@pytest.mark.parametrize('custom_voice_ready', [False, True])
def test_all_nine_qwen_presets_remain_visible_and_use_complete_backend_readiness(studio, monkeypatch, custom_voice_ready):
    client, data = studio
    for name in ('qwen', 'qwen_clone'):
        (data / 'models' / (name + '.ready')).write_text('stale marker alone is insufficient')
    calls = []

    def ready(directory, engine='qwen'):
        calls.append((directory, engine))
        return custom_voice_ready if engine == 'qwen' else False

    monkeypatch.setattr(qwen_backend, 'is_ready', ready)
    config = client.get('/api/config').json()
    assert config['version'] == '1.13.0'
    assert config['models']['qwen'] is custom_voice_ready
    assert config['models']['qwen_clone'] is False
    rows = [v for v in client.get('/api/voices').json()['voices'] if v['engine'] == 'qwen']
    assert len(rows) == 9
    assert all(v['ready'] is custom_voice_ready for v in rows)
    if not custom_voice_ready:
        assert all('CustomVoice' in v['missing_reason'] and 'runtime Qwen' in v['missing_reason'] for v in rows)
        assert all('TAI_GIONG_QUOC_TE.bat' not in v['missing_reason'] for v in rows)
    assert {engine for directory, engine in calls if directory == data} == {'qwen', 'qwen_clone'}


@pytest.mark.parametrize(('supplied_text', 'asr_ready', 'expected'), [
    ('Private reference words.', False, True),
    ('', False, False),
    ('   ', True, True),
    ('Private reference words.', True, True),
])
def test_omni_requires_asr_only_for_reference_without_supplied_transcript(reference_catalog, monkeypatch, supplied_text, asr_ready, expected):
    client, data, root, _ = reference_catalog
    manifest = root / 'manifest.json'
    document = json.loads(manifest.read_text())
    next(v for v in document['voices'] if v['id'] == KOREAN)['transcript'] = supplied_text
    manifest.write_text(json.dumps(document))
    monkeypatch.setattr(fast_multilingual, 'is_ready', lambda data, device=None, family='omnivoice': family == 'omnivoice')
    monkeypatch.setattr(native_transcript, 'asr_ready', lambda data: asr_ready)
    config = client.get('/api/config').json()
    assert config['native_reference_transcription_ready'] is asr_ready
    voice = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == KOREAN)
    assert voice['requires_reference_transcription'] is (not bool(supplied_text.strip()))
    assert voice['ready_native'] is expected and voice['ready'] is expected
    assert not voice['ready_voxcpm_native']
    assert not {'transcript', 'original_audio', 'reference_audio', 'reference_sha256'} & voice.keys()
    assert str(root) not in json.dumps(voice)
    if supplied_text.strip():
        assert supplied_text not in json.dumps(voice)
    if not expected:
        assert 'nhận dạng' in voice['missing_reason']


def test_native_voxcpm_without_transcript_does_not_require_asr(reference_catalog, monkeypatch):
    client, _, root, _ = reference_catalog
    manifest = root / 'manifest.json'
    document = json.loads(manifest.read_text())
    next(v for v in document['voices'] if v['id'] == KOREAN)['transcript'] = ''
    manifest.write_text(json.dumps(document))
    monkeypatch.setattr(fast_multilingual, 'is_ready', lambda *args, **kwargs: True)
    monkeypatch.setattr(native_transcript, 'asr_ready', lambda data: False)
    voice = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == KOREAN)
    assert voice['requires_reference_transcription']
    assert voice['ready'] and voice['ready_voxcpm_native']
    assert not voice['ready_native']


def test_uploaded_reference_readiness_checks_file_and_never_exposes_private_transcript(studio, monkeypatch):
    client, data = studio
    ident = 'd' * 32
    record = {'id': ident, 'engine': 'voxcpm', 'category': 'cloned', 'name': 'Uploaded sample',
              'languages': ['fr'], 'language': 'fr', 'transcript': 'Private uploaded reference text.'}
    (data / 'voices' / (ident + '.json')).write_text(json.dumps(record))
    sample = data / 'voices' / (ident + '.wav')
    sample.write_bytes(sine_wave())
    monkeypatch.setattr(fast_multilingual, 'is_ready', lambda data, device=None, family='omnivoice': family == 'omnivoice')
    monkeypatch.setattr(native_transcript, 'asr_ready', lambda data: False)
    voice = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == ident)
    assert voice['has_sample'] and voice['ready_native']
    assert voice['requires_reference_transcription'] is False
    assert 'transcript' not in voice and record['transcript'] not in json.dumps(voice)
    sample.unlink()
    voice = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == ident)
    assert not voice['has_sample'] and not voice['ready']


@pytest.mark.parametrize('supplied_text', ['', 'Private reference words.'])
def test_direct_omni_post_rejects_missing_asr_before_queue_unless_reference_has_text(reference_catalog, monkeypatch, supplied_text):
    client, data, root, submit = reference_catalog
    manifest = root / 'manifest.json'
    document = json.loads(manifest.read_text())
    next(v for v in document['voices'] if v['id'] == KOREAN)['transcript'] = supplied_text
    manifest.write_text(json.dumps(document))
    monkeypatch.setattr(fast_multilingual, 'is_ready', lambda data, device=None, family='omnivoice': family == 'omnivoice')
    monkeypatch.setattr(native_transcript, 'asr_ready', lambda data: False)
    response = client.post('/api/speech', json={
        'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.',
        'international_backend': 'omnivoice', 'international_device': 'cpu',
    })
    if supplied_text:
        assert response.status_code == 202, response.text
        submit.assert_called_once()
        assert len(list((data / 'jobs').glob('*.json'))) == 1
        assert supplied_text not in response.text
    else:
        assert response.status_code == 503, response.text
        assert 'nhận dạng lời mẫu' in response.json()['detail']
        assert '1.12.2' in response.json()['detail']
        submit.assert_not_called()
        assert not list((data / 'jobs').glob('*.json'))
    assert str(root) not in response.text and 'transcript' not in response.json()


def test_direct_omni_post_accepts_uploaded_reference_text_without_asr(studio, monkeypatch):
    from unittest.mock import Mock
    client, data = studio
    ident = 'e' * 32
    text = 'Private uploaded reference words.'
    record = {'id': ident, 'engine': 'voxcpm', 'category': 'cloned', 'name': 'Uploaded sample',
              'languages': ['fr'], 'language': 'fr', 'transcript': text}
    (data / 'voices' / (ident + '.json')).write_text(json.dumps(record))
    (data / 'voices' / (ident + '.wav')).write_bytes(sine_wave())
    submit = Mock()
    monkeypatch.setattr(app.executor, 'submit', submit)
    monkeypatch.setattr(fast_multilingual, 'is_ready', lambda data, device=None, family='omnivoice': family == 'omnivoice')
    monkeypatch.setattr(native_transcript, 'asr_ready', lambda data: pytest.fail('Supplied reference text must not require ASR'))
    response = client.post('/api/speech', json={
        'voice_id': ident, 'language': 'fr', 'text': 'Bonjour.',
        'international_backend': 'omnivoice', 'international_device': 'cpu',
    })
    assert response.status_code == 202, response.text
    assert response.json()['voice_id'] == ident
    assert response.json()['language'] == 'fr'
    assert text not in response.text and 'transcript' not in response.json()
    submit.assert_called_once()
