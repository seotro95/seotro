"""Exercise the real local API and FFmpeg without claiming AI models are loaded."""
import io
import json
import math
import struct
import subprocess
import uuid
import wave

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


def sine_wave(seconds=4, rate=24000):
    buffer = io.BytesIO()
    samples = (struct.pack('<h', round(4000 * math.sin(2 * math.pi * 220 * n / rate))) for n in range(rate * seconds))
    with wave.open(buffer, 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(b''.join(samples))
    return buffer.getvalue()


def test_text_boundary_and_missing_model_are_distinct(studio):
    client, data = studio
    config = client.get('/api/config').json()
    assert config['edition'] == 'standalone-voice'
    assert config['max_characters'] == 1_000_000
    assert not any(config['models'].values())
    text = ('Xin chào. ' * 111_112)[:1_000_000]
    valid = {'text': text, 'voice_id': 'vi-maianh'}
    # 503 means the exact-limit body passed schema validation, while the
    # model correctly remains unavailable. No ready marker is fabricated.
    assert client.post('/api/speech', json=valid).status_code == 503
    assert client.post('/api/speech', json={**valid, 'text': text + 'a'}).status_code == 422
    converted = client.post('/api/scripts/convert', json={'text': text, 'input_format': 'txt', 'output_format': 'txt'})
    assert converted.status_code == 200
    assert converted.json()['text'] == text
    assert client.post('/api/scripts/convert', json={'text': text + 'a', 'input_format': 'txt', 'output_format': 'txt'}).status_code == 422
    assert not list((data / 'jobs').iterdir())


def test_video_writing_translation_are_not_in_standalone(studio):
    client, _ = studio
    paths = client.get('/openapi.json').json()['paths']
    assert not any(any(word in path for word in ('video', 'writing', 'translation', 'dubbed')) for path in paths)
    response = client.post('/api/speech', json={'text': 'Xin chào', 'voice_id': 'vi-maianh', 'video_id': 'a' * 32})
    assert response.status_code == 422


def test_real_ffmpeg_voice_reference_import_and_delete(studio):
    client, data = studio
    response = client.post('/api/voices/clone', data={'name': 'Mẫu kiểm thử', 'language': 'vi', 'consent': 'true'}, files={'file': ('reference.wav', sine_wave(), 'audio/wav')})
    assert response.status_code == 201, response.text
    voice = response.json()
    assert voice['duration'] == 4
    assert voice['consent_at']
    sample = client.get(f"/api/voices/{voice['id']}/sample")
    with wave.open(io.BytesIO(sample.content), 'rb') as stream:
        assert (stream.getnchannels(), stream.getframerate(), stream.getsampwidth()) == (1, 24000, 2)
    entry = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == voice['id'])
    assert entry['ready'] is False
    assert client.delete('/api/voices/' + voice['id']).status_code == 204
    assert not list((data / 'voices').iterdir())


def test_consent_bad_audio_and_local_browser_guard(studio):
    client, data = studio
    denied = client.post('/api/voices/clone', data={'name': 'Mẫu', 'consent': 'false'}, files={'file': ('reference.wav', sine_wave(), 'audio/wav')})
    assert denied.status_code == 422
    invalid = client.post('/api/voices/clone', data={'name': 'Mẫu', 'consent': 'true'}, files={'file': ('reference.wav', b'not wave', 'audio/wav')})
    assert invalid.status_code == 422
    assert not list((data / 'voices').iterdir())
    assert client.get('/api/config', headers={'Origin': 'https://untrusted.example'}).status_code == 403


