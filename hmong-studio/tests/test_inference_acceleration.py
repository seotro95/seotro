"""Real tiny Qwen2 parity checks without model downloads or speech inference."""
from types import SimpleNamespace

import pytest

import inference_acceleration as acceleration

torch = pytest.importorskip('torch')
transformers = pytest.importorskip('transformers')
from transformers import Qwen2Config, Qwen2ForCausalLM


class LegacyEncoder(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    # Keep the pinned legacy implementation verbatim: the helper deliberately
    # refuses unknown wrappers even if they contain a genuine Qwen2 model.
    def forward_one_step(self, xs, masks, cache=None):
        input_masks = masks[:, -1, :]
        outs = self.model(
            inputs_embeds=xs,
            attention_mask=input_masks,
            output_hidden_states=True,
            return_dict=True,
            use_cache=True,
            past_key_values=cache,
        )
        xs = outs.hidden_states[-1]
        new_cache = outs.past_key_values
        return xs, new_cache


@pytest.fixture
def encoder():
    torch.manual_seed(1986)
    config = Qwen2Config(vocab_size=97, hidden_size=32, intermediate_size=64,
                         num_hidden_layers=2, num_attention_heads=4,
                         num_key_value_heads=2, max_position_embeddings=64,
                         attention_dropout=0.0, tie_word_embeddings=True,
                         use_cache=True)
    return LegacyEncoder(Qwen2ForCausalLM(config).eval()).eval()


def backend_for(encoder):
    return SimpleNamespace(llm=SimpleNamespace(llm=encoder))


def cache_tensors(cache):
    """Snapshot cache contents: the HF dynamic cache mutates on later steps."""
    return tuple((key.clone(), value.clone()) for key, value in cache.to_legacy_cache())


def test_prefill_and_cached_decode_keep_hidden_states_and_kv_exact(encoder):
    original_step = encoder.forward_one_step
    weights = {name: (value, value.detach().clone()) for name, value in encoder.named_parameters()}
    torch.manual_seed(19)
    inputs = [torch.randn(1, length, 32) for length in (5, 1, 1)]
    masks = [torch.tril(torch.ones((1, value.shape[1], value.shape[1]), dtype=torch.bool))
             for value in inputs]
    expected = []
    with torch.inference_mode():
        cache = None
        for value, mask in zip(inputs, masks):
            hidden, cache = original_step(value, mask, cache)
            expected.append((hidden.clone(), cache_tensors(cache)))

    assert acceleration.optimize_qwen_decode(backend_for(encoder)) is True

    def unused_head(*args):
        raise AssertionError('The discarded language-vocabulary lm_head must not run')
    hook = encoder.model.lm_head.register_forward_hook(unused_head)
    try:
        with torch.inference_mode():
            cache = None
            for (value, mask), (expected_hidden, expected_cache) in zip(zip(inputs, masks), expected):
                hidden, cache = encoder.forward_one_step(value, mask, cache)
                torch.testing.assert_close(hidden, expected_hidden, rtol=0, atol=0)
                actual_cache = cache_tensors(cache)
                assert len(actual_cache) == len(expected_cache) == 2
                for (key, val), (expected_key, expected_val) in zip(actual_cache, expected_cache):
                    torch.testing.assert_close(key, expected_key, rtol=0, atol=0)
                    torch.testing.assert_close(val, expected_val, rtol=0, atol=0)
    finally:
        hook.remove()
    for name, parameter in encoder.named_parameters():
        original_parameter, original_value = weights[name]
        assert parameter is original_parameter
        torch.testing.assert_close(parameter, original_value, rtol=0, atol=0)


def test_optimization_is_idempotent(encoder):
    backend = backend_for(encoder)
    assert acceleration.optimize_qwen_decode(backend) is True
    first = encoder.forward_one_step
    assert acceleration.optimize_qwen_decode(backend) is True
    assert encoder.forward_one_step is first


@pytest.mark.parametrize('backend', [None, object(), SimpleNamespace(),
                                    backend_for(SimpleNamespace(model=object(), forward_one_step=lambda: None))])
def test_unknown_backend_is_not_modified(backend):
    assert acceleration.optimize_qwen_decode(backend) is False


def test_real_qwen_in_unknown_encoder_is_not_modified(encoder):
    class ChangedEncoder(LegacyEncoder):
        def forward_one_step(self, xs, masks, cache=None):
            return xs * 2, cache

    unknown = ChangedEncoder(encoder.model)
    original = unknown.forward_one_step.__func__
    assert acceleration.optimize_qwen_decode(backend_for(unknown)) is False
    assert unknown.forward_one_step.__func__ is original


def test_model_subclasses_are_not_modified(encoder):
    class ChangedQwen(Qwen2ForCausalLM):
        pass

    encoder.model = ChangedQwen(encoder.model.config).eval()
    original = encoder.forward_one_step.__func__
    assert acceleration.optimize_qwen_decode(backend_for(encoder)) is False
    assert encoder.forward_one_step.__func__ is original
