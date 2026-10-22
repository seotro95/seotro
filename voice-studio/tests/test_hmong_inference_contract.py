"""Regression checks for text loss and forced-short Hmong utterances.

The lightweight sampler probes the adapter contract, not pronunciation quality.
Actual checkpoint inference is covered by the native portable smoke test.
"""
import string
from types import SimpleNamespace

import pytest

from hmong_engine import EngineError, SpeechEngine
from hmong_text import HmongTextError


def test_unsupported_script_fails_before_loading_a_large_model(monkeypatch):
    engine = SpeechEngine()
    monkeypatch.setattr(engine, '_load', lambda: pytest.fail('Must validate text before loading'))
    with pytest.raises(EngineError, match='RPA'):
        engine.synthesize('Nyob zoo ꟽ ࠁ.', '/missing/reference.wav', 'Nyob zoo.')


def adapter_probe():
    torch = pytest.importorskip('torch')
    captured = []
    class Sampler:
        def sample(self, **kwargs):
            captured.append(kwargs)
            return torch.ones((1, kwargs['duration'], 100)), None
    class Vocoder:
        def decode(self, mel):
            return torch.ones((1, mel.shape[-1] * 256)) * .1
    model = SimpleNamespace(ema_model=Sampler(), vocoder=Vocoder(),
                            vocabulary=dict.fromkeys(string.printable))
    return torch, model, captured


def test_short_greeting_is_not_forced_into_half_a_second():
    from hmong_f5 import infer_batch
    torch, model, captured = adapter_probe()
    reference = (torch.ones((1, 5 * 24000)) * .1, 24000)
    audio, rate = infer_batch(reference, 'Kuv zoo siab tau ntsib nej hnub no.',
                             'Nyob zoo.', model, steps=16, speed=1, device='cpu')
    assert rate == 24000 and len(audio) / rate > 3
    assert captured[0]['steps'] == 16
    assert captured[0]['text'] == ['Kuv zoo siab tau ntsib nej hnub no. Nyob zoo.']


def test_vocab_unknown_is_rejected_instead_of_becoming_space():
    from hmong_f5 import infer_batch
    torch, model, captured = adapter_probe()
    model.vocabulary.pop('@')
    with pytest.raises(HmongTextError, match='ký tự'):
        infer_batch((torch.ones((1, 120000)) * .1, 24000), 'Nyob zoo.',
                    'Kuv @ zoo.', model, steps=16, speed=1, device='cpu')
    assert not captured


def test_natural_precision_is_preserved_and_draft_fallback_is_cached(tmp_path, monkeypatch):
    pytest.importorskip('torch')
    import hmong_engine
    import hmong_f5
    monkeypatch.setenv('HMOOB_DEVICE', 'cpu')
    monkeypatch.setenv('HMOOB_PRECISION', 'auto')
    monkeypatch.setattr(hmong_engine, 'model_directory', lambda: tmp_path)
    monkeypatch.setattr(hmong_engine, 'verify_models', lambda root: ('verified',))
    calls = []
    def loader(root, device, progress=None, precision=None):
        calls.append(precision)
        if precision == 'int8':
            raise NotImplementedError('CPU quantization unavailable')
        return SimpleNamespace(precision='fp32')
    monkeypatch.setattr(hmong_f5, 'load_local_model', loader)
    engine = SpeechEngine()
    natural = engine._load('fast')
    assert natural.precision == 'fp32' and calls == ['auto']
    assert engine._load('standard') is natural and calls == ['auto']
    draft = engine._load('turbo')
    assert draft.precision == 'fp32' and calls == ['auto', 'int8', 'fp32']
    assert engine._load('turbo') is draft and calls == ['auto', 'int8', 'fp32']
    monkeypatch.setenv('HMOOB_PRECISION', 'fp32')
    engine._load('turbo')
    assert calls[-1] == 'fp32'


def test_explicit_fp32_override_also_applies_to_cuda(monkeypatch):
    torch = pytest.importorskip('torch')
    safetensors = pytest.importorskip('safetensors.torch')
    from hmong_f5 import _load_ema_checkpoint
    conversions = []
    class Network:
        def to(self, target):
            conversions.append(target)
            return self
        def load_state_dict(self, state):
            assert state == {}
    monkeypatch.setattr(safetensors, 'load_file', lambda *args, **kwargs: {})
    _load_ema_checkpoint(Network(), 'not-read.safetensors', 'cuda', force_fp32=True)
    assert conversions == [torch.float32, 'cuda']