def test_real_ffmpeg_mp3_wav_and_text_exports(studio):
    client, data = studio
    ident = uuid.uuid4().hex
    app.write_json(data / 'jobs' / f'{ident}.json', {'id': ident, 'status': 'done', 'format': 'wav', 'text': 'Xin chào.', 'input_format': 'txt'})
    source = data / 'audio' / f'{ident}.wav'
    source.write_bytes(sine_wave(seconds=1))
    (data / 'audio' / f'{ident}.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nXin chào.\n', encoding='utf-8')
    mp3 = client.get(f'/api/jobs/{ident}/export.mp3')
    assert mp3.status_code == 200 and mp3.headers['content-type'] == 'audio/mpeg'
    probed = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name', '-of', 'json', str(data / 'audio' / f'{ident}.mp3')], capture_output=True, check=True)
    assert json.loads(probed.stdout)['streams'][0]['codec_name'] == 'mp3'
    assert client.get(f'/api/jobs/{ident}/export.wav').content == source.read_bytes()
    assert client.get(f'/api/jobs/{ident}/export.txt').text == 'Xin chào.\n'
    assert '00:00:01,000' in client.get(f'/api/jobs/{ident}/export.srt').text
    assert client.get(f'/api/jobs/{ident}/timing').json()['cues'][0]['text'] == 'Xin chào.'
    assert client.get(f'/api/jobs/{ident}/export.exe').status_code == 422


def test_srt_to_text_uses_parsed_cues(studio):
    client, _ = studio
    srt = '1\n00:00:00,000 --> 00:00:03,000\nXin chào.\n'
    response = client.post('/api/scripts/convert', json={'text': srt, 'input_format': 'srt', 'output_format': 'txt'})
    assert response.status_code == 200
    assert response.json()['text'] == 'Xin chào.'
    assert client.post('/api/scripts/convert', json={'text': 'Xin chào.', 'input_format': 'txt', 'output_format': 'srt'}).status_code == 422


@pytest.mark.parametrize('extension', ['wav', 'mp3'])
def test_worker_audio_pipeline_with_explicit_test_synthesizer(tmp_path, monkeypatch, extension):
    # Exercise rendering, checkpoints, real normalization/export and timing with
    # deterministic test audio. This is not a test of any AI voice/model.
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    import worker
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    ident = uuid.uuid4().hex
    job = {'id': ident, 'text': 'Xin chào. **Cảm ơn bạn.**', 'engine': 'system', 'voice_id': 'fixture', 'speaker': 'Fixture', 'language': 'vi', 'format': extension, 'speed': 1.0, 'delivery': 'natural', 'paragraph_pause': 0.2, 'max_minutes': 1}
    spoken = []

    def test_synthesizer(text, output):
        spoken.append(text)
        output.write_bytes(sine_wave(seconds=1))

    worker.render(job, synthesize=test_synthesizer)
    assert spoken == ['Xin chào.', 'Cảm ơn bạn.']
    audio = tmp_path / 'audio' / f'{ident}.{extension}'
    assert audio.stat().st_size > 100
    result = json.loads((tmp_path / 'parts' / ident / 'result.json').read_text())
    assert result['completed'] == result['total'] == 2
    assert result['audio_seconds'] > 2
    assert result['duration_limited'] is False
    assert 'Cảm ơn bạn.' in (tmp_path / 'audio' / f'{ident}.srt').read_text()
    assert json.loads((tmp_path / 'parts' / ident / 'progress.json').read_text())['progress'] >= 90


@pytest.mark.parametrize('srt', [
    '1\ninvalid timestamp\nXin chào.',
    '1\n00:00:02,000 --> 00:00:01,000\nXin chào.',
    '1\n00:00:00,000 --> 24:00:00,001\nXin chào.',
    '1\n00:00:00,000 --> 00:00:02,000\nXin chào.\n\n2\n00:00:01,000 --> 00:00:03,000\nChồng mốc.',
    '1\n00:00:00,000 --> 00:00:02,000\n<i></i>',
])
def test_invalid_srt_conversion_returns_validation_error(studio, srt):
    client, data = studio
    response = client.post('/api/scripts/convert', json={'text': srt, 'input_format': 'srt', 'output_format': 'txt'})
    assert response.status_code == 422
    assert response.json()['detail'].startswith('SRT:')
    assert not list((data / 'jobs').iterdir())
