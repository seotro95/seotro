import asyncio
import hashlib
import io
import json
import time
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app
import builtin_references
import voice_jobs


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path))
    monkeypatch.setattr(app.cloning_engine, 'availability', lambda: {
        'ready': True, 'configured': True, 'dependencies': True, 'reason': ''})
    with TestClient(app.app) as value:
        yield value


def save(client, gender, text, start=0, end=4):
    result = client.put('/api/voices/hmong-white-' + gender + '/reference',
                        json={'text': text, 'start': start, 'end': end})
    assert result.status_code == 200, result.text
    return result.json()['voice']


def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b'\x01\x01' * 2400)
    return output.getvalue()


def test_male_and_female_route_to_distinct_wav_and_exact_transcript(client):
    seen = []
    def synth(text, speed, sample, transcript):
        with wave.open(str(sample)) as wav:
            assert wav.getframerate() == 24000
            assert wav.getnchannels() == 1
            assert wav.getnframes() == 4 * 24000
            digest = hashlib.sha256(wav.readframes(wav.getnframes())).hexdigest()
        seen.append((text, speed, transcript, digest))
        return wav_bytes()
    with patch('app.cloning_engine.synthesize', side_effect=synth):
        for gender in ('female', 'male'):
            voice = save(client, gender, 'Exact ' + gender + ' transcript')
            assert voice['generation_configured']
            response = client.post('/api/speech', json={
                'text': 'Nyob zoo.', 'voice': voice['id'], 'speed': .8})
            assert response.status_code == 200, response.text
            assert response.content == wav_bytes()
    assert [row[:3] for row in seen] == [
        ('Nyob zoo.', .8, 'Exact female transcript'),
        ('Nyob zoo.', .8, 'Exact male transcript')]
    assert seen[0][3] != seen[1][3]


def test_reference_pair_is_frozen_at_job_submission(client):
    save(client, 'male', 'First exact male words')
    with patch('app.voice_jobs.create', return_value={'id': 'test', 'status': 'running'}) as create:
        response = client.post('/api/speech/jobs', json={
            'text': 'Nyob zoo.', 'voice': 'hmong-white-male', 'speed': 1.2,
            '_reference': {'path': '/untrusted', 'text': 'untrusted'}})
        assert response.status_code == 202
        sent = create.call_args.args[0]
        assert sent['_reference']['text'] == 'First exact male words'
        original = Path(sent['_reference']['path'])
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        save(client, 'male', 'New exact male words', 4, 8)
        current, text = builtin_references.selected('hmong-white-male')
        assert current != original
        assert text == 'New exact male words'
        assert hashlib.sha256(original.read_bytes()).hexdigest() == digest
        assert sent['_reference']['text'] == 'First exact male words'
        assert sent['voice'] == 'hmong-white-male' and sent['speed'] == 1.2


def test_missing_model_reference_and_bad_input_never_start_worker(client):
    with patch('app.voice_jobs.create') as create:
        response = client.post('/api/speech/jobs', json={'text': 'Nyob zoo', 'voice': 'hmong-white-female'})
        assert response.status_code == 422
        assert 'lời mẫu' in response.json()['detail']
        with patch('app.cloning_engine.availability', return_value={'ready': False, 'reason': 'Cần cài mô hình.'}):
            assert not client.get('/api/status').json()['ready']
            result = client.post('/api/speech/jobs', json={'text': 'Nyob zoo', 'voice': 'hmong-white-female'})
            assert result.status_code == 503
            assert result.json()['detail'] == 'Cần cài mô hình.'
        for payload in ({'text': ' ', 'voice': 'hmong-white-male'},
                        {'text': 'x' * 2001, 'voice': 'hmong-white-male'},
                        {'text': 'Nyob zoo', 'voice': 'unknown'},
                        {'text': 'Nyob zoo', 'voice': 'hmong-white-female', 'speed': 4}):
            assert client.post('/api/speech/jobs', json=payload).status_code == 422
        create.assert_not_called()


