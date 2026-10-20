import array
import asyncio
import io
import math
import subprocess
import wave

import httpx
import pytest
from fastapi import FastAPI

from audio_workspace import load_profile, router


def audio_bytes(seconds=3, silence=False):
    output = io.BytesIO()
    samples = array.array('h', (0 if silence else int(8000 * math.sin(2 * math.pi * 220 * frame / 24000))
                               for frame in range(int(seconds * 24000))))
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(samples.tobytes())
    return output.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA', str(tmp_path))
    app = FastAPI()
    app.include_router(router)

    def request(method, path, **kwargs):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as session:
                return await session.request(method, path, **kwargs)
        return asyncio.run(run())

    return request


def test_reference_roundtrip_and_delete(client):
    response = client('POST', '/api/profiles', data={'name': 'Giọng của tôi', 'transcript': 'Nyob zoo', 'consent': 'true'},
                      files={'audio': ('sample.wav', audio_bytes(), 'audio/wav')})
    assert response.status_code == 201, response.text
    metadata = response.json()
    assert metadata['name'] == 'Giọng của tôi'
    assert metadata['transcript'] == 'Nyob zoo'
    assert metadata['language'] == 'mww'
    assert metadata['duration'] == 3
    rows = client('GET', '/api/profiles').json()
    assert rows['profiles'] == [metadata]
    assert rows['cloning_available'] is False
    served = client('GET', metadata['url'])
    assert served.status_code == 200
    with wave.open(io.BytesIO(served.content), 'rb') as wav:
        assert wav.getframerate() == 24000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
    saved, path = load_profile(metadata['id'])
    assert saved == metadata and path.exists()
    assert client('DELETE', '/api/profiles/' + metadata['id']).status_code == 204
    assert client('GET', metadata['url']).status_code == 404
    assert client('GET', '/api/profiles').json()['profiles'] == []


@pytest.mark.parametrize('details', [{}, {'consent': 'false'}, {'consent': 'true', 'name': ' '}])
def test_reference_needs_name_and_permission(client, details):
    response = client('POST', '/api/profiles', data={'name': 'Sample', **details},
                      files={'audio': ('sample.wav', audio_bytes(), 'audio/wav')})
    assert response.status_code == 422
    assert client('GET', '/api/profiles').json()['profiles'] == []


@pytest.mark.parametrize('audio', [b'not audio', b'', audio_bytes(1), audio_bytes(31), audio_bytes(3, silence=True)])
def test_reject_bad_short_long_or_silent_reference(client, audio):
    response = client('POST', '/api/profiles', data={'name': 'Sample', 'consent': 'true'},
                      files={'audio': ('sample.wav', audio, 'audio/wav')})
    assert response.status_code == 422, response.text
    assert client('GET', '/api/profiles').json()['profiles'] == []


def test_profile_validation_and_path_safety(client):
    for data in ({'name': 'x' * 121}, {'name': 'Sample', 'transcript': 'x' * 2001}):
        response = client('POST', '/api/profiles', data={'consent': 'true', **data},
                          files={'audio': ('sample.wav', audio_bytes(), 'audio/wav')})
        assert response.status_code == 422
    assert client('GET', '/api/profiles/not-an-id/audio').status_code == 404
    assert client('DELETE', '/api/profiles/' + '0' * 32).status_code == 404


@pytest.mark.parametrize('format,media', [('wav', 'audio/wav'), ('mp3', 'audio/mpeg')])
def test_real_audio_export(client, tmp_path, format, media):
    response = client('POST', '/api/audio/export', data={'format': format},
                      files={'audio': ('voice.wav', audio_bytes(1), 'audio/wav')})
    assert response.status_code == 200, response.text
    assert response.headers['content-type'].startswith(media)
    assert f'hmong-studio.{format}' in response.headers['content-disposition']
    output = tmp_path / ('export.' + format)
    output.write_bytes(response.content)
    decoded = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 's16le', '-ac', '1', '-ar', '24000', 'pipe:1'])
    assert 0.95 < len(decoded) / (24000 * 2) < 1.15
    assert any(decoded)


def test_export_invalid_format_and_audio(client):
    for format, audio in [('exe', audio_bytes()), ('wav', b'invalid')]:
        response = client('POST', '/api/audio/export', data={'format': format},
                          files={'audio': ('voice.wav', audio, 'audio/wav')})
        assert response.status_code == 422
