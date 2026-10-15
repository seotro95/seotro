import importlib
import json
import os
import wave

import numpy as np
import soundfile as sf

import app
from test_app import studio  # noqa: F401


def test_same_model_configuration_is_reused_and_switch_reloads(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, '_cached_key', None)
    monkeypatch.setattr(worker, '_cached_synth', None)
    loaded = []
    def load(job):
        loaded.append(job['quality'])
        return object()
    monkeypatch.setattr(worker, 'load_synthesizer', load)
    job = {'engine': 'vieneu', 'voice_id': 'vi-maianh', 'speaker': 'Mai Anh', 'language': 'vi', 'quality': 'standard'}
    first = worker.get_synthesizer(job)
    assert worker.get_synthesizer({**job, 'text': 'Nội dung khác'}) is first
    assert worker.get_synthesizer({**job, 'quality': 'fast'}) is not first
    assert loaded == ['standard', 'fast']


def test_native_audio_path_resamples_without_spawning_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    raw, output = tmp_path / 'raw.wav', tmp_path / 'out.wav'
    x = (np.sin(np.arange(48000) * (2 * np.pi * 440 / 48000)) * 0.3).astype('float32')
    sf.write(raw, np.column_stack((x, x)), 48000)
    def forbidden(*args, **kwargs):
        raise AssertionError('Natural-speed audio must not spawn FFmpeg')
    monkeypatch.setattr(worker.subprocess, 'run', forbidden)
    worker.normalize_audio(raw, output, 1, 1)
    with wave.open(str(output)) as audio:
        assert audio.getnchannels() == 1 and audio.getframerate() == 24000
        assert audio.getnframes() == 24000 and audio.getsampwidth() == 2
    y, rate = sf.read(output)
    assert np.max(np.abs(y)) > 0.2


def test_serial_jobs_use_same_live_worker_process(studio, monkeypatch, tmp_path):
    _, root = studio
    fake = tmp_path / 'runtime'
    fake.mkdir()
    (fake / 'worker.py').write_text('''import json,os,sys
from pathlib import Path
root=Path(os.environ['VOICE_STUDIO_DATA_DIR'])
for line in sys.stdin:
 p=Path(line.strip())
 work=root/'parts'/p.stem
 (work/'worker-done.json').write_text(json.dumps({'code':0,'pid':os.getpid()}))
''')
    monkeypatch.setattr(app, 'BASE', fake)
    env = dict(os.environ, VOICE_STUDIO_DATA_DIR=str(root))
    pids = []
    for ident in ['a' * 32, 'b' * 32]:
        path = root / 'jobs' / (ident + '.json')
        path.write_text(json.dumps({'id': ident, 'status': 'done'}))
        work = root / 'parts' / ident
        work.mkdir()
        assert app.execute_worker(path, env, work) == 0
        pids.append(json.loads((work / 'worker-done.json').read_text())['pid'])
    assert pids[0] == pids[1]
    assert app.warm_worker.poll() is None
    app.close_warm_worker()
    assert app.warm_worker is None


def test_auto_mode_falls_back_and_nano_is_explicit(studio, monkeypatch):
    from unittest.mock import patch
    client, root = studio
    (root / 'models' / 'vieneu.ready').touch()
    monkeypatch.setattr(app, 'supports_int8', lambda: False)
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'vi-maianh'})
        assert response.status_code == 202 and response.json()['quality'] == 'standard'
        assert response.json()['speaker'] == 'Mai Anh'
        assert client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'nano-minhquan'}).status_code == 503
        (root / 'models' / 'vieneu_nano.ready').touch()
        response = client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'nano-minhquan'})
        assert response.status_code == 202 and response.json()['engine'] == 'vieneu_nano'
