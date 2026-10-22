"""Nano enrollment is reusable and bad model samples never become checkpoints."""
import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import soundfile as sf
import pytest


def worker_module(monkeypatch, root):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(root))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', root)
    return worker


def test_nano_clone_encodes_once_and_reuses_voice_tensors(tmp_path, monkeypatch):
    worker = worker_module(monkeypatch, tmp_path)
    import local_vieneu
    spk, style = np.zeros(192), np.zeros((50, 256))
    model = SimpleNamespace(encode_reference=Mock(return_value=(spk, style)), infer=Mock(return_value=np.ones(240)), save=Mock())
    factory = Mock(return_value=model)
    monkeypatch.setattr(local_vieneu, 'LocalNano', factory)
    synth = worker.load_synthesizer({'engine': 'vieneu_nano', 'voice_id': 'clone', 'speaker': None, 'nano_steps': 4, 'nano_threads': 2})
    synth('Câu thứ nhất.', tmp_path/'one.wav')
    synth('Câu thứ hai.', tmp_path/'two.wav')
    model.encode_reference.assert_called_once_with(str(tmp_path/'voices/clone.wav'), denoise=False)
    voice = model.infer.call_args_list[0].kwargs['voice']
    assert voice['speaker_emb'] is spk and voice['style'] is style
    assert model.infer.call_args_list[1].kwargs['voice'] is voice
    assert model.infer.call_args.kwargs['steps'] == 4


def test_nano_presets_do_not_enroll_reference(tmp_path, monkeypatch):
    worker = worker_module(monkeypatch, tmp_path)
    import local_vieneu
    model = SimpleNamespace(encode_reference=Mock(), infer=Mock(return_value=np.ones(240)), save=Mock())
    monkeypatch.setattr(local_vieneu, 'LocalNano', Mock(return_value=model))
    worker.load_synthesizer({'engine': 'vieneu_nano', 'speaker': 'Minh Quân'})('Xin chào.', tmp_path/'one.wav')
    model.encode_reference.assert_not_called()
    assert model.infer.call_args.kwargs['voice'] == 'Minh Quân'


def test_nano_reference_cleaning_stays_local_and_is_removed_on_failure(tmp_path, monkeypatch):
    worker_module(monkeypatch, tmp_path)
    from local_vieneu import LocalNano
    model = LocalNano.__new__(LocalNano)
    sample = tmp_path/'reference.wav'
    sf.write(sample, np.sin(np.arange(24000)*.1)*.2, 24000)
    cleaned = []
    def enroll(path, **kwargs):
        cleaned.append(path)
        assert str(tmp_path/'tmp') in path and Path(path).is_file()
        raise ValueError('test enrollment failure')
    model.engine = SimpleNamespace(prepare_reference=enroll)
    with pytest.raises(ValueError, match='test enrollment failure'):
        model.encode_reference(sample, denoise=False)
    assert sample.is_file() and cleaned and not Path(cleaned[0]).exists()


@pytest.mark.parametrize('bad', ['nan', 'broken'])
def test_invalid_model_wav_is_retried_before_cache(tmp_path, monkeypatch, bad):
    worker = worker_module(monkeypatch, tmp_path)
    from narration import Segment
    calls = []
    def synth(text, output):
        calls.append(text)
        if len(calls) == 1:
            if bad == 'nan':
                sf.write(output, np.full(2400, np.nan), 24000, subtype='FLOAT')
            else:
                output.write_bytes(b'invalid wav')
        else:
            sf.write(output, np.sin(np.arange(2400)*.1)*.2, 24000)
    worker.prepare_chunk({'engine':'vieneu_nano', 'speed':1}, Segment(text='Xin chào.'), 0, tmp_path, synth)
    assert calls == ['Xin chào.'] * 2
    audio, _ = sf.read(tmp_path/'000000.wav')
    assert np.isfinite(audio).all() and np.max(np.abs(audio)) > .1
