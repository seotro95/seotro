"""API coverage uses synthetic references and never loads a speech model."""
import hashlib
import json
from unittest.mock import Mock

import pytest

import app
from test_standalone_api import sine_wave, studio  # noqa: F401


ENGLISH = 'a' * 32
KOREAN = 'b' * 32
THAI = 'c' * 32


@pytest.fixture
def reference_catalog(studio, monkeypatch):
    client, data = studio
    root = data / 'private reference library'
    (root / 'voices').mkdir(parents=True)
    records = []
    for ident, language in ((ENGLISH, 'en-US'), (KOREAN, 'ko'), (THAI, 'th')):
        audio = sine_wave()
        (root / 'voices' / f'{ident}.wav').write_bytes(audio)
        records.append({'id': ident, 'name': f'Synthetic {language}', 'language': language,
                        'reference_audio': f'voices/{ident}.wav',
                        'reference_sha256': hashlib.sha256(audio).hexdigest(),
                        'reference_frames': 96000, 'reference_sample_rate': 24000,
                        'duration': 4, 'original_audio': f'originals/{ident}.mp3',
                        'transcript': f'Private draft for {language}.'})
    (root / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'voices': records}), encoding='utf-8')
    monkeypatch.setenv('VOICE_STUDIO_VOICE_LIBRARY', str(root))
    submit = Mock()
    monkeypatch.setattr(app.executor, 'submit', submit)
    return client, data, root, submit


def default_voices(client):
    return {voice['id']: voice for voice in client.get('/api/voices').json()['voices']
            if voice.get('is_default')}


def prepared_international_model(data, monkeypatch):
    # Metadata/empty files exercise readiness validation only. No execution or
    # synthesized speech is claimed by these API tests.
    runtime = data / 'synthetic-international-python'
    runtime.touch()
    monkeypatch.setenv('VOICE_STUDIO_INTERNATIONAL_PYTHON', str(runtime))
    model = data / 'models' / 'synthetic-voxcpm2-cpu'
    model.mkdir()
    (model / 'config.json').write_text(json.dumps({'architecture': 'voxcpm2', 'dtype': 'float32'}))
    (model / 'model.safetensors').touch()
    (model / 'audiovae.safetensors').touch()
    (data / 'models' / 'voxcpm.ready').write_text(json.dumps({'model_dir': model.name}))
    return runtime, model


def test_defaults_are_listed_with_native_languages_without_private_metadata(reference_catalog):
    client, data, root, _ = reference_catalog
    voices = default_voices(client)
    assert set(voices) == {ENGLISH, KOREAN, THAI}
    assert {ident: voice['native_language'] for ident, voice in voices.items()} == {
        ENGLISH: 'en', KOREAN: 'ko', THAI: 'th'}
    assert voices[ENGLISH]['languages'] == ['en-US', 'en-GB']
    assert voices[KOREAN]['languages'] == ['ko'] and voices[THAI]['languages'] == ['th']
    for voice in voices.values():
        assert voice['category'] == 'reference' and voice['readonly'] is True
        assert voice['has_sample'] is True and voice['ready'] is False
        assert not {'transcript', 'original_audio', 'reference_audio', 'reference_sha256'} & voice.keys()
        assert str(root) not in json.dumps(voice)
    config = client.get('/api/config').json()
    assert {'en-US', 'en-GB', 'ko', 'th'} <= set(config['ai_voice_languages'])
    assert 'th' in config['languages'] and config['models']['voxcpm'] is False
    assert 'TAI_GIONG_DA_NGON_NGU.bat' in voices[THAI]['missing_reason']


@pytest.mark.parametrize('ident', [ENGLISH, KOREAN, THAI])
def test_default_sample_is_available_and_default_cannot_be_deleted(reference_catalog, ident):
    client, _, root, _ = reference_catalog
    response = client.get(f'/api/voices/{ident}/sample')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/wav'
    assert response.content == (root / 'voices' / f'{ident}.wav').read_bytes()
    assert client.delete(f'/api/voices/{ident}').status_code == 403
    assert ident in default_voices(client)
    assert client.get(f'/api/voices/{ident}/sample').content == response.content


def test_english_default_queues_reference_id_without_a_preset_speaker(reference_catalog):
    client, data, _, submit = reference_catalog
    (data / 'models' / 'vieneu.ready').touch()
    response = client.post('/api/speech', json={'voice_id': ENGLISH, 'language': 'en-US',
                                               'text': 'A synthetic English test.'})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['voice_id'] == ENGLISH and job['speaker'] is None and job['engine'] == 'vieneu'
    assert app.read_json(data / 'jobs' / f"{job['id']}.json")['voice_id'] == ENGLISH
    assert not (data / 'voices' / f'{ENGLISH}.json').exists()
    submit.assert_called_once_with(app.run_job, job['id'])
    assert default_voices(client)[ENGLISH]['ready'] is True
    assert client.post('/api/speech', json={'voice_id': ENGLISH, 'language': 'ko',
                                          'text': '잘못된 언어입니다.'}).status_code == 422


