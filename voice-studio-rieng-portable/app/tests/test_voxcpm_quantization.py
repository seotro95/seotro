"""Experimental quantization safety on tiny CPU models, no downloaded weights."""
from types import SimpleNamespace

import pytest

torch = pytest.importorskip('torch')
from voxcpm_quantization import quantize_cpu_language_models


class TinyTTS(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.base_lm = torch.nn.Sequential(torch.nn.Embedding(32, 16),
                                          torch.nn.Linear(16, 16), torch.nn.ReLU())
        self.residual_lm = torch.nn.Sequential(torch.nn.Linear(16, 16))
        self.audio_vae = torch.nn.Linear(16, 16)
        self.diffusion = torch.nn.Linear(16, 16)


def test_only_language_model_linear_layers_change_and_originals_survive():
    torch.manual_seed(73)
    model = TinyTTS()
    original = {name: module for name, module in model.named_children()}
    weights = {name: value.clone() for name, value in model.state_dict().items()}
    report = quantize_cpu_language_models(SimpleNamespace(tts_model=model))
    assert report['enabled'] and report['linear_layers'] == 2
    assert isinstance(model.base_lm[0], torch.nn.Embedding)
    assert isinstance(model.base_lm[1], torch.nn.quantized.dynamic.Linear)
    assert isinstance(model.residual_lm[0], torch.nn.quantized.dynamic.Linear)
    assert model.audio_vae is original['audio_vae']
    assert model.diffusion is original['diffusion']
    assert model.base_lm is not original['base_lm']
    assert original['base_lm'].training and original['residual_lm'].training
    torch.testing.assert_close(original['base_lm'][1].weight, weights['base_lm.1.weight'])
    assert quantize_cpu_language_models(model)['reason'] == 'already_quantized'


def test_second_model_failure_does_not_replace_either_model(monkeypatch):
    model = TinyTTS()
    base, residual = model.base_lm, model.residual_lm
    original = torch.ao.quantization.quantize_dynamic
    def fail_second(lm, *args, **options):
        if lm is residual:
            raise RuntimeError('synthetic unsupported residual')
        return original(lm, *args, **options)
    monkeypatch.setattr(torch.ao.quantization, 'quantize_dynamic', fail_second)
    report = quantize_cpu_language_models(model)
    assert not report['enabled'] and report['reason'] == 'quantization_failed'
    assert model.base_lm is base and model.residual_lm is residual


def test_partial_conversion_is_rejected_atomically_and_engine_restored(monkeypatch):
    model = TinyTTS()
    base, residual = model.base_lm, model.residual_lm
    engine = torch.backends.quantized.engine
    # Returning a clone without converting all Linear layers cannot masquerade
    # as compact inference. Neither live LM may change after this failure.
    import copy
    monkeypatch.setattr(torch.ao.quantization,'quantize_dynamic',lambda lm,*a,**kw:copy.deepcopy(lm))
    status = quantize_cpu_language_models(model)
    assert status['enabled'] is False and status['reason']=='quantization_failed'
    assert model.base_lm is base and model.residual_lm is residual
    assert torch.backends.quantized.engine==engine


def test_missing_x86_engine_leaves_original_models_unchanged(monkeypatch):
    model = TinyTTS()
    base, residual = model.base_lm, model.residual_lm
    monkeypatch.setattr(torch.backends.quantized._SupportedQEnginesProp,'__get__',
                        lambda self,obj,objtype=None:['none'])
    monkeypatch.setattr(torch.backends.quantized,'engine','none')
    status = quantize_cpu_language_models(model)
    assert status['enabled'] is False and status['reason']=='x86_quantization_unavailable'
    assert model.base_lm is base and model.residual_lm is residual


def test_out_of_memory_during_copy_preserves_both_language_models(monkeypatch):
    model = TinyTTS()
    base, residual = model.base_lm, model.residual_lm
    def fail(*a,**kw):raise MemoryError('synthetic allocation failure')
    monkeypatch.setattr(torch.ao.quantization,'quantize_dynamic',fail)
    status = quantize_cpu_language_models(model)
    assert status['enabled'] is False and status['error_type']=='MemoryError'
    assert model.base_lm is base and model.residual_lm is residual


def test_unsupported_and_non_fp32_models_unchanged():
    assert quantize_cpu_language_models(object())['reason'] == 'unsupported_model'
    model = TinyTTS().double()
    original = model.base_lm
    assert quantize_cpu_language_models(model)['reason'] == 'cpu_fp32_only'
    assert model.base_lm is original


def test_quantized_attention_accepts_active_kv_method_after_deep_copy():
    pytest.importorskip('voxcpm')
    from voxcpm.modules.minicpm4.model import MiniCPMAttention
    from voxcpm_acceleration import enable_active_kv_attention
    config = SimpleNamespace(hidden_size=64, num_attention_heads=4,
                             num_key_value_heads=2, max_position_embeddings=8192,
                             kv_channels=None)
    model = TinyTTS().eval()
    model.device = torch.device('cpu')
    model.base_lm = torch.nn.ModuleList([MiniCPMAttention(config, 0)])
    assert enable_active_kv_attention(model)['enabled']
    original_attention = model.base_lm[0]
    hidden = torch.randn(1, 64)
    cache = tuple(torch.randn(1, 2, 64, 16) for _ in range(2))
    with torch.inference_mode():
        expected = original_attention.forward_step(hidden, None, torch.tensor([7]),
                                                  tuple(value.clone() for value in cache))
    assert quantize_cpu_language_models(model)['enabled']
    assert model.base_lm[0].forward_step.__self__ is model.base_lm[0]
    assert model.base_lm[0] is not original_attention
    with torch.inference_mode():
        actual = model.base_lm[0].forward_step(hidden, None, torch.tensor([7]), cache)
    assert actual.shape == expected.shape and torch.isfinite(actual).all()
    # Quantization is lossy. This only guards obvious API/shape corruption.
    torch.testing.assert_close(actual, expected, atol=0.04, rtol=0.1)
