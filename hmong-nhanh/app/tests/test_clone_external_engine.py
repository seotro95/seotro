"""External references remain the conditioning source regardless of their language."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys
import wave

import numpy as np
import pytest

import cloning_engine as engine


def reference(path, frequency):
    seconds, rate = 4, 24000
    values = .2 * np.sin(2 * np.pi * frequency * np.arange(seconds * rate) / rate)
    with wave.open(str(path), 'wb') as output:
        output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        output.writeframes((values * 32767).astype('<i2').tobytes())
    return path


@pytest.mark.parametrize('transcript', [
    'Some call me nature, others call me mother nature.',
    'Đây là giọng nói mẫu bằng tiếng Việt.',
    '这是原始参考声音。',
])
def test_reference_transcript_stays_in_its_original_language(tmp_path, transcript):
    sample = reference(tmp_path / 'outside.wav', 180)
    prepared = {'seconds': 4, 'text': transcript + ' '}
    with patch.object(engine, 'availability', return_value={'ready': True}), \
         patch.object(engine, '_load_model') as model, \
         patch.object(engine, '_prepare_reference', return_value=prepared) as prepare, \
         patch.object(engine, '_infer_one', return_value=engine._wav([.2] * 2400, 24000)) as infer:
        engine.synthesize('Kuv hais lus Hmoob rau koj.', 1, sample, transcript, quality='quality')
    assert prepare.call_args.args[1] == sample
    assert prepare.call_args.args[2] == transcript
    assert infer.call_args.args[1] is prepared
    assert infer.call_args.args[-1] == 32


def test_changing_external_audio_changes_conditioning_and_never_reuses_default(tmp_path, monkeypatch):
    torch = pytest.importorskip('torch')
    monkeypatch.setattr(engine, '_reference', None)
    monkeypatch.setattr(engine, '_reference_key', None)
    monkeypatch.setattr(engine, '_model_key', ('local-hmong-checkpoint',))
    # Compute a real frequency-dependent spectrogram rather than using the same
    # dummy mel for both voices. No neural voice-similarity claim is made here.
    def spectrogram(audio):
        return torch.stft(audio, n_fft=512, hop_length=256,
                          window=torch.hann_window(512), return_complex=True).abs()[:, :100, :]
    neural_model = SimpleNamespace(mel_spec=Mock(side_effect=spectrogram), sample=Mock())
    model = SimpleNamespace(device='cpu', ema_model=neural_model)
    first_path = reference(tmp_path / 'external-a.wav', 160)
    second_path = reference(tmp_path / 'external-b.wav', 430)
    text = 'This reference is not spoken in Hmong.'
    first = engine._prepare_reference(model, first_path, text, engine._reference_identity(first_path, text))
    assert engine._prepare_reference(model, first_path, text, engine._reference_identity(first_path, text)) is first
    second = engine._prepare_reference(model, second_path, text, engine._reference_identity(second_path, text))
    assert not torch.equal(first['audio'][0], second['audio'][0])
    assert not torch.equal(first['conditioned_model'].mel, second['conditioned_model'].mel)
    assert neural_model.mel_spec.call_count == 2
    second['conditioned_model'].sample(cond=torch.zeros(1, 100), text=['Nyob zoo'], steps=32)
    assert neural_model.sample.call_args.kwargs['cond'] is second['conditioned_model'].mel
    # Replacing a reference in place must invalidate its cached conditioning too.
    reference(second_path, 290)
    replaced = engine._prepare_reference(model, second_path, text, engine._reference_identity(second_path, text))
    assert replaced is not second
    assert not torch.equal(replaced['conditioned_model'].mel, second['conditioned_model'].mel)
    assert neural_model.mel_spec.call_count == 3


def test_missing_external_reference_fails_without_loading_another_voice(tmp_path):
    with patch.object(engine, '_load_model') as load:
        with pytest.raises(engine.CloningError, match='mẫu WAV'):
            engine.synthesize('Nyob zoo.', 1, tmp_path / 'missing.wav', 'An exact English transcript.')
    load.assert_not_called()


def test_short_subtitle_duration_honours_speed_instead_of_forcing_point_three(monkeypatch):
    calls = []
    def upstream(*args, **kwargs):
        calls.append(kwargs)
        return iter([([.2] * 240, 24000, None)])
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(inference_mode=nullcontext))
    monkeypatch.setitem(sys.modules, 'f5_tts.infer.utils_infer', SimpleNamespace(infer_batch_process=upstream))
    prepared = {'audio': ('waveform', 24000), 'text': 'Exact reference transcript. ',
                'conditioned_model': object(), 'seconds': 4}
    model = SimpleNamespace(vocoder=object(), device='cpu', mel_spec_type='vocos')
    for speed in (.5, 1, 2):
        engine._infer_one(model, prepared, 'Nyob zoo', speed, 16)
    # F5 fix_duration includes the reference portion as well as the new speech.
    ref_frames = 4 * 24000 // 256
    generated = [int(call['fix_duration'] * 24000 / 256) - ref_frames for call in calls]
    assert generated[0] > generated[1] > generated[2] > 0
    assert abs(generated[0] / generated[1] - 2) < .05
    assert abs(generated[1] / generated[2] - 2) < .05
    calls.clear()
    engine._infer_one(model, prepared, 'Kuv hais lus Hmoob rau koj.', 1, 16)
    assert 'fix_duration' not in calls[0]
