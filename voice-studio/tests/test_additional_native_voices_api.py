"""Audio-only supplied presets and personal defaults retain their own identity."""
import importlib
import hashlib
import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app
import hmong_assets
from character_cast import validate_job_references, settings_for_cue


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    for folder in ('voices', 'jobs', 'parts', 'audio', 'models', 'videos'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'IS_HMONG', True)
    monkeypatch.setattr(app, 'PRESETS', hmong_assets.presets())
    monkeypatch.setattr(app, 'LANGUAGES', {**app.LANGUAGES, 'mww': 'Hmong'})
    monkeypatch.setattr(app, 'CORE_LANGUAGES', {'mww': 'Hmong'})
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    monkeypatch.setattr(app, 'model_ready', lambda engine: True)
    with TestClient(app.app) as client:
        monkeypatch.setattr(app.executor, 'submit', Mock())
        yield client, tmp_path


@pytest.mark.parametrize('ident', ['hmong-female-3', 'hmong-ngoc-huyen'])
@pytest.mark.parametrize('cast', [False, True])
def test_supplied_audio_only_presets_use_exact_wav_for_speech_and_cast(studio, monkeypatch, ident, cast):
    import numpy as np
    client, data = studio
    voice = next(item for item in client.get('/api/voices').json()['voices'] if item['id'] == ident)
    assert voice['engine'] == 'hmong_native' and voice['reference_conditioning'] == 'audio'
    payload = {'text': 'Tae-yong cov ntaub ntawv tus kheej.', 'voice_id': ident, 'language': 'mww'}
    if cast:
        payload.update(text='217\n00:06:07,200 --> 00:06:18,400\nTae-yong cov ntaub ntawv tus kheej.',
                       input_format='srt', voice_id='hmong-male',
                       character_voices={'visitor': ident}, cue_characters=['visitor'])
    result = client.post('/api/speech', json=payload)
    assert result.status_code == 202, result.text
    job = result.json()
    validate_job_references(job, data)
    selected = settings_for_cue(job, 0) if cast else job
    assert selected['speaker'] == selected['voice_id'] == ident
    assert selected['hmong_reference_fingerprint'] == hmong_assets.reference_fingerprint(ident)
    received = []
    class Engine:
        def set_progress_callback(self, callback):
            pass
        def synthesize(self, text, reference, words, **kwargs):
            received.append((reference, reference.read_bytes(), words))
            return np.full(2400, .1), 24000
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(data))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', data)
    monkeypatch.setattr(worker, '_hmong_native_instance', Engine())
    worker.load_synthesizer(selected)('Nyob zoo.', data / 'parts' / 'probe.wav')
    reference, _ = hmong_assets.reference(ident)
    assert received == [(reference, reference.read_bytes(), '')]
    assert client.get('/api/hmong/presets/' + ident + '/sample').content == hmong_assets.source(ident).read_bytes()


def test_new_presets_hidden_for_f5_without_inventing_hmong_words(monkeypatch):
    monkeypatch.setenv('HMOOB_BACKEND', 'f5')
    assert {voice['id'] for voice in hmong_assets.presets()} == {'hmong-male', 'hmong-female'}
    for ident in ('hmong-female-3', 'hmong-ngoc-huyen'):
        assert hmong_assets.reference(ident)[1] == ''


@pytest.mark.parametrize('ident', ['hmong-female-3', 'hmong-ngoc-huyen'])
def test_importing_actual_supplied_original_uses_verified_builtin_excerpt(studio, ident):
    client, _ = studio
    original = hmong_assets.source(ident)
    selected, _ = hmong_assets.reference(ident)
    response = client.post('/api/voices/clone', data={'name': 'Copy of supplied sample',
        'language': 'mww', 'consent': 'true'},
        files={'file': (original.name, original.read_bytes(), 'audio/mpeg')})
    assert response.status_code == 201, response.text
    voice = response.json()
    assert voice['automatic_reference'] is True and voice['known_preset'] == ident
    assert voice['transcript'] == '' and voice['reference_conditioning'] == 'audio'
    assert voice['source_sha256'] == hashlib.sha256(original.read_bytes()).hexdigest()
    sample = client.get('/api/voices/' + voice['id'] + '/sample')
    assert sample.status_code == 200 and sample.content == selected.read_bytes()


def test_preferred_personal_voice_persists_and_delete_guard_preserves_selection(studio):
    client, data = studio
    assert client.get('/api/config').json()['default_voice_id'] == 'hmong-female-3'
    reference, _ = hmong_assets.reference('hmong-female-3')
    response = client.post('/api/voices/clone', data={'name': 'My reference', 'language': 'mww',
        'consent': 'true'}, files={'file': ('external.wav', reference.read_bytes(), 'audio/wav')})
    assert response.status_code == 201, response.text
    ident = response.json()['id']
    changed = client.put('/api/voices/default', json={'voice_id': ident})
    assert changed.status_code == 200, changed.text
    assert changed.json()['default_voice_id'] == ident
    assert json.loads((data / 'voice-preferences.json').read_text())['voice_id'] == ident
    assert client.get('/api/config').json()['default_voice_id'] == ident
    job = client.post('/api/speech', json={'voice_id': ident, 'language': 'mww', 'text': 'Nyob zoo.'}).json()
    assert client.delete('/api/voices/' + ident).status_code == 409
    assert client.get('/api/config').json()['default_voice_id'] == ident
    saved = data / 'jobs' / (job['id'] + '.json')
    app.write_json(saved, {**job, 'status': 'done'})
    assert client.delete('/api/voices/' + ident).status_code == 204
    assert client.get('/api/config').json()['default_voice_id'] == 'hmong-female-3'


def test_invalid_default_never_replaces_existing_preference(studio):
    client, data = studio
    assert client.put('/api/voices/default', json={'voice_id': 'hmong-ngoc-huyen'}).status_code == 200
    original = (data / 'voice-preferences.json').read_bytes()
    assert client.put('/api/voices/default', json={'voice_id': 'unknown'}).status_code == 422
    assert (data / 'voice-preferences.json').read_bytes() == original
    assert client.get('/api/config').json()['default_voice_id'] == 'hmong-ngoc-huyen'


def test_speech_only_user_excerpt_keeps_original_and_generated_export_times(studio):
    client, data = studio
    source = '217\n00:06:07,200 --> 00:06:08,400\nTae-yong cov ntaub ntawv tus kheej'
    response = client.post('/api/speech', json={'text': source, 'input_format': 'srt',
        'subtitle_timing': False, 'voice_id': 'hmong-female-3', 'language': 'mww', 'max_minutes': 1})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['text'] == source and job['subtitle_timing'] is False
    assert client.get('/api/jobs/' + job['id'] + '/script.srt').status_code == 409
    generated = '1\n00:00:00,000 --> 00:00:02,400\nTae-yong cov ntaub ntawv tus kheej\n'
    (data / 'audio' / (job['id'] + '.srt')).write_text(generated)
    app.write_json(data / 'jobs' / (job['id'] + '.json'), {**job, 'status': 'done'})
    assert client.get('/api/jobs/' + job['id'] + '/script.srt').text == generated
    rejected = client.post('/api/speech', json={'text': source, 'input_format': 'srt',
        'subtitle_timing': False, 'voice_id': 'hmong-female-3', 'language': 'mww',
        'character_voices': {'visitor': 'hmong-ngoc-huyen'}, 'cue_characters': ['visitor']})
    assert rejected.status_code == 422 and 'giữ mốc' in rejected.json()['detail']
