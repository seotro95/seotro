"""Exact CPU attention trimming and reusable reference encoding for VoxCPM 2.0.3.

No heavyweight imports happen until a loaded international model is supplied.
Weights and generation settings are unchanged. The attention replacement is
adapted from Apache-2.0 OpenBMB VoxCPM's MiniCPMAttention.forward_step, guarded
against that method's exact source before it is attached to model instances.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import importlib.metadata
import inspect
from pathlib import Path
import re
from types import MethodType


PACKAGE_VERSION = '2.0.3'
_FORWARD_STEP_SHA256 = '2b730666fa3260009f145bb3c057dc09a2666073052574e0121ddfac5de6fc17'


def enable_active_kv_attention(model):
    """Limit CPU decoding to populated KV entries; return observable status.

    Batch-one autoregressive queries can attend to the populated prefix without
    a mask. Future cache entries remain allocated and untouched for subsequent
    tokens, so prefill, cache reset, positional encoding and model weights retain
    the upstream behavior. Unsupported versions or overridden methods are left
    alone rather than guessed at.
    """
    try:
        if importlib.metadata.version('voxcpm') != PACKAGE_VERSION:
            return {'enabled': False, 'active_layers': 0, 'reason': 'unsupported_version'}
        import torch
        from voxcpm.modules.minicpm4.model import MiniCPMAttention, apply_rotary_pos_emb
        original = MiniCPMAttention.forward_step
        source = inspect.getsource(original).replace('\r\n', '\n').encode('utf-8')
        if hashlib.sha256(source).hexdigest() != _FORWARD_STEP_SHA256:
            return {'enabled': False, 'active_layers': 0, 'reason': 'unsupported_attention_source'}
    except (ImportError, OSError, TypeError, importlib.metadata.PackageNotFoundError):
        return {'enabled': False, 'active_layers': 0, 'reason': 'unavailable_attention_source'}

    tts = getattr(model, 'tts_model', model)
    if str(getattr(tts, 'device', 'cpu')).split(':', 1)[0] != 'cpu':
        return {'enabled': False, 'active_layers': 0, 'reason': 'cpu_only'}

    def forward_step(self, hidden_states, position_emb, position_id, kv_cache):
        # Runtime shape guards allow future callers to retain upstream behavior.
        if (not isinstance(position_id, torch.Tensor) or position_id.numel() != 1
                or position_id.dtype not in (torch.int32, torch.int64)
                or hidden_states.device.type != 'cpu' or hidden_states.dtype != torch.float32
                or len(kv_cache) != 2 or kv_cache[0].ndim != 4 or kv_cache[1].ndim != 4
                or kv_cache[0].shape != kv_cache[1].shape
                or kv_cache[0].device.type != 'cpu' or kv_cache[1].device.type != 'cpu'
                or kv_cache[0].dtype != torch.float32 or kv_cache[1].dtype != torch.float32):
            return original(self, hidden_states, position_emb, position_id, kv_cache)
        position = int(position_id.item())
        capacity = kv_cache[0].size(2)
        if not 0 <= position < capacity:
            raise IndexError('VoxCPM decode position lies outside its KV cache')
        bsz, _ = hidden_states.size()
        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)
        query_states = query_states.view(bsz, 1, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(bsz, 1, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(bsz, 1, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        if position_emb is not None:
            cos, sin = position_emb
            query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)
        key_cache, value_cache = kv_cache
        key_cache[:, :, position_id, :] = key_states
        value_cache[:, :, position_id, :] = value_states
        # The query is the newest token: all and only these keys are its past.
        # Keep the original allocated buffers for writes at the next position.
        populated = position + 1
        attention = torch.nn.functional.scaled_dot_product_attention(
            query_states.contiguous(), key_cache[:, :, :populated, :].contiguous(),
            value_cache[:, :, :populated, :].contiguous(), enable_gqa=True)
        attention = attention.transpose(1, 2).contiguous().reshape(bsz, self.num_heads*self.head_dim)
        return self.o_proj(attention)

    forward_step._voice_studio_active_kv = True
    active, patched = 0, 0
    for module in tts.modules():
        if type(module) is not MiniCPMAttention:
            continue
        method = getattr(module, 'forward_step')
        if getattr(method, '_voice_studio_active_kv', False):
            active += 1
        elif getattr(method, '__func__', None) is original:
            module.forward_step = MethodType(forward_step, module)
            active += 1
            patched += 1
    return {'enabled': active > 0, 'active_layers': active, 'patched_layers': patched,
            'reason': None if active else 'no_compatible_attention_layers'}


class CachedReferenceModel:
    """Drop-in VoxCPM.generate adapter with bounded reference-only feature cache.

    The pinned upstream public build_prompt_cache/generate_with_prompt_cache
    functions perform the same inference and bad-case handling. Other generation
    modes fall back to VoxCPM.generate. One isolated backend serializes calls;
    the mutable model's KV cache is never shared between concurrent threads.
    """
    def __init__(self, model, maximum=4):
        self._model = model
        self.tts_model = model.tts_model
        self.maximum = max(1, min(32, int(maximum)))
        self._references = OrderedDict()
        self.reference_cache_hits = 0
        self.reference_cache_misses = 0

    def _reference(self, filename):
        path = Path(filename).resolve()
        stat = path.stat()
        key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino)
        if key in self._references:
            cache = self._references.pop(key)
            self._references[key] = cache
            self.reference_cache_hits += 1
            return cache
        # Remove an older revision of this path before retaining a replacement.
        for previous in tuple(self._references):
            if previous[0] == key[0]:
                del self._references[previous]
        cache = self.tts_model.build_prompt_cache(reference_wav_path=str(path))
        self._references[key] = cache
        while len(self._references) > self.maximum:
            self._references.popitem(last=False)
        self.reference_cache_misses += 1
        return cache

    def generate(self, **options):
        reference = options.get('reference_wav_path')
        allowed = {'text', 'reference_wav_path', 'cfg_value', 'inference_timesteps', 'min_len',
                   'max_len', 'normalize', 'denoise', 'retry_badcase', 'retry_badcase_max_times',
                   'retry_badcase_ratio_threshold'}
        if (not reference or options.get('normalize') or options.get('denoise')
                or set(options)-allowed):
            return self._model.generate(**options)
        text = options.get('text')
        if not isinstance(text, str) or not text.strip():
            # Preserve the upstream validation rather than encoding an unused reference.
            return self._model.generate(**options)
        text = re.sub(r'\s+', ' ', text.replace('\n', ' '))
        settings = {key: options.get(key, default) for key, default in {
            'cfg_value': 2.0, 'inference_timesteps': 10, 'min_len': 2, 'max_len': 4096,
            'retry_badcase': True, 'retry_badcase_max_times': 3,
            'retry_badcase_ratio_threshold': 6.0}.items()}
        wave, _, _ = self.tts_model.generate_with_prompt_cache(
            target_text=text, prompt_cache=self._reference(reference), **settings)
        return wave.squeeze(0).cpu().numpy()
