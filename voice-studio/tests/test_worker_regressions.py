import importlib
import wave
from pathlib import Path

import pytest

from narration import Segment


def pcm(path, *, rate=24000, channels=1, frames=2400):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(b'\x10\x00' * frames * channels)


def worker_module(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    return importlib.import_module('worker')


@pytest.mark.parametrize('damage', ['truncated', 'wrong_rate', 'stereo'])
def test_resume_regenerates_damaged_checkpoint_instead_of_losing_words(tmp_path, monkeypatch, damage):
    worker = worker_module(tmp_path, monkeypatch)
    part = tmp_path / '000000.wav'
    pcm(part, rate=48000 if damage == 'wrong_rate' else 24000,
        channels=2 if damage == 'stereo' else 1)
    if damage == 'truncated':
        part.write_bytes(part.read_bytes()[:-1000])  # Keep the original full-frame WAV header.
    calls = []
    def synth(text, output):
        calls.append(text)
        pcm(output)
    worker.prepare_chunk({'engine': 'vieneu', 'speed': 1}, Segment(text='Không được bỏ mất lời.'), 0, tmp_path, synth)
    assert calls == ['Không được bỏ mất lời.']
    with wave.open(str(part)) as audio:
        assert audio.getframerate() == 24000 and audio.getnchannels() == 1
        assert len(audio.readframes(audio.getnframes())) == audio.getnframes() * 2


def test_corrupt_model_output_retries_same_text_and_keeps_valid_retry(tmp_path, monkeypatch):
    worker = worker_module(tmp_path, monkeypatch)
    calls = []
    def synth(text, output):
        calls.append(text)
        if len(calls) == 1:
            Path(output).write_bytes(b'RIFFbroken')
        else:
            pcm(output)
    worker.prepare_chunk({'engine': 'vieneu', 'speed': 1}, Segment(text='Xin chào.'), 0, tmp_path, synth)
    assert calls == ['Xin chào.', 'Xin chào.']
    assert worker.valid_checkpoint(tmp_path / '000000.wav')


def test_failed_output_cleans_normalized_temporary_audio(tmp_path, monkeypatch):
    worker = worker_module(tmp_path, monkeypatch)
    def synth(text, output):
        with wave.open(str(output), 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(24000)
            audio.writeframes(b'\0\0' * 2400)
    with pytest.raises(ValueError, match='sau 3 lần'):
        worker.prepare_chunk({'engine': 'vieneu', 'speed': 1}, Segment(text='Xin chào.'), 0, tmp_path, synth)
    assert not (tmp_path / 'normalized-000000.wav').exists()
    assert not (tmp_path / 'raw-000000.wav').exists()


def test_missing_reference_does_not_leave_an_empty_temp_file(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    from local_vieneu import LocalVieneu
    missing = tmp_path / 'missing.wav'
    assert LocalVieneu._preclean_reference_audio(missing) == str(missing)
    assert list((tmp_path / 'tmp').iterdir()) == []


def test_four_parallel_workers_preserve_order_and_rebuild_pool_when_count_changes(tmp_path, monkeypatch):
    import json
    import time
    from concurrent.futures import ThreadPoolExecutor
    import numpy as np
    import soundfile as sf
    worker = worker_module(tmp_path, monkeypatch)
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    monkeypatch.setattr(worker, '_nano_pool', None)
    monkeypatch.setattr(worker, '_nano_pool_workers', None)
    (tmp_path / 'audio').mkdir()
    pool_sizes = []
    pools = []
    def pool_factory(max_workers, **kwargs):
        pool_sizes.append(max_workers)
        pool = ThreadPoolExecutor(max_workers=max_workers)
        pools.append(pool)
        return pool
    monkeypatch.setattr(worker, 'ProcessPoolExecutor', pool_factory)
    def synth(text, output):
        index = ['Một.', 'Hai.', 'Ba.', 'Bốn.'].index(text)
        time.sleep(.01 * (3 - index))
        sf.write(output, np.full(2400, .1 * (index + 1)), 24000)
    monkeypatch.setattr(worker, 'get_synthesizer', lambda job: synth)
    job = {'id': 'four', 'text': 'Một. Hai. Ba. Bốn.', 'engine': 'vieneu_nano', 'nano_parallel': 4,
           'format': 'wav', 'speed': 1, 'paragraph_pause': 0}
    try:
        worker.render(job)
        samples, _ = sf.read(tmp_path / 'audio' / 'four.wav')
        for index in range(4):
            assert abs(samples[index*2400:(index+1)*2400].mean() - .1*(index+1)) < .001
        worker.render({**job, 'id': 'two', 'nano_parallel': 2})
        assert pool_sizes == [4, 2]
        assert pools[0]._shutdown
        result = json.loads((tmp_path / 'parts' / 'two' / 'result.json').read_text())
        assert result['completed'] == 4
    finally:
        worker.close_nano_pool()
