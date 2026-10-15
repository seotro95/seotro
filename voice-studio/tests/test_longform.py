import importlib
import json
import wave
from unittest.mock import patch

import httpx
import pytest

import app
import writing
from narration import MAX_SECONDS, PCMWriter, split_script
from test_app import studio  # noqa: F401


def test_real_three_hour_streaming_limit(tmp_path):
    # Low test sample rate keeps this exact three-hour boundary test at 21.6 MB.
    path = tmp_path / 'three-hours.wav'
    writer = PCMWriter(path, rate=1000)
    writer.silence(MAX_SECONDS + 120)
    writer.close()
    with wave.open(str(path)) as audio:
        assert audio.getnframes() / audio.getframerate() == 10800
    assert writer.frames == writer.limit


def test_unicode_chunks_preserve_text_and_controls():
    text = 'Xin chào. **Nhấn ý này** [pause=1.5] 日本語。 한국어! ' + 'rất dài ' * 100
    segments = split_script(text)
    assert any(s.emphasis and s.text == 'Nhấn ý này' for s in segments)
    assert any(s.pause == 1.5 for s in segments)
    assert all(len(s.text) <= 240 for s in segments)
    assert '日本語。' in [s.text for s in segments]
    assert not any('pause=' in s.text or '**' in s.text for s in segments)
    with pytest.raises(ValueError):
        split_script('Nội dung [pause=999]')


def write_wave(path, seconds):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b'\x10\x00' * int(24000 * seconds))


def local_worker(root, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(root))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', root)
    return module


def job(ident='c' * 32, **changes):
    return {'id': ident, 'text': 'Câu đầu. Câu tiếp.', 'engine': 'vieneu', 'speaker': 'Mai Anh', 'speed': 1, 'format': 'wav', 'language': 'vi', 'paragraph_pause': 0, **changes}


def test_worker_resumes_completed_chunks_with_real_ffmpeg(studio, monkeypatch):
    _, root = studio
    worker = local_worker(root, monkeypatch)
    calls = []
    def failing(text, path):
        calls.append(text)
        if len(calls) == 2:
            raise RuntimeError('Interrupted after a complete chunk')
        write_wave(path, 1)
    with pytest.raises(RuntimeError):
        worker.render(job(), synthesize=failing)
    assert len(list((root / 'parts' / ('c' * 32)).glob('0*.wav'))) == 1
    def resume(text, path):
        calls.append(text)
        write_wave(path, 1)
    worker.render(job(), synthesize=resume)
    assert calls == ['Câu đầu.', 'Câu tiếp.', 'Câu tiếp.']
    with wave.open(str(root / 'audio' / ('c' * 32 + '.wav'))) as audio:
        assert audio.getnframes() > 45000
    result = json.loads((root / 'parts' / ('c' * 32) / 'result.json').read_text())
    assert result['completed'] == 2 and not result['duration_limited']


def test_pipeline_caps_actual_duration_and_reports_unread_text(studio, monkeypatch):
    _, root = studio
    worker = local_worker(root, monkeypatch)
    worker.render(job(max_minutes=1), synthesize=lambda text, path: write_wave(path, 70))
    with wave.open(str(root / 'audio' / ('c' * 32 + '.wav'))) as audio:
        assert audio.getnframes() == 60 * 24000
    result = json.loads((root / 'parts' / ('c' * 32) / 'result.json').read_text())
    assert result['duration_limited'] and result['completed'] == 1


