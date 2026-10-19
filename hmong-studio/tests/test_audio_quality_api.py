"""The selected cleanup and compute settings must affect the local audio path."""
import asyncio
import io
import math
from pathlib import Path
import struct
from unittest.mock import Mock
import wave
import pytest

from fastapi.responses import FileResponse
from fastapi.testclient import TestClient

import app


def tone(seconds=1):
    output = io.BytesIO()
    with wave.open(output, 'wb') as writer:
        writer.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        writer.writeframes(b''.join(struct.pack('<h', round(8000 * math.sin(i * .08)))
                                    for i in range(round(seconds * 24000))))
    return output.getvalue()


def payload(text='Nyob zoo.', **values):
    return {'text': text, 'dialect': 'mww', 'voice': 'hmong-white-female',
            'emotion': 'review', **values}


def test_noise_and_compute_enum_are_validated_before_spawning(monkeypatch):
    create = Mock(return_value={'id': 'test', 'status': 'running', 'progress': 0})
    monkeypatch.setattr(app.voice_jobs, 'create', create)
    client = TestClient(app.app)
    for values in ({'compute_mode': '30x'}, {'cleanup': 'magic'}):
        assert client.post('/api/speech/jobs', json=payload(**values)).status_code == 422
    create.assert_not_called()
    response = client.post('/api/speech/jobs', json=payload(compute_mode='fast', cleanup='strong'))
    assert response.status_code == 202
    settings = create.call_args.args[0]
    assert settings['compute_mode'] == 'fast' and settings['cleanup'] == 'strong'
    assert app.Speech(**payload()).compute_mode == 'standard'
    assert app.Speech(**payload()).cleanup == 'light'


def test_cleanup_off_keeps_exact_model_audio(monkeypatch):
    monkeypatch.setattr(app.cosy_engine, 'availability', lambda: {'ready': True})
    original = tone()
    infer = Mock(return_value=original)
    polish = Mock(side_effect=AssertionError('Off must not filter model audio'))
    monkeypatch.setattr(app.cosy_engine, 'synthesize', infer)
    monkeypatch.setattr(app.audio_clean, 'polish_audio', polish)
    response = TestClient(app.app).post('/api/speech', json=payload(cleanup='off'))
    assert response.status_code == 200 and response.content == original
    assert infer.call_args.kwargs == {}
    polish.assert_not_called()


def test_srt_passes_settings_to_each_cue_and_polishes_once_without_timing_shift(monkeypatch, tmp_path):
    monkeypatch.setattr(app.cosy_engine, 'availability', lambda: {'ready': True})
    calls = []

    def infer(text, reference, emotion, speed, **options):
        calls.append((text, options['compute_mode'], options['cleanup']))
        target = Path(options['output_path'])
        target.write_bytes(tone())
        options['progress']({'progress': 99, 'phase': 'complete',
                             'completed_units': 1, 'total_units': 1, 'generated_seconds': 1})
        return target

    monkeypatch.setattr(app.cosy_engine, 'synthesize', infer)
    polish = Mock(wraps=app.audio_clean.polish_audio)
    monkeypatch.setattr(app.audio_clean, 'polish_audio', polish)
    text = ('1\n00:00:00,200 --> 00:00:02,700\nNyob zoo.\n\n'
            '2\n00:00:03,000 --> 00:00:05,300\nKuv hais lus Hmoob.')
    events = []
    target = tmp_path / 'review.wav'
    response = asyncio.run(app.generate_speech(
        app.Speech(**payload(text, compute_mode='fast', cleanup='light')),
        output_path=target, progress=events.append))
    assert isinstance(response, FileResponse) and Path(response.path) == target
    assert calls == [('Nyob zoo.', 'fast', 'light'), ('Kuv hais lus Hmoob.', 'fast', 'light')]
    assert polish.call_count == 1
    assert polish.call_args.kwargs == {'level': 'light'}
    assert events[-1]['phase'] == 'cleanup' and events[-1]['progress'] == 99
    assert all(event['progress'] < 100 for event in events)
    with wave.open(str(target), 'rb') as reader:
        assert reader.getnframes() == 127200  # Exact 5.300-second SRT timeline.
        leading = struct.unpack('<' + 'h' * 4000, reader.readframes(4000))
        assert max(map(abs, leading)) < 8
        reader.setpos(6000)
        assert any(reader.readframes(2000))


def test_polishing_failure_returns_error_without_publishing_success(monkeypatch):
    monkeypatch.setattr(app.cosy_engine, 'availability', lambda: {'ready': True})
    monkeypatch.setattr(app.cosy_engine, 'synthesize', Mock(return_value=tone()))
    monkeypatch.setattr(app.audio_clean, 'polish_audio',
                        Mock(side_effect=RuntimeError('FFmpeg cannot process this audio')))
    response = TestClient(app.app).post('/api/speech', json=payload())
    assert response.status_code == 503
    assert 'FFmpeg' in response.json()['detail']


def test_fast_cpu_precision_reaches_runtime_status():
    state = app.voice_jobs._validated_runtime({
        'loaded': True, 'device': 'cpu', 'precision': 'float32_int8_flow',
        'reference_cache_entries': 1, 'compute_mode': 'fast'})
    assert state['precision'] == 'float32_int8_flow'
    assert state['compute_mode'] == 'fast'


@pytest.mark.parametrize('seconds,accepted', [(86400, True), (86401, False)])
def test_wav_metadata_allowance_keeps_exact_24_hour_limit(tmp_path, seconds, accepted):
    frames = 24000 * seconds
    data_bytes = frames * 2
    metadata = b'INFO' + b'ISFT' + struct.pack('<I', 4) + b'test'
    fmt = struct.pack('<4sIHHIIHH', b'fmt ', 16, 1, 1, 24000, 48000, 2, 16)
    chunks = fmt + b'LIST' + struct.pack('<I', len(metadata)) + metadata
    chunks += b'data' + struct.pack('<I', data_bytes)
    header = b'RIFF' + struct.pack('<I', 4 + len(chunks) + data_bytes) + b'WAVE' + chunks
    path = tmp_path / 'long-metadata.wav'
    with path.open('wb') as stream:
        stream.write(header)
        stream.truncate(len(header) + data_bytes)
    assert app.voice_jobs._valid_audio(path, 'audio/wav') is accepted