def test_reference_validation_and_independent_saved_settings(client):
    for selection in ({'start': 0, 'end': 2, 'text': 'words'},
                      {'start': 0, 'end': 9, 'text': 'words'},
                      {'start': 30, 'end': 34, 'text': 'words'},
                      {'start': 0, 'end': 4, 'text': '  '}):
        assert client.put('/api/voices/hmong-white-female/reference', json=selection).status_code == 422
    save(client, 'female', 'Exact female words', 1, 5)
    catalog = client.get('/api/voices').json()['voices']
    assert catalog[0]['reference_ready'] and not catalog[1]['reference_ready']
    assert catalog[0]['reference_settings']['start'] == 1
    assert catalog[0]['reference_settings']['text'] == 'Exact female words'
    assert client.put('/api/voices/unknown/reference', json={'start': 0, 'end': 4, 'text': 'x'}).status_code == 404


def test_reference_extraction_does_not_require_external_ffmpeg(client, monkeypatch):
    monkeypatch.setenv('PATH', '')
    saved = save(client, 'male', 'Exact male transcript')
    assert saved['generation_configured']
    assert client.get('/api/status').json()['ready']
    path, transcript = builtin_references.selected('hmong-white-male')
    with wave.open(str(path)) as audio:
        assert audio.getframerate() == 24000
        assert audio.getnframes() == 4 * 24000
        assert audio.getnchannels() == 1
    assert transcript == 'Exact male transcript'


def test_cancellable_worker_and_restart(client, tmp_path, monkeypatch):
    worker = tmp_path / 'worker.py'
    worker.write_text('import sys,time\nsys.stdin.read()\ntime.sleep(60)\n', encoding='utf-8')
    monkeypatch.setattr(voice_jobs, 'WORKER', worker)
    save(client, 'female', 'Exact female transcript')
    payload = {'text': 'Nyob zoo.', 'voice': 'hmong-white-female'}
    result = client.post('/api/speech/jobs', json=payload)
    assert result.status_code == 202
    ident = result.json()['id']
    deadline = time.monotonic() + 5
    while 'process' not in voice_jobs.get(ident):
        assert time.monotonic() < deadline
        time.sleep(.01)
    process = voice_jobs.get(ident)['process']
    assert client.post('/api/speech/jobs', json=payload).status_code == 409
    assert client.post('/api/speech/jobs/' + ident + '/stop').json()['status'] == 'cancelled'
    assert process.returncode is not None
    assert client.get('/api/speech/jobs/' + ident + '/audio').status_code == 409
    another = client.post('/api/speech/jobs', json=payload)
    assert another.status_code == 202
    assert client.post('/api/speech/jobs/' + another.json()['id'] + '/stop').json()['status'] == 'cancelled'


def test_worker_result_is_downloadable_audio(client, tmp_path, monkeypatch):
    worker = tmp_path / 'worker.py'
    worker.write_text("""import sys,json,wave
from pathlib import Path
p=Path(sys.argv[1]); raw=json.load(sys.stdin)
assert raw['voice']=='hmong-white-male'
assert raw['_reference']['text']=='Exact male transcript'
assert Path(raw['_reference']['path']).is_file()
with wave.open(str(p/'audio.bin'),'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000)
    wav.writeframes(b'\\x01\\x01'*2400)
(p/'result.json').write_text(json.dumps({'media_type':'audio/wav'}))
""", encoding='utf-8')
    monkeypatch.setattr(voice_jobs, 'WORKER', worker)
    save(client, 'male', 'Exact male transcript')
    result = client.post('/api/speech/jobs', json={'text': 'Nyob zoo.', 'voice': 'hmong-white-male'})
    assert result.status_code == 202
    ident = result.json()['id']
    deadline = time.monotonic() + 5
    while True:
        state = client.get('/api/speech/jobs/' + ident).json()
        if state['status'] != 'running':
            break
        assert time.monotonic() < deadline
        time.sleep(.01)
    assert state['status'] == 'completed', state
    response = client.get('/api/speech/jobs/' + ident + '/audio')
    assert response.status_code == 200
    with wave.open(io.BytesIO(response.content)) as audio:
        assert audio.getnframes() == 2400 and audio.getframerate() == 24000
