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


def test_cpu_text_offload_keeps_embedding_hidden_states_cache_ties_and_state_exact(encoder):
    backend = backend_for(encoder)
    ids = [torch.tensor([[1, 8, 12, 5, 3]]), torch.tensor([[7]]), torch.tensor([[9]])]
    weights = {name: (value, value.detach().clone()) for name, value in encoder.named_parameters()}
    original_state = {name: value.clone() for name, value in encoder.state_dict().items()}
    table = encoder.model.model.embed_tokens
    original_parameter = table.weight
    expected = []
    with torch.inference_mode():
        cache = None
        for tokens in ids:
            embedded = table(tokens)
            mask = torch.tril(torch.ones(1, tokens.shape[1], tokens.shape[1], dtype=torch.bool))
            hidden, cache = encoder.forward_one_step(embedded, mask, cache)
            expected.append((embedded.clone(), hidden.clone(), cache_tensors(cache)))

    assert acceleration.optimize_qwen_decode(backend)
    assert acceleration.offload_qwen_text_embedding(backend, force=True)
    assert table.weight is original_parameter is encoder.model.lm_head.weight
    assert table.weight.device.type == 'cpu'
    assert backend._hmong_text_embedding_offloaded is True
    assert backend._hmong_text_embedding_bytes == 0  # CPU parity cannot claim VRAM saved.

    def head_must_remain_unused(*args):
        raise AssertionError('Offloaded unused language head must never execute')

    hook = encoder.model.lm_head.register_forward_hook(head_must_remain_unused)
    try:
        with torch.inference_mode():
            cache = None
            for tokens, (expected_embedding, expected_hidden, expected_cache) in zip(ids, expected):
                embedded = table(tokens)
                assert embedded.device == tokens.device
                torch.testing.assert_close(embedded, expected_embedding, rtol=0, atol=0)
                mask = torch.tril(torch.ones(1, tokens.shape[1], tokens.shape[1], dtype=torch.bool))
                hidden, cache = encoder.forward_one_step(embedded, mask, cache)
                torch.testing.assert_close(hidden, expected_hidden, rtol=0, atol=0)
                for (key, value), (expected_key, expected_value) in zip(cache_tensors(cache), expected_cache):
                    torch.testing.assert_close(key, expected_key, rtol=0, atol=0)
                    torch.testing.assert_close(value, expected_value, rtol=0, atol=0)
    finally:
        hook.remove()

    assert set(encoder.state_dict()) == set(original_state)
    for name, value in encoder.state_dict().items():
        torch.testing.assert_close(value, original_state[name], rtol=0, atol=0)
    for name, parameter in encoder.named_parameters():
        original, value = weights[name]
        assert parameter is original
        torch.testing.assert_close(parameter, value, rtol=0, atol=0)


def test_text_offload_requires_optimized_encoder_and_skips_cpu_by_default(encoder):
    backend = backend_for(encoder)
    backend.device = 'cpu'
    table = encoder.model.model.embed_tokens
    original = table.forward.__func__
    assert acceleration.offload_qwen_text_embedding(backend, force=True) is False
    assert acceleration.optimize_qwen_decode(backend)
    assert acceleration.offload_qwen_text_embedding(backend) is False
    assert table.forward.__func__ is original


@pytest.mark.parametrize('backend', [None, SimpleNamespace(),
                                    backend_for(SimpleNamespace(model=object(), forward_one_step=lambda: None))])
def test_text_offload_does_not_touch_unknown_backends(backend):
    assert acceleration.offload_qwen_text_embedding(backend, force=True) is False


def test_text_offload_is_idempotent_and_keeps_parameter_identity(encoder):
    backend = backend_for(encoder)
    assert acceleration.optimize_qwen_decode(backend)
    parameter = encoder.model.model.embed_tokens.weight
    assert acceleration.offload_qwen_text_embedding(backend, force=True)
    lookup = encoder.model.model.embed_tokens.forward
    assert acceleration.offload_qwen_text_embedding(backend, force=True)
    assert encoder.model.model.embed_tokens.forward is lookup
    assert encoder.model.model.embed_tokens.weight is parameter is encoder.model.lm_head.weight