def test_long_script_acceptance_and_cancel_resume(studio):
    client, root = studio
    (root / 'models' / 'vieneu.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={'text': 'Kịch bản dài. ' * 1000, 'voice_id': 'vi-maianh', 'max_minutes': 180})
        assert response.status_code == 202
        ident = response.json()['id']
        assert response.json()['total'] == 1000
        assert client.post(f'/api/jobs/{ident}/cancel').json()['status'] == 'cancelled'
        assert (root / 'parts' / ident / 'cancel.flag').exists()
        assert client.post(f'/api/jobs/{ident}/resume').json()['status'] == 'queued'
        assert not (root / 'parts' / ident / 'cancel.flag').exists()
    assert client.post('/api/speech', json={'text': 'x', 'voice_id': 'vi-maianh', 'max_minutes': 181}).status_code == 422
    assert client.post('/api/speech', json={'text': '[pause=1]', 'voice_id': 'vi-maianh'}).status_code == 422
    assert client.post('/api/speech', json={'text': 'x' * 200001, 'voice_id': 'vi-maianh'}).status_code == 422


@pytest.mark.parametrize('provider', ['openai', 'gemini'])
def test_writing_api_contract_and_in_memory_key(studio, monkeypatch, provider):
    client, _ = studio
    writing.KEYS.clear()
    for key in ('OPENAI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    seen = []
    def respond(request):
        seen.append(request)
        if request.method == 'GET':
            return httpx.Response(200, json={'data': [], 'models': []})
        body = json.loads(request.content)
        if provider == 'openai':
            assert request.headers['Authorization'] == 'Bearer test-key'
            assert 'input' in body and request.url.path == '/v1/responses'
            return httpx.Response(200, json={'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': 'Xin **chào** [pause=0.8]'}]}]})
        assert request.headers['x-goog-api-key'] == 'test-key'
        assert 'contents' in body and 'generateContent' in request.url.path
        return httpx.Response(200, json={'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': 'Một kịch bản'}]}}]})
    original = httpx.AsyncClient
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(writing.httpx, 'AsyncClient', lambda **kwargs: original(transport=transport, **kwargs))
    response = client.post('/api/writing/connect', json={'provider': provider, 'api_key': 'test-key'})
    assert response.status_code == 200
    assert 'test-key' not in response.text
    assert client.get('/api/writing/connections').json()['providers'][provider]
    response = client.post('/api/writing/generate', json={'provider': provider, 'prompt': 'Viết câu chào', 'minutes': 180})
    assert response.status_code == 200 and response.json()['text']
    assert response.json()['incomplete'] == (provider == 'gemini')
    assert len(seen) == 2
    assert client.delete('/api/writing/connections/' + provider).status_code == 204
    assert not client.get('/api/writing/connections').json()['providers'][provider]
    assert client.post('/api/writing/generate', json={'provider': provider, 'prompt': 'Test'}).status_code == 503


def test_failed_writing_connection_does_not_save_key(studio, monkeypatch):
    client, _ = studio
    writing.KEYS.clear()
    original = httpx.AsyncClient
    monkeypatch.setattr(writing.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(401, json={'error': 'secret detail'})), **kwargs))
    response = client.post('/api/writing/connect', json={'provider': 'openai', 'api_key': 'bad-key'})
    assert response.status_code == 502
    assert 'bad-key' not in response.text and not writing.KEYS


def test_second_server_cannot_interrupt_running_job(studio):
    from fastapi.testclient import TestClient
    _, root = studio
    ident = 'd' * 32
    app.write_json(root / 'jobs' / (ident + '.json'), {'id': ident, 'status': 'running'})
    with pytest.raises(RuntimeError, match='đã chạy'):
        with TestClient(app.app):
            pass
    assert app.read_json(root / 'jobs' / (ident + '.json'))['status'] == 'running'


def test_shutdown_terminates_real_worker_process(studio, monkeypatch, tmp_path):
    import os
    import threading
    _, root = studio
    script_root = tmp_path / 'fake-worker'
    script_root.mkdir()
    (script_root / 'worker.py').write_text('import time\ntime.sleep(60)\n')
    monkeypatch.setattr(app, 'BASE', script_root)
    event = threading.Event()
    monkeypatch.setattr(app, 'shutdown_event', event)
    path = root / 'jobs' / ('e' * 32 + '.json')
    path.write_text('{}')
    work = root / 'parts' / ('e' * 32)
    work.mkdir()
    timer = threading.Timer(0.2, event.set)
    timer.start()
    try:
        assert app.execute_worker(path, dict(os.environ), work) == -2
    finally:
        timer.join()
