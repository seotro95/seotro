import asyncio
import math
from pathlib import Path
import struct
import tempfile
import wave

from fastapi.testclient import TestClient
import pytest

import app


def test_ultra_job_keeps_hmong_text_and_passes_srt_estimate(monkeypatch):
    captured = {}
    def create(payload, **options):
        captured.update(payload=payload, options=options)
        return {'id': 'example', 'status': 'running'}
    monkeypatch.setattr(app.voice_jobs, 'create', create)
    text = '1\n00:00:00,200 --> 00:00:02,700\nKuv hlub Hmoob Dawb.\n'
    with TestClient(app.app) as client:
        response = client.post('/api/speech/jobs', json={
            'text': text, 'dialect': 'mww', 'voice': 'hmong-white-female', 'compute_mode': 'ultra'})
        assert response.status_code == 202
        assert captured['payload']['text'] == text
        assert captured['payload']['compute_mode'] == 'ultra'
        assert captured['options']['estimated_total_seconds'] == 2.7
        assert client.post('/api/speech/jobs', json={
            'text': 'Nyob zoo.', 'dialect': 'mww', 'compute_mode': 'turbo'}).status_code == 422


def test_pause_resume_api_calls_owned_job_controls(monkeypatch):
    calls = []
    async def pause(job_id):
        calls.append(('pause', job_id))
        return {'id': job_id, 'status': 'running', 'pause_requested': True}
    async def resume(job_id):
        calls.append(('resume', job_id))
        return {'id': job_id, 'status': 'running', 'pause_requested': False}
    monkeypatch.setattr(app.voice_jobs, 'pause', pause)
    monkeypatch.setattr(app.voice_jobs, 'resume', resume)
    with TestClient(app.app) as client:
        assert client.post('/api/speech/jobs/sample/pause').json()['pause_requested'] is True
        assert client.post('/api/speech/jobs/sample/resume').json()['pause_requested'] is False
    assert calls == [('pause', 'sample'), ('resume', 'sample')]


@pytest.mark.skipif(not app.audio_export.shutil.which('ffmpeg') or
                    not app.audio_export.shutil.which('ffprobe'), reason='FFmpeg required')
def test_real_mp3_http_download_and_ranges_keep_lossless_wav(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'audio.bin'
        with wave.open(str(path), 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(24000)
            writer.writeframes(b''.join(struct.pack('<h', int(6000 * math.sin(i * .1))) for i in range(24000)))
        original = path.read_bytes()
        job = {'status': 'completed', 'media_type': 'audio/wav',
               'temp': type('Folder', (), {'name': directory})()}
        monkeypatch.setattr(app.voice_jobs, 'get', lambda key: job)
        with TestClient(app.app) as client:
            response = client.get('/api/speech/jobs/sample/audio?format=mp3')
            assert response.status_code == 200
            assert response.headers['content-type'].startswith('audio/mpeg')
            assert len(response.content) > 100
            ranged = client.get('/api/speech/jobs/sample/audio?format=mp3', headers={'Range': 'bytes=0-99'})
            assert ranged.status_code == 206 and ranged.content == response.content[:100]
            assert client.head('/api/speech/jobs/sample/audio?format=mp3').status_code == 200
            assert client.get('/api/speech/jobs/sample/audio?format=wav').content == original
            assert client.get('/api/speech/jobs/sample/audio?format=invalid').status_code == 422
            assert job['_downloads_active'] == 0
        assert path.read_bytes() == original


def test_cancelled_download_releases_result_pin(tmp_path):
    path = tmp_path / 'voice.wav'
    path.write_bytes(b'example download body')
    job = {}
    response = app.DownloadResponse(path, job=job)
    assert job['_downloads_active'] == 1
    async def scenario():
        started = asyncio.Event()
        waiting = asyncio.Event()
        async def send(message):
            started.set()
            await waiting.wait()
        async def receive():
            await waiting.wait()
        task = asyncio.create_task(response(
            {'type': 'http', 'method': 'GET', 'headers': [], 'asgi': {'spec_version': '2.4'}}, receive, send))
        await asyncio.wait_for(started.wait(), 3)
        assert job['_downloads_active'] == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())
    assert job['_downloads_active'] == 0
