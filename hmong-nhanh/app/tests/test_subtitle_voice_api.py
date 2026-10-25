import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote
from unittest.mock import patch
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app
import custom_references
import voice_jobs


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr(app.cloning_engine, 'availability', lambda: {'ready': True, 'reason': ''})
    monkeypatch.setattr(app, 'hardware_info', lambda: {'device': 'cpu'})
    with TestClient(app.app) as client:
        yield client


def recording(hz=180):
    data = io.BytesIO()
    samples = np.sin(np.arange(24000 * 4) * 2 * np.pi * hz / 24000) * .3
    with wave.open(data, 'wb') as wav:
        wav.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        wav.writeframes((samples * 32767).astype('<i2').tobytes())
    return data.getvalue()


def upload(client, hz=180, name='Giọng tiếng Anh của tôi'):
    original = recording(hz)
    response = client.post('/api/voices/upload', content=original, headers={
        'Content-Type': 'audio/wav', 'X-Voice-Name': quote(name), 'X-File-Name': quote('../../my voice.wav')})
    assert response.status_code == 201, response.text
    voice = response.json()['voice']
    assert voice['name'] == name and voice['gender'] == 'custom'
    assert client.get(voice['reference']).content == original
    response = client.put('/api/voices/' + voice['id'] + '/reference', json={
        'start': 0, 'end': 4, 'text': 'This is the exact English reference.'})
    assert response.status_code == 200, response.text
    return response.json()['voice']


def test_external_voice_uses_own_audio_and_original_language_never_default(client):
    one, two = upload(client, 180), upload(client, 310, 'Một giọng khác')
    seen = []
    def synth(text, speed, sample, transcript, **options):
        seen.append((text, transcript, hashlib.sha256(Path(sample).read_bytes()).hexdigest()))
        return recording()
    with patch('app.builtin_references.selected', side_effect=AssertionError('Never use default')):
        with patch('app.cloning_engine.synthesize', side_effect=synth):
            for voice in (one, two):
                response = client.post('/api/speech', json={'voice': voice['id'], 'text': 'Kuv muaj 12 phau ntawv.'})
                assert response.status_code == 200, response.text
    assert seen[0][:2] == ('Kuv muaj 12 phau ntawv.', 'This is the exact English reference.')
    assert seen[0][2] != seen[1][2]
    assert len(client.get('/api/voices').json()['voices']) == 4


def test_preview_strips_indices_and_timestamps_but_retains_spoken_numbers(client):
    source = '27\n00:04:28,533 --> 00:04:29,333\nKuv muaj 12 phau ntawv xyoo 2026.\n'
    response = client.post('/api/documents/preview', json={'text': source})
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview['text'] == 'Kuv muaj 12 phau ntawv xyoo 2026.'
    assert preview['timed'] and preview['duration'] == 269.333 and preview['cue_count'] == 1
    natural = client.post('/api/documents/preview', json={'text': source, 'timing': 'natural'}).json()
    assert not natural['timed'] and natural['text'] == preview['text']
    voice = upload(client)
    with patch('app.voice_jobs.create', return_value={'id': 'sample', 'parts': []}) as create:
        response = client.post('/api/speech/jobs', json={'text': source, 'voice': voice['id']})
        assert response.status_code == 202, response.text
        snapshot = create.call_args.args[0]
        assert snapshot['text'] == source and snapshot['target_seconds'] == 269.333
        assert snapshot['spoken_characters'] == len(preview['text'])
        assert snapshot['voice_name'] == voice['name']
        assert snapshot['_reference']['text'] == 'This is the exact English reference.'
        assert custom_references.selected(voice['id'])[0] == Path(snapshot['_reference']['path'])


def test_synchronous_natural_mode_cleans_subtitles_and_timed_requires_jobs(client):
    voice = upload(client)
    source = '1\n00:00:01.000 --> 00:00:03.000\nKuv muaj 12.'
    with patch('app.cloning_engine.synthesize', return_value=recording()) as synth:
        payload = {'voice': voice['id'], 'text': source}
        assert client.post('/api/speech', json=payload).status_code == 422
        synth.assert_not_called()
        assert client.post('/api/speech', json={**payload, 'timing': 'natural'}).status_code == 200
        assert synth.call_args.args[0] == 'Kuv muaj 12.'


def test_missing_custom_voice_invalid_timing_and_audio_have_no_default_fallback(client):
    with patch('app.builtin_references.selected', side_effect=AssertionError('No fallback')):
        assert client.post('/api/speech/jobs', json={'voice': 'custom-' + '0' * 32, 'text': 'Nyob zoo'}).status_code == 404
    with patch('app.voice_jobs.create') as create:
        result = client.post('/api/speech/jobs', json={'voice': 'hmong-white-female', 'text': '00:04:99,000 --> 00:05:00,000\n12'})
        assert result.status_code == 422
        create.assert_not_called()
    assert client.post('/api/voices/upload', content=b'not audio').status_code == 422
    assert client.post('/api/voices/upload', content=b'x', headers={'Content-Length': str(51 * 1024 * 1024)}).status_code == 413
    assert len(client.get('/api/voices').json()['voices']) == 2


def test_preview_limits_response_without_truncating_document_validation(client):
    response = client.post('/api/documents/preview', json={'text': '😀' * 1_000_000})
    assert response.status_code == 200
    assert response.json()['characters'] == 1_000_000 and len(response.json()['text']) == 4000
    assert response.json()['preview_truncated']
