"""Long-script boundaries, timed routing and streaming downloads stay explicit."""
import asyncio
from pathlib import Path
import struct
from unittest.mock import Mock

from fastapi.responses import FileResponse
from fastapi.testclient import TestClient

import app


def payload(text, **values):
    return {'text': text, 'dialect': 'mww', 'voice': 'hmong-white-female',
            'emotion': 'review', **values}


def test_million_character_job_is_accepted_but_extra_character_never_starts(monkeypatch):
    create = Mock(return_value={'id': 'test', 'status': 'running', 'progress': 0})
    monkeypatch.setattr(app.voice_jobs, 'create', create)
    client = TestClient(app.app)
    text = ('Hmoob ' * 166667)[:1_000_000]
    response = client.post('/api/speech/jobs', json=payload(text))
    assert response.status_code == 202, response.text
    assert create.call_count == 1
    assert create.call_args.args[0]['text'] == text
    assert create.call_args.args[0]['input_format'] == 'auto'
    assert client.post('/api/speech/jobs', json=payload(text + 'x')).status_code == 422
    assert create.call_count == 1


def test_bad_or_overlapping_srt_never_starts_worker(monkeypatch):
    create = Mock()
    monkeypatch.setattr(app.voice_jobs, 'create', create)
    client = TestClient(app.app)
    for text in (
        '00:00:02,000 --> 00:00:01,000\nNyob zoo.',
        '00:00:00,000 --> 00:00:02,000\nNyob zoo.\n\n'
        '00:00:01,000 --> 00:00:03,000\nKuv hais lus Hmoob.',
        '00:99:00,000 --> 01:00:00,000\nNyob zoo.',
    ):
        response = client.post('/api/speech/jobs', json=payload(text, input_format='srt'))
        assert response.status_code == 422, response.text
    create.assert_not_called()


def test_srt_uses_timed_renderer_and_never_speaks_timestamps(monkeypatch):
    monkeypatch.setattr(app.cosy_engine, 'availability', lambda: {'ready': True})
    render = Mock(return_value=b'RIFF-timed-audio')
    plain = Mock()
    monkeypatch.setattr(app.review_script, 'render_timeline', render)
    monkeypatch.setattr(app.cosy_engine, 'synthesize', plain)
    text = '1\n00:00:00,200 --> 00:00:02,700\nNyob zoo.\n'
    response = TestClient(app.app).post('/api/speech', json=payload(text, cleanup='off'))
    assert response.status_code == 200
    script, reference, emotion, speed = render.call_args.args
    assert script.timed and script.cues[0].text == 'Nyob zoo.'
    assert script.cues[0].start == .2 and script.cues[0].end == 2.7
    assert reference.name == 'hmong-white-female.mp3'
    assert emotion == 'review' and speed == 1
    plain.assert_not_called()


def test_long_timeline_uses_job_api_even_when_script_text_is_short(monkeypatch):
    render = Mock()
    monkeypatch.setattr(app.review_script, 'render_timeline', render)
    text = '23:59:57,000 --> 24:00:00,000\nNyob zoo.'
    response = TestClient(app.app).post('/api/speech', json=payload(text))
    assert response.status_code == 413
    render.assert_not_called()


def test_local_job_writes_to_file_instead_of_materializing_response(monkeypatch, tmp_path):
    monkeypatch.setattr(app.cosy_engine, 'availability', lambda: {'ready': True})
    path = tmp_path / 'audio.bin'
    progress = Mock()

    def synthesize(text, reference, emotion, speed, **options):
        assert len(text) == 10001
        assert options['output_path'] == path
        options['progress']({'progress': 50, 'phase': 'synthesis'})
        path.write_bytes(b'file-backed-result')
        return path

    monkeypatch.setattr(app.cosy_engine, 'synthesize', synthesize)
    response = asyncio.run(app.generate_speech(app.Speech(**payload('x' * 10001, cleanup='off')),
                                             progress=progress, output_path=path))
    assert isinstance(response, FileResponse)
    assert Path(response.path) == path
    assert not hasattr(response, 'body')
    progress.assert_called_once_with({'progress': 50, 'phase': 'synthesis'})
    direct = TestClient(app.app).post('/api/speech', json=payload('x' * 10001))
    assert direct.status_code == 413


def test_long_audio_download_supports_range_without_reading_entire_wav(monkeypatch, tmp_path):
    frames = 24000 * 3600
    size = frames * 2
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', size + 36, b'WAVE',
                         b'fmt ', 16, 1, 1, 24000, 48000, 2, 16, b'data', size)
    folder = tmp_path / 'job'
    folder.mkdir()
    path = folder / 'audio.bin'
    with path.open('wb') as stream:
        stream.write(header)
        stream.truncate(size + 44)
    monkeypatch.setattr(app.voice_jobs, 'get', lambda job_id: {
        'status': 'completed', 'temp': type('Folder', (), {'name': str(folder)})(),
        'media_type': 'audio/wav',
    })
    response = TestClient(app.app).get('/api/speech/jobs/test/audio',
                                     headers={'Range': 'bytes=0-43'})
    assert response.status_code == 206
    assert response.content == header
    assert response.headers['content-range'] == f'bytes 0-43/{size + 44}'
    assert response.headers['content-length'] == '44'
    head = TestClient(app.app).head('/api/speech/jobs/test/audio')
    assert head.status_code == 200
    assert head.headers['content-length'] == str(size + 44)
    assert head.content == b''