@pytest.mark.parametrize('variant', ['untied_head', 'mutating_lookup', 'embedding_subclass', 'output_hook'])
def test_text_offload_leaves_custom_or_untied_embeddings_unchanged(encoder, variant):
    backend = backend_for(encoder)
    assert acceleration.optimize_qwen_decode(backend)
    table = encoder.model.model.embed_tokens
    if variant == 'untied_head':
        encoder.model.lm_head.weight = torch.nn.Parameter(table.weight.detach().clone())
    elif variant == 'mutating_lookup':
        table.max_norm = 1.0
    elif variant == 'embedding_subclass':
        class ChangedEmbedding(torch.nn.Embedding):
            def forward(self, indices):
                return super().forward(indices) * 2
        encoder.model.model.embed_tokens = ChangedEmbedding(table.num_embeddings, table.embedding_dim).eval()
        table = encoder.model.model.embed_tokens
        encoder.model.lm_head.weight = table.weight
    else:
        table.register_forward_hook(lambda module, inputs, output: output * 2)
    original_forward = table.forward.__func__
    original_parameter = table.weight
    original_value = table.weight.detach().clone()
    assert acceleration.offload_qwen_text_embedding(backend, force=True) is False
    assert table.forward.__func__ is original_forward
    assert table.weight is original_parameter
    torch.testing.assert_close(table.weight, original_value, rtol=0, atol=0)


@pytest.mark.parametrize('memory_gib,expected', [(6, True), (8, True), (12, False)])
def test_text_offload_default_policy_selects_only_low_vram_cuda(encoder, monkeypatch, memory_gib, expected):
    backend = backend_for(encoder)
    backend.device = 'cuda:0'
    assert acceleration.optimize_qwen_decode(backend)
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
    monkeypatch.setattr(torch.cuda, 'get_device_properties',
                        lambda device: SimpleNamespace(total_memory=memory_gib * 1024 ** 3))
    # CUDA metadata is simulated; model operations remain real CPU tiny Qwen.
    assert acceleration.offload_qwen_text_embedding(backend) is expected


def test_text_offload_copy_failure_leaves_parameter_and_forward_unchanged(encoder, monkeypatch):
    backend = backend_for(encoder)
    assert acceleration.optimize_qwen_decode(backend)
    table = encoder.model.model.embed_tokens
    original_forward = table.forward.__func__
    parameter = table.weight
    original_value = parameter.detach().clone()
    original_to = torch.Tensor.to

    def failed_copy(tensor, *args, **kwargs):
        if kwargs.get('device') == 'cpu':
            raise RuntimeError('CPU allocation unavailable')
        return original_to(tensor, *args, **kwargs)

    monkeypatch.setattr(torch.Tensor, 'to', failed_copy)
    assert acceleration.offload_qwen_text_embedding(backend, force=True) is False
    assert table.forward.__func__ is original_forward
    assert table.weight is parameter is encoder.model.lm_head.weight
    torch.testing.assert_close(parameter, original_value, rtol=0, atol=0)


def test_text_offload_restores_storage_when_forward_binding_fails(encoder, monkeypatch):
    backend = backend_for(encoder)
    assert acceleration.optimize_qwen_decode(backend)
    table = encoder.model.model.embed_tokens
    parameter = table.weight
    original_value = parameter.detach().clone()
    original_forward = table.forward.__func__
    original_to = torch.Tensor.to
    original_setattr = torch.nn.Embedding.__setattr__

    def copied_storage(tensor, *args, **kwargs):
        result = original_to(tensor, *args, **kwargs)
        return result.clone() + 1 if kwargs.get('device') == 'cpu' else result

    def fail_after_storage_change(module, name, value):
        if (module is table and name == 'forward'
                and getattr(value, '__func__', None) is acceleration._cpu_text_embedding_on_input_device):
            assert not torch.equal(parameter, original_value)
            raise RuntimeError('Could not bind lookup')
        return original_setattr(module, name, value)

    monkeypatch.setattr(torch.Tensor, 'to', copied_storage)
    monkeypatch.setattr(torch.nn.Embedding, '__setattr__', fail_after_storage_change)
    assert acceleration.offload_qwen_text_embedding(backend, force=True) is False
    assert table.weight is parameter is encoder.model.lm_head.weight
    assert table.forward.__func__ is original_forward and 'forward' not in table.__dict__
    torch.testing.assert_close(parameter, original_value, rtol=0, atol=0)


@pytest.mark.skipif(not torch.cuda.is_available(), reason='Native CUDA device is not available')
def test_native_cuda_offload_returns_embeddings_to_gpu_and_preserves_parameters(encoder):
    encoder.to('cuda')
    backend = backend_for(encoder)
    backend.device = 'cuda'
    assert acceleration.optimize_qwen_decode(backend)
    table = encoder.model.model.embed_tokens
    ids = torch.tensor([[1, 8, 12, 3]], device='cuda')
    parameter = table.weight
    with torch.inference_mode():
        expected = table(ids).clone()
    assert acceleration.offload_qwen_text_embedding(backend, force=True)
    assert table.weight is parameter is encoder.model.lm_head.weight
    assert parameter.device.type == 'cpu'
    assert backend._hmong_text_embedding_bytes == parameter.numel() * parameter.element_size()
    assert encoder.model.model.layers[0].self_attn.q_proj.weight.device.type == 'cuda'
    with torch.inference_mode():
        actual = table(ids)
    assert actual.device == ids.device
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
