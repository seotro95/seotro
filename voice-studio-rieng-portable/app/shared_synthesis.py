"""Share CPU ONNX weights while keeping each synthesis request's state private.

VieNeu 3.8.3's Nano and Turbo inference paths put their generated tensors and
autoregressive caches in call-local variables. CPU ONNX Runtime sessions support
concurrent Run calls. Each worker therefore owns a shallow model/engine copy and
its own engine lock, while immutable session weights are loaded once.

Only the pinned, audited CPU engines are accepted. Call clear_shared_models
after the thread executor has stopped and its synthesis closures are released.
"""
from __future__ import annotations

from collections import OrderedDict
import copy
import gc
import importlib.metadata
import threading
from types import MethodType


PACKAGE_VERSION = '3.8.3'
_ENGINES = {
    ('vieneu.v3nano', 'OnnxV3NanoEngine'): 'nano',
    ('vieneu._v3_turbo_engine.onnx_runtime_lite', 'OnnxV3LiteEngine'): 'turbo',
}
_lock = threading.RLock()
_entry = None
_local = threading.local()


class SharedInferenceUnsupported(ValueError):
    pass


class _SharedModel:
    def __init__(self, key, model):
        self.key = key
        self.model = model
        self.reference_lock = threading.RLock()
        self.watermark_lock = threading.RLock()
        engine = getattr(model, 'engine', None)
        self.kind = _ENGINES.get((type(engine).__module__, type(engine).__name__))
        if (self.kind is None or getattr(model, 'backend', None) != 'onnx'
                or getattr(getattr(engine, 'device', None), 'type', None) != 'cpu'
                or not hasattr(engine, '_lock')):
            raise SharedInferenceUnsupported('Bộ đọc không hỗ trợ dùng chung trọng số CPU.')

    def clone(self):
        model = copy.copy(self.model)
        model.engine = copy.copy(self.model.engine)
        model.engine._lock = threading.RLock()
        if hasattr(model.engine, '_oov_warned'):
            model.engine._oov_warned = set(model.engine._oov_warned)
        if hasattr(model, '_ref_phoneme_cache'):
            model._ref_phoneme_cache = dict(model._ref_phoneme_cache)
        if hasattr(model, '_stream_lock'):
            model._stream_lock = threading.Lock()
        if hasattr(model, '_ref_cache'):
            model._ref_cache = OrderedDict()
        if self.kind == 'turbo':
            # Enrollment mutates an LRU and lazily creates reference-only ONNX
            # sessions. Keep one synchronized copy rather than duplicating these
            # graphs and encoding the same reference in every worker.
            owner = self
            def enroll(_model, *args, **kwargs):
                with owner.reference_lock:
                    return owner.model._enroll_reference(*args, **kwargs)
            model._enroll_reference = MethodType(enroll, model)
        if getattr(model, 'watermarker', None) is not None:
            # Optional watermarkers are outside the audited ONNX engine. Keep
            # their state serialized without serializing speech generation.
            owner = self
            def apply_watermark(_model, *args, **kwargs):
                with owner.watermark_lock:
                    return owner.model._apply_watermark(*args, **kwargs)
            model._apply_watermark = MethodType(apply_watermark, model)
        return model


def acquire_model(key, factory):
    """Load one audited CPU model and return a stable private copy per thread.

    The key identifies the weights, precision and ONNX thread count. Voice,
    language and inference steps belong to each request, not to this key.
    A changed key replaces the registry entry; a caller must first stop the old
    executor to avoid simultaneously retaining old and new model allocations.
    """
    global _entry
    with _lock:
        if _entry is None or _entry.key != key:
            if importlib.metadata.version('vieneu') != PACKAGE_VERSION:
                raise SharedInferenceUnsupported('Dùng chung trọng số cần VieNeu '+PACKAGE_VERSION+'.')
            _entry = _SharedModel(key, factory())
        entry = _entry
        if getattr(_local, 'entry', None) is not entry:
            _local.model = entry.clone()
            _local.entry = entry
        return _local.model


def clear_shared_models():
    """Release the registry after all inference threads have joined."""
    global _entry, _local
    with _lock:
        previous, _entry = _entry, None
        _local = threading.local()
        if previous is not None:
            previous.model.close()
        # The per-clone bound enrollment/watermark adapters form cycles. Their
        # sessions should be released before another large engine is loaded,
        # rather than waiting for an unrelated automatic collection later.
        del previous
    gc.collect()
