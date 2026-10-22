import importlib

import numpy as np
import pytest
import soundfile as sf

from prepare_models import validate_sample
from test_app import studio
from unittest.mock import patch


@pytest.mark.parametrize('samples', [np.zeros(2400), np.array([]), np.full(2400, np.nan), np.full(2400, np.inf)])
def test_preparation_rejects_invalid_model_output(tmp_path, samples):
    path = tmp_path / 'check.wav'
    sf.write(path, samples, 24000, subtype='FLOAT')
    with pytest.raises(ValueError, match='chưa đánh dấu'):
        validate_sample(path)


def test_preparation_accepts_real_waveform(tmp_path):
    path = tmp_path / 'check.wav'
    sf.write(path, .2 * np.sin(np.arange(2400) * .1), 24000)
    validate_sample(path)


@pytest.mark.parametrize('delivery', ['review', 'documentary', 'story'])
def test_delivery_is_saved_for_worker_and_resume(studio, delivery):
    client, root = studio
    (root / 'models' / 'vieneu.ready').touch()
    with patch('app.executor.submit'):
        result = client.post('/api/speech', json={'text': 'Đây là sản phẩm hôm nay.', 'voice_id': 'vi-maianh', 'delivery': delivery})
    assert result.status_code == 202
    assert result.json()['delivery'] == delivery
    assert client.get('/api/jobs/' + result.json()['id']).json()['delivery'] == delivery


def test_nonfinite_generation_is_retried_before_pcm_conversion(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    from narration import Segment
    calls = []
    def synth(text, path):
        calls.append(text)
        samples = np.full(2400, np.nan) if len(calls) == 1 else .2 * np.sin(np.arange(2400) * .1)
        sf.write(path, samples, 24000, subtype='FLOAT')
    worker.prepare_chunk({'engine': 'vieneu', 'speed': 1}, Segment(text='Xin chào.'), 0, tmp_path, synth)
    assert len(calls) == 2
    samples, _ = sf.read(tmp_path / '000000.wav')
    assert np.all(np.isfinite(samples)) and np.max(np.abs(samples)) > .1


def test_clone_rejects_silence_and_leaves_no_profile(studio):
    import io
    import wave
    client, root = studio
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(b'\x00\x00' * 24000 * 4)
    result = client.post('/api/voices/clone', data={'name': 'Silent', 'language': 'vi', 'consent': 'true'}, files={'file': ('sample.wav', buf.getvalue(), 'audio/wav')})
    assert result.status_code == 422 and 'im lặng' in result.json()['detail']
    assert list((root / 'voices').iterdir()) == []


def test_four_nano_workers_are_saved_and_invalid_counts_rejected(studio):
    client, root = studio
    (root / 'models' / 'vieneu_nano.ready').touch()
    with patch('app.executor.submit'):
        result = client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'nano-minhquan', 'nano_parallel': 4, 'nano_threads': 1})
    assert result.status_code == 202
    assert result.json()['nano_parallel'] == 4 and result.json()['nano_threads'] == 1
    assert client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'nano-minhquan', 'nano_parallel': 5}).status_code == 422
