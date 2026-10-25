"""Personal reference audio remains selected when its words are not Hmong."""
from unittest.mock import Mock
import importlib

import pytest
from fastapi.testclient import TestClient

import app
import hmong_assets
from character_cast import validate_job_references


@pytest.fixture
def native_studio(tmp_path, monkeypatch):
    for folder in ('jobs', 'parts', 'audio', 'voices', 'models', 'videos'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'IS_HMONG', True)
    monkeypatch.setattr(app, 'PRESETS', hmong_assets.presets())
    monkeypatch.setattr(app, 'LANGUAGES', {**app.LANGUAGES, 'mww': 'Hmong Trắng'})
    monkeypatch.setattr(app, 'CORE_LANGUAGES', {'mww': 'Hmong Trắng'})
    monkeypatch.setattr(app, 'active_hmong_engine', lambda: 'hmong_native')
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    monkeypatch.setattr(app, 'model_ready', lambda engine: True)
    with TestClient(app.app) as client:
        monkeypatch.setattr(app.executor, 'submit', Mock())
        yield client, tmp_path


def save_reference(client, *, transcript='', language='mww'):
    audio, _ = hmong_assets.reference('hmong-female')
    result = client.post('/api/voices/clone', data={
        'name': 'External voice', 'language': language,
        'consent': 'true', 'transcript': transcript,
    }, files={'file': ('external.wav', audio.read_bytes(), 'audio/wav')})
    assert result.status_code == 201, result.text
    return result.json()


@pytest.mark.parametrize('transcript', ['', 'Xin chào, tôi nói tiếng Việt.', 'こんにちは。你好。'])
def test_native_import_accepts_foreign_or_absent_words_and_binds_exact_custom_voice(native_studio, transcript):
    client, data = native_studio
    voice = save_reference(client, transcript=transcript)
    assert voice['languages'] == ['mww'] and voice['language'] == 'mww'
    assert voice['engine'] == 'hmong_native'
    assert voice['transcript'] == transcript
    assert voice['reference_conditioning'] == 'audio'
    assert voice['cross_language_reference'] is True
    assert client.get('/api/config').json()['cross_language_reference'] is True
    assert client.get(f"/api/voices/{voice['id']}/sample").content[:4] == b'RIFF'
    response = client.post('/api/speech', json={
        'text': 'Nyob zoo. Ua tsaug.', 'voice_id': voice['id'], 'language': 'mww'})
    assert response.status_code == 202, response.text
    job = response.json()
    snapshot = job['hmong_voice_snapshot']
    assert job['voice_id'] == snapshot['voice_id'] == voice['id']
    assert job['speaker'] is None and snapshot['speaker'] is None
    assert snapshot['reference_text'] == transcript
    assert snapshot['hmong_reference_fingerprint'] != hmong_assets.reference_fingerprint('hmong-female')
    validate_job_references(job, data)
    # Missing reference audio must stop rendering/resume, never select a preset.
    (data / 'voices' / (voice['id'] + '.wav')).unlink()
    with pytest.raises(ValueError, match='thay đổi|không còn'):
        validate_job_references(job, data)


def test_native_foreign_reference_available_to_character_cast(native_studio):
    client, data = native_studio
    voice = save_reference(client, transcript='Hello, this is my own voice.')
    response = client.post('/api/speech', json={
        'text': '1\n00:00:00,000 --> 00:00:04,000\nNyob zoo.',
        'input_format': 'srt', 'voice_id': 'hmong-male', 'language': 'mww',
        'character_voices': {'visitor': voice['id']}, 'cue_characters': ['visitor']})
    assert response.status_code == 202, response.text
    job = response.json()
    actor = job['character_cast']['voices']['visitor']
    assert actor['voice_id'] == voice['id'] and actor['speaker'] is None
    assert actor['reference_text'] == voice['transcript']
    validate_job_references(job, data)
    assert client.delete('/api/voices/' + voice['id']).status_code == 409


def test_native_reference_info_says_audio_conditioning_but_target_remains_hmong(native_studio):
    client, _ = native_studio
    audio, _ = hmong_assets.reference('hmong-male')
    info = client.post('/api/hmong/reference-info',
        files={'file': ('external.wav', audio.read_bytes())})
    assert info.status_code == 200, info.text
    assert info.json()['requires_transcript'] is False
    assert info.json()['reference_conditioning'] == 'audio'
    voice = save_reference(client)
    response = client.post('/api/speech', json={
        'text': '你好。', 'voice_id': voice['id'], 'language': 'mww'})
    assert response.status_code == 422
    app.executor.submit.assert_not_called()


@pytest.mark.parametrize('cast_voice', [False, True])
def test_legacy_custom_profile_cannot_redirect_to_a_copied_default_speaker(native_studio, monkeypatch, cast_voice):
    """Reproduce legacy metadata naming male while its own audio is female."""
    import numpy as np
    from character_cast import settings_for_cue
    client, data = native_studio
    voice = save_reference(client, transcript='This recording is not in Hmong.')
    profile_path = data / 'voices' / (voice['id'] + '.json')
    app.write_json(profile_path, {**voice, 'speaker': 'hmong-male', 'voice_id': 'hmong-male'})
    original_profile = profile_path.read_bytes()
    payload = {'text': 'Nyob zoo.', 'voice_id': voice['id'], 'language': 'mww'}
    if cast_voice:
        payload.update(text='1\n00:00:00,000 --> 00:00:04,000\nNyob zoo.',
                       input_format='srt', voice_id='hmong-male',
                       character_voices={'visitor': voice['id']}, cue_characters=['visitor'])
    response = client.post('/api/speech', json=payload)
    assert response.status_code == 202, response.text
    job = response.json()
    settings = settings_for_cue(job, 0) if cast_voice else job
    assert settings['voice_id'] == voice['id'] and settings['speaker'] is None
    validate_job_references(job, data)
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
    worker.load_synthesizer(settings)('Nyob zoo.', data / 'parts' / 'probe.wav')
    actual_path = data / 'voices' / (voice['id'] + '.wav')
    assert received == [(actual_path, actual_path.read_bytes(), voice['transcript'])]
    assert profile_path.read_bytes() == original_profile


def test_old_job_with_custom_id_and_preset_speaker_rejected_before_mutating_checkpoints(native_studio, monkeypatch):
    client, data = native_studio
    voice = save_reference(client)
    response = client.post('/api/speech', json={
        'text': 'Nyob zoo.', 'voice_id': voice['id'], 'language': 'mww'})
    assert response.status_code == 202, response.text
    job = response.json()
    job['speaker'] = 'hmong-male'
    job['hmong_voice_snapshot']['speaker'] = 'hmong-male'
    job['status'] = 'cancelled'
    app.write_json(data / 'jobs' / (job['id'] + '.json'), job)
    folder = data / 'parts' / job['id']
    folder.mkdir()
    checkpoint = folder / '000000.wav'
    checkpoint.write_bytes(b'unchanged legacy checkpoint')
    flag = folder / 'cancel.flag'
    flag.touch()
    before = checkpoint.read_bytes()
    resumed = client.post('/api/jobs/' + job['id'] + '/resume')
    assert resumed.status_code == 409, resumed.text
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(data))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', data)
    with pytest.raises(ValueError, match='giọng cá nhân'):
        worker.render(job)
    with pytest.raises(ValueError, match='giọng cá nhân'):
        worker.load_synthesizer(job)
    assert checkpoint.read_bytes() == before and flag.exists()
