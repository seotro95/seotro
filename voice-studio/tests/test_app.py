import io
import wave
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app


@pytest.fixture
def studio(tmp_path, monkeypatch):
    for folder in ('voices', 'audio', 'jobs', 'models', 'parts'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    with TestClient(app.app) as client:
        yield client, tmp_path


def sample(seconds=5, silent=False):
    import math
    import struct
    file = io.BytesIO()
    with wave.open(file, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b'\x00\x00' * (24000 * seconds) if silent else b''.join(struct.pack('<h', int(8000 * math.sin(i * 2 * math.pi * 220 / 24000))) for i in range(24000 * seconds)))
    return file.getvalue()


def enroll(client, **data):
    return client.post('/api/voices/clone', data={'name': 'Giọng thử', 'language': 'vi', 'consent': 'true', **data}, files={'file': ('sample.wav', sample(), 'audio/wav')})


def test_local_config_and_missing_model(studio):
    client, root = studio
    conf = client.get('/api/config').json()
    assert conf['mode'] == 'local'
    assert not any(conf['models'].values())
    response = client.post('/api/speech', json={'text': 'Xin chào', 'voice_id': 'vi-maianh'})
    assert response.status_code == 503
    assert not list((root / 'jobs').iterdir())


def test_real_ffmpeg_reference_import_and_delete(studio):
    client, root = studio
    response = enroll(client)
    assert response.status_code == 201, response.text
    voice = response.json()
    assert voice['duration'] == 5
    assert voice['consent_at']
    reference = client.get(f"/api/voices/{voice['id']}/sample")
    assert reference.content[:4] == b'RIFF'
    assert voice['id'] in [v['id'] for v in client.get('/api/voices').json()['voices']]
    assert client.delete('/api/voices/' + voice['id']).status_code == 204
    assert not list((root / 'voices').iterdir())


def test_consent_and_audio_validation(studio):
    client, root = studio
    assert enroll(client, consent='false').status_code == 422
    response = client.post('/api/voices/clone', data={'name': 'Test', 'consent': 'true'}, files={'file': ('x.wav', b'not audio')})
    assert response.status_code == 422
    assert not list((root / 'voices').iterdir())
    response = client.post('/api/voices/clone', data={'name': 'Test', 'consent': 'true'}, files={'file': ('x.wav', sample(1))})
    assert response.status_code == 422
    assert not list((root / 'voices').iterdir())


def test_generation_queue_validation_and_metadata(studio):
    client, root = studio
    (root / 'models' / 'vieneu.ready').touch()
    with patch.object(app.executor, 'submit') as submit:
        response = client.post('/api/speech', json={'text': 'Xin chào thế giới', 'voice_id': 'vi-maianh', 'speed': 1.1, 'format': 'mp3'})
        assert response.status_code == 202
        job = response.json()
        submit.assert_called_once_with(app.run_job, job['id'])
        assert job['engine'] == 'vieneu'
        assert client.get('/api/jobs/' + job['id']).json()['status'] == 'queued'
        assert client.delete('/api/history/' + job['id']).status_code == 409
        assert client.get('/api/audio/' + job['id']).status_code == 404
        for _ in range(3):
            assert client.post('/api/speech', json={'text': 'Thử', 'voice_id': 'vi-maianh'}).status_code == 202
        assert client.post('/api/speech', json={'text': 'Thử', 'voice_id': 'vi-maianh'}).status_code == 429
    assert client.post('/api/speech', json={'text': 'x', 'voice_id': 'vi-maianh', 'language': 'ja'}).status_code == 422
    assert client.post('/api/speech', json={'text': ' ', 'voice_id': 'vi-maianh'}).status_code == 422


def test_clone_uses_international_engine(studio):
    client, root = studio
    voice = enroll(client, language='ja').json()
    (root / 'models' / 'qwen_clone.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={'text': 'こんにちは', 'voice_id': voice['id'], 'language': 'ja'})
    assert response.status_code == 202
    assert response.json()['engine'] == 'qwen_clone'
    assert client.delete('/api/voices/' + voice['id']).status_code == 409


def test_history_audio_and_path_boundaries(studio):
    client, root = studio
    ident = 'a' * 32
    app.write_json(root / 'jobs' / (ident + '.json'), {'id': ident, 'created_at': app.now(), 'status': 'done', 'format': 'wav'})
    (root / 'audio' / (ident + '.wav')).write_bytes(sample())
    assert client.get('/api/audio/' + ident).content[:4] == b'RIFF'
    assert client.get('/api/history').json()['items'][0]['id'] == ident
    assert client.get('/api/audio/invalid').status_code == 404
    assert client.delete('/api/history/' + ident).status_code == 204
    assert not list((root / 'audio').iterdir())


def test_browser_cross_origin_and_host_guard(studio):
    client, _ = studio
    assert client.get('/api/history', headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert client.get('/api/config', headers={'Host': 'untrusted.example'}).status_code == 403
    response = client.get('/')
    assert response.status_code == 200
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert client.get('/static/app.js').status_code == 200


def test_worker_failure_is_persisted(studio):
    _, root = studio
    ident = 'b' * 32
    app.write_json(root / 'jobs' / (ident + '.json'), {'id': ident, 'status': 'queued', 'format': 'wav'})
    with patch('app.execute_worker', return_value=1):
        app.run_job(ident)
    result = app.read_json(root / 'jobs' / (ident + '.json'))
    assert result['status'] == 'error'
    assert 'error' in result
    assert 'nhật ký' in result['error']