@pytest.mark.parametrize('state', ['absent', 'marker_only', 'missing_runtime', 'wrong_dtype'])
def test_international_defaults_require_runtime_and_prepared_model(reference_catalog, monkeypatch, state):
    client, data, _, submit = reference_catalog
    runtime_path = data / 'missing-international-python'
    monkeypatch.setenv('VOICE_STUDIO_INTERNATIONAL_PYTHON', str(runtime_path))
    if state == 'marker_only':
        runtime_path.touch()
        (data / 'models' / 'voxcpm.ready').write_text(json.dumps({'model_dir': 'missing-model'}))
    elif state in {'missing_runtime', 'wrong_dtype'}:
        runtime, model = prepared_international_model(data, monkeypatch)
        if state == 'missing_runtime':
            runtime.unlink()
        else:
            (model / 'config.json').write_text(json.dumps({'architecture': 'voxcpm2', 'dtype': 'bfloat16'}))
    response = client.post('/api/speech', json={'voice_id': THAI, 'language': 'th',
                                               'text': 'สวัสดีครับ'})
    assert response.status_code == 503, response.text
    assert 'TAI_GIONG_DA_NGON_NGU.bat' in response.json()['detail']
    assert default_voices(client)[THAI]['ready'] is False
    assert client.get('/api/config').json()['models']['voxcpm'] is False
    submit.assert_not_called()
    assert not list((data / 'jobs').glob('*.json'))


@pytest.mark.parametrize(('ident', 'language', 'text'), [
    (KOREAN, 'ko', '안녕하세요.'), (THAI, 'th', 'สวัสดีครับ')])
def test_ready_international_defaults_queue_with_voxcpm(reference_catalog, monkeypatch, ident, language, text):
    client, data, _, submit = reference_catalog
    prepared_international_model(data, monkeypatch)
    assert client.get('/api/config').json()['models']['voxcpm'] is True
    assert default_voices(client)[ident]['ready'] is True
    response = client.post('/api/speech', json={'voice_id': ident, 'language': language, 'text': text})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['engine'] == 'voxcpm' and job['speaker'] is None and job['voice_id'] == ident
    submit.assert_called_once_with(app.run_job, job['id'])


def test_resume_uses_readonly_catalog_reference_without_editable_clone_metadata(reference_catalog):
    client, data, root, submit = reference_catalog
    (data / 'models' / 'vieneu.ready').touch()
    response = client.post('/api/speech', json={'voice_id': ENGLISH, 'language': 'en-US', 'text': 'Resume this test.'})
    assert response.status_code == 202, response.text
    job = response.json()
    assert client.post(f"/api/jobs/{job['id']}/cancel").status_code == 202
    assert not (data / 'voices' / f'{ENGLISH}.json').exists()
    submit.reset_mock()
    resumed = client.post(f"/api/jobs/{job['id']}/resume")
    assert resumed.status_code == 202, resumed.text
    assert resumed.json()['status'] == 'queued'
    submit.assert_called_once_with(app.run_job, job['id'])
    assert client.post(f"/api/jobs/{job['id']}/cancel").status_code == 202
    (root / 'voices' / f'{ENGLISH}.wav').unlink()
    assert client.post(f"/api/jobs/{job['id']}/resume").status_code == 409


def test_tampered_reference_is_blocked_for_preview_and_speech(reference_catalog):
    client, data, root, submit = reference_catalog
    (data / 'models' / 'vieneu.ready').touch()
    path = root / 'voices' / f'{ENGLISH}.wav'
    content = bytearray(path.read_bytes())
    content[-1] ^= 1
    path.write_bytes(content)
    voice = default_voices(client)[ENGLISH]
    assert voice['ready'] is False and voice['has_sample'] is False
    assert 'SHA256' in voice['missing_reason']
    assert client.get(f'/api/voices/{ENGLISH}/sample').status_code == 404
    response = client.post('/api/speech', json={'voice_id': ENGLISH, 'language': 'en-US', 'text': 'Do not queue.'})
    assert response.status_code == 503, response.text
    assert str(root) not in response.text
    submit.assert_not_called()


def test_imported_thai_clone_uses_international_backend_and_can_be_previewed(reference_catalog):
    client, data, _, submit = reference_catalog
    response = client.post('/api/voices/clone', data={'name': 'Synthetic Thai clone', 'language': 'th', 'consent': 'true'},
                           files={'file': ('synthetic-reference.wav', sine_wave(), 'audio/wav')})
    assert response.status_code == 201, response.text
    voice = response.json()
    assert voice['engine'] == 'voxcpm' and voice['language'] == 'th' and voice['languages'] == ['th']
    stored = app.read_json(data / 'voices' / f"{voice['id']}.json")
    assert stored['engine'] == 'voxcpm'
    listed = next(item for item in client.get('/api/voices').json()['voices'] if item['id'] == voice['id'])
    assert listed['native_language'] == 'th' and listed['ready'] is False
    assert client.get(f"/api/voices/{voice['id']}/sample").status_code == 200
    assert client.delete(f"/api/voices/{voice['id']}").status_code == 204
    submit.assert_not_called()
