"""Explicit compact-mode dynamic INT8 for VoxCPM CPU language models.

INT8 changes model arithmetic and therefore remains an explicit choice. Only
language-model Linear weights change; original model files are never rewritten.
The first load converts in memory, so its transient allocation is larger than
the final model. Budget 20 GiB for each concurrent cold loader, not its measured
approximately 8 GiB steady state. No executable model pickle/cache is created.
"""
from __future__ import annotations

import warnings


def quantize_cpu_language_models(model):
    """Atomically replace both CPU FP32 language models, or leave both intact.

    Dynamic quantization only replaces standard Linear modules in base_lm and
    residual_lm. Embeddings, AudioVAE and diffusion modules retain their dtype.
    Returns observable status; unsupported runtimes keep the original model.
    """
    try:
        import torch
        from torch import nn
        from torch.ao.quantization import quantize_dynamic
    except ImportError:
        return {'enabled': False, 'reason': 'torch_unavailable', 'linear_layers': 0}
    tts = getattr(model, 'tts_model', model)
    if getattr(tts, '_voice_studio_int8_lm', False):
        return {'enabled': True, 'reason': 'already_quantized',
                'linear_layers': tts._voice_studio_int8_lm,
                'engine': torch.backends.quantized.engine, 'dtype': 'qint8'}
    names = ('base_lm', 'residual_lm')
    language_models = [getattr(tts, name, None) for name in names]
    if any(not isinstance(lm, nn.Module) for lm in language_models):
        return {'enabled': False, 'reason': 'unsupported_model', 'linear_layers': 0}
    parameters = [p for lm in language_models for p in lm.parameters()]
    if (not parameters or any(p.device.type != 'cpu' or p.dtype != torch.float32
                              for p in parameters)):
        return {'enabled': False, 'reason': 'cpu_fp32_only', 'linear_layers': 0}
    linear_count = sum(type(module) is nn.Linear
                       for lm in language_models for module in lm.modules())
    if not linear_count:
        return {'enabled': False, 'reason': 'no_linear_layers', 'linear_layers': 0}
    previous_engine = torch.backends.quantized.engine
    supported = torch.backends.quantized.supported_engines
    engine = previous_engine if previous_engine in {'x86', 'fbgemm'} and previous_engine in supported else (
        'fbgemm' if 'fbgemm' in supported else 'x86' if 'x86' in supported else None)
    if engine is None:
        return {'enabled': False, 'reason': 'x86_quantization_unavailable', 'linear_layers': 0}
    try:
        torch.backends.quantized.engine = engine
        # Both copies must succeed before either live language model changes.
        # inplace=False also preserves the original LM's training/eval state.
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning,
                                    message='.*torch.ao.quantization.*')
            replacements = [quantize_dynamic(lm, {nn.Linear}, dtype=torch.qint8,
                                             inplace=False)
                            for lm in language_models]
        converted = sum(isinstance(module, nn.quantized.dynamic.Linear)
                        for lm in replacements for module in lm.modules())
        if converted != linear_count:
            raise ValueError('not_all_linear_layers_converted')
    except (RuntimeError, TypeError, ValueError, AttributeError, NotImplementedError,
            MemoryError) as exc:
        torch.backends.quantized.engine = previous_engine
        return {'enabled': False, 'reason': 'quantization_failed',
                'error_type': type(exc).__name__, 'linear_layers': 0}
    for name, replacement in zip(names, replacements):
        setattr(tts, name, replacement)
    tts._voice_studio_int8_lm = converted
    return {'enabled': True, 'reason': None, 'linear_layers': converted,
            'engine': engine, 'dtype': 'qint8'}
