from unittest.mock import patch

from test_app import studio, enroll, sample  # noqa: F401


def test_silent_clone_does_not_register_as_usable(studio):
    client, root = studio
    response = client.post('/api/voices/clone', data={'name': 'Mẫu im lặng', 'consent': 'true'}, files={'file': ('silent.wav', sample(silent=True), 'audio/wav')})
    assert response.status_code == 422 and 'im lặng' in response.json()['detail']
    assert not list((root / 'voices').iterdir())


def test_nano_clone_needs_reference_graphs_not_only_preset_model(studio):
    client, root = studio
    (root / 'models' / 'vieneu_nano.ready').touch()
    response = enroll(client, engine='vieneu_nano')
    assert response.status_code == 201
    voice = response.json()
    assert voice['engine'] == 'vieneu_nano' and voice['preparation_engine'] == 'vieneu_nano_clone'
    assert next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == voice['id'])['ready'] is False
    body = {'text': 'Đây là lời đọc mới của giọng cá nhân.', 'voice_id': voice['id']}
    assert client.post('/api/speech', json=body).status_code == 503
    (root / 'models' / 'vieneu_nano_clone.ready').touch()
    with patch('app.executor.submit'):
        result = client.post('/api/speech', json=body)
        assert result.status_code == 202 and result.json()['engine'] == 'vieneu_nano'
        task = client.post('/api/video-tasks', json={'action': 'prepare_voice', 'engine': 'vieneu_nano_clone'})
        assert task.status_code == 202


def test_auto_clone_pins_engine_and_preserves_explicit_choice(studio):
    client, root = studio
    assert enroll(client).json()['engine'] == 'vieneu'
    (root / 'models' / 'vieneu_nano_clone.ready').touch()
    assert enroll(client).json()['engine'] == 'vieneu_nano'
    assert enroll(client, engine='vieneu').json()['engine'] == 'vieneu'
    assert enroll(client, engine='qwen_clone').status_code == 422
    assert enroll(client, language='ja', engine='vieneu_nano').status_code == 422
