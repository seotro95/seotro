"""VoxCPM acceleration parity uses tiny tensors, not downloaded model weights."""
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

torch = pytest.importorskip('torch')
pytest.importorskip('voxcpm')

import voxcpm_acceleration as acceleration
from voxcpm.modules.minicpm4.model import MiniCPMAttention


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.device = torch.device('cpu')
        config = SimpleNamespace(hidden_size=64, num_attention_heads=4,
                                 num_key_value_heads=2, max_position_embeddings=8192,
                                 kv_channels=None)
        self.attention = MiniCPMAttention(config, 0)


@pytest.mark.parametrize('position', [0, 1, 7, 31, 63])
@pytest.mark.parametrize('rotary', [False, True])
def test_active_prefix_matches_upstream_full_future_mask(position, rotary):
    torch.manual_seed(73)
    model = TinyModel().eval()
    baseline = copy.deepcopy(model)
    report = acceleration.enable_active_kv_attention(model)
    assert report['enabled'] and report['active_layers'] == 1
    hidden = torch.randn(1, 64)
    # Future cache contents deliberately contain unrelated nonzero values.
    caches = tuple(torch.randn(1, 2, 64, 16) for _ in range(2))
    reference_caches = tuple(cache.clone() for cache in caches)
    position_id = torch.tensor([position])
    emb = (torch.randn(1, 16), torch.randn(1, 16)) if rotary else None
    with torch.inference_mode():
        expected = baseline.attention.forward_step(hidden, emb, position_id, reference_caches)
        actual = model.attention.forward_step(hidden, emb, position_id, caches)
    torch.testing.assert_close(actual, expected, atol=2e-6, rtol=2e-5)
    for actual_cache, expected_cache in zip(caches, reference_caches):
        torch.testing.assert_close(actual_cache, expected_cache, atol=0, rtol=0)


def test_sequential_decode_and_cache_reset_preserve_outputs():
    torch.manual_seed(11)
    model = TinyModel().eval()
    baseline = copy.deepcopy(model)
    acceleration.enable_active_kv_attention(model)
    for initial in (torch.randn(1, 2, 64, 16), torch.zeros(1, 2, 64, 16)):
        caches = (initial.clone(), initial.clone())
        reference_caches = tuple(cache.clone() for cache in caches)
        for position in (3, 4, 5):
            hidden = torch.randn(1, 64)
            with torch.inference_mode():
                expected = baseline.attention.forward_step(hidden, None, torch.tensor([position]), reference_caches)
                actual = model.attention.forward_step(hidden, None, torch.tensor([position]), caches)
            torch.testing.assert_close(actual, expected, atol=2e-6, rtol=2e-5)


@pytest.mark.parametrize('position', [-1, 64])
def test_invalid_positions_do_not_modify_cache(position):
    model = TinyModel().eval()
    acceleration.enable_active_kv_attention(model)
    caches = tuple(torch.zeros(1, 2, 64, 16) for _ in range(2))
    with pytest.raises(IndexError):
        model.attention.forward_step(torch.zeros(1, 64), None, torch.tensor([position]), caches)
    assert all(torch.count_nonzero(cache) == 0 for cache in caches)


def test_weights_unchanged_and_instance_patch_is_idempotent():
    model = TinyModel().eval()
    weights = {name: tensor.clone() for name, tensor in model.state_dict().items()}
    original_class_method = MiniCPMAttention.forward_step
    first = acceleration.enable_active_kv_attention(model)
    second = acceleration.enable_active_kv_attention(model)
    assert first['patched_layers'] == 1 and second['patched_layers'] == 0
    assert second['active_layers'] == 1 and MiniCPMAttention.forward_step is original_class_method
    for name, tensor in model.state_dict().items():
        torch.testing.assert_close(tensor, weights[name], atol=0, rtol=0)


def test_unknown_version_source_or_device_is_untouched(monkeypatch):
    model = TinyModel()
    original = model.attention.forward_step
    with monkeypatch.context() as patch:
        patch.setattr(acceleration.importlib.metadata, 'version', lambda name: '2.1.0')
        assert acceleration.enable_active_kv_attention(model)['reason'] == 'unsupported_version'
    with monkeypatch.context() as patch:
        patch.setattr(acceleration.inspect, 'getsource', lambda method: 'changed upstream implementation')
        assert acceleration.enable_active_kv_attention(model)['reason'] == 'unsupported_attention_source'
    model.device = torch.device('cuda')
    assert acceleration.enable_active_kv_attention(model)['reason'] == 'cpu_only'
    assert model.attention.forward_step == original


class FakeWave:
    def squeeze(self, dimension):
        assert dimension == 0
        return self
    def cpu(self):
        return self
    def numpy(self):
        return 'exact upstream output array'


class FakeReferenceModel:
    def __init__(self):
        self.tts_model = self
        self.built = []
        self.generated = []
        self.fallback = []
    def build_prompt_cache(self, **options):
        cache = {'reference': options['reference_wav_path'], 'index': len(self.built)}
        self.built.append(cache)
        return cache
    def generate_with_prompt_cache(self, **options):
        self.generated.append(options)
        return FakeWave(), None, None
    def generate(self, **options):
        self.fallback.append(options)
        return 'upstream fallback'


def test_reference_encoding_is_reused_without_changing_text_or_generation_settings(tmp_path):
    reference = tmp_path/'reference.wav'; reference.write_bytes(b'synthetic reference')
    model = FakeReferenceModel()
    cached = acceleration.CachedReferenceModel(model)
    settings = {'text': 'Hello,\n world.', 'reference_wav_path': str(reference), 'inference_timesteps': 4,
                'cfg_value': 1.7, 'normalize': False, 'denoise': False, 'retry_badcase': True}
    assert cached.generate(**settings) == 'exact upstream output array'
    cached.generate(**dict(settings, text='Another sentence.'))
    assert len(model.built) == 1 and cached.reference_cache_hits == 1
    first, second = model.generated
    assert first['target_text'] == 'Hello, world.' and second['target_text'] == 'Another sentence.'
    assert first['prompt_cache'] is second['prompt_cache']
    assert first['inference_timesteps'] == 4 and first['cfg_value'] == 1.7
    assert first['retry_badcase'] is True and first['retry_badcase_max_times'] == 3
    assert first['max_len'] == 4096


def test_changed_reference_and_lru_limit_do_not_reuse_wrong_voice(tmp_path):
    refs = [tmp_path/(str(index)+'.wav') for index in range(3)]
    for index, path in enumerate(refs): path.write_bytes(b'synthetic'+bytes([index]))
    model = FakeReferenceModel(); cached = acceleration.CachedReferenceModel(model, maximum=2)
    for path in refs: cached.generate(text='Test.', reference_wav_path=str(path))
    assert len(cached._references) == 2
    cached.generate(text='Test.', reference_wav_path=str(refs[0]))
    assert len(model.built) == 4
    refs[0].write_bytes(b'a changed synthetic reference with different length')
    cached.generate(text='Test.', reference_wav_path=str(refs[0]))
    assert len(model.built) == 5 and len(cached._references) == 2
    assert model.generated[-1]['prompt_cache']['index'] == 4


@pytest.mark.parametrize('options', [
    {'text': 'No reference.'}, {'text': 'Normalize.', 'normalize': True},
    {'text': 'Denoise.', 'denoise': True}, {'text': 'Prompt.', 'prompt_text': 'A prompt.'},
    {'text': ''}])
def test_other_modes_keep_upstream_validation_and_behavior(tmp_path, options):
    path = tmp_path/'reference.wav'; path.write_bytes(b'synthetic reference')
    model = FakeReferenceModel(); cached = acceleration.CachedReferenceModel(model)
    if options.get('text') != 'No reference.': options = {'reference_wav_path': str(path), **options}
    assert cached.generate(**options) == 'upstream fallback'
    assert model.fallback == [options] and not model.built
