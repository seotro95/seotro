"""Concurrent state isolation and bounded model loading, without downloaded AI."""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import gc
import weakref
from types import SimpleNamespace

import pytest

import shared_synthesis as shared


class Session:
    def __init__(self, workers=1):
        self.barrier = threading.Barrier(workers)

    def run(self, value):
        self.barrier.wait(timeout=3)
        return value * 3


class OnnxV3NanoEngine:
    def __init__(self, session):
        self.device = SimpleNamespace(type='cpu')
        self._lock = threading.RLock()
        self._oov_warned = set()
        self.s_ve = session

    def infer(self, value):
        with self._lock:
            return self.s_ve.run(value)


OnnxV3NanoEngine.__module__ = 'vieneu.v3nano'


class OnnxV3LiteEngine(OnnxV3NanoEngine):
    pass


OnnxV3LiteEngine.__module__ = 'vieneu._v3_turbo_engine.onnx_runtime_lite'


class Model:
    def __init__(self, session, engine_type=OnnxV3NanoEngine):
        self.engine = engine_type(session)
        self.backend = 'onnx'
        self._ref_phoneme_cache = {}
        self._ref_cache = OrderedDict()
        self._stream_lock = threading.Lock()
        self.watermarker = None
        self.closed = False
        self.enrollments = 0
        self._preset_voices = {'first': object(), 'second': object()}

    def _enroll_reference(self, name, **kwargs):
        if name not in self._ref_cache:
            time.sleep(.005)
            self.enrollments += 1
            self._ref_cache[name] = object()
        return self._ref_cache[name]

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    shared.clear_shared_models()
    monkeypatch.setattr(shared.importlib.metadata, 'version', lambda package: '3.8.3')
    yield
    shared.clear_shared_models()


def test_parallel_clones_share_only_sessions_and_presets_with_private_decode_locks():
    calls = []
    base = Model(Session(4))
    barrier = threading.Barrier(4)
    def factory():
        calls.append(1)
        return base
    def task(index):
        model = shared.acquire_model(('nano', 1), factory)
        barrier.wait(timeout=3)
        model.engine._oov_warned.add(index)
        model._ref_phoneme_cache[index] = index
        result = model.engine.infer(index)
        return model, result
    with ThreadPoolExecutor(4) as pool:
        outputs = list(pool.map(task, range(4)))
    assert len(calls) == 1
    models = [model for model, _ in outputs]
    assert len({id(model) for model in models}) == 4
    assert len({id(model.engine._lock) for model in models}) == 4
    assert [result for _, result in outputs] == [0, 3, 6, 9]
    assert all(model.engine.s_ve is base.engine.s_ve for model in models)
    assert all(model._preset_voices is base._preset_voices for model in models)
    assert [model.engine._oov_warned for model in models] == [{0}, {1}, {2}, {3}]
    assert base.engine._oov_warned == set() and base._ref_phoneme_cache == {}


def test_same_thread_reuses_clone_but_new_precision_or_thread_budget_reloads():
    bases = []
    def factory():
        bases.append(Model(Session()))
        return bases[-1]
    first = shared.acquire_model(('turbo', 'fp32', 1), factory)
    assert shared.acquire_model(('turbo', 'fp32', 1), factory) is first
    second = shared.acquire_model(('turbo', 'int8', 1), factory)
    third = shared.acquire_model(('turbo', 'int8', 2), factory)
    assert first is not second and second is not third and len(bases) == 3


def test_turbo_reference_cache_is_shared_and_enrolled_once():
    base = Model(Session(), OnnxV3LiteEngine)
    barrier = threading.Barrier(4)
    def task(index):
        model = shared.acquire_model(('turbo', 'fp32', 1), lambda: base)
        barrier.wait(timeout=3)
        return model._enroll_reference('same reference', denoise=False)
    with ThreadPoolExecutor(4) as pool:
        outputs = list(pool.map(task, range(4)))
    assert all(value is outputs[0] for value in outputs)
    assert base.enrollments == 1


def test_clear_releases_base_after_threads_have_joined_and_reloads_next_job():
    base = Model(Session())
    with ThreadPoolExecutor(1) as pool:
        assert pool.submit(shared.acquire_model, ('nano', 1), lambda: base).result() is not base
    shared.clear_shared_models()
    assert base.closed
    new = Model(Session())
    assert shared.acquire_model(('nano', 1), lambda: new).engine.s_ve is new.engine.s_ve
    assert not new.closed


@pytest.mark.parametrize('version', ['3.8.2', '3.9.0'])
def test_unknown_sdk_version_fails_before_allocating_models(monkeypatch, version):
    monkeypatch.setattr(shared.importlib.metadata, 'version', lambda package: version)
    called = []
    with pytest.raises(shared.SharedInferenceUnsupported, match='3.8.3'):
        shared.acquire_model('nano', lambda: called.append(1))
    assert called == []


def test_gpu_or_unknown_engine_is_never_shared():
    gpu = Model(Session())
    gpu.engine.device.type = 'cuda'
    with pytest.raises(shared.SharedInferenceUnsupported):
        shared.acquire_model('gpu', lambda: gpu)
    unsupported = Model(Session())
    unsupported.engine = SimpleNamespace(device=SimpleNamespace(type='cpu'), _lock=threading.RLock())
    with pytest.raises(shared.SharedInferenceUnsupported):
        shared.acquire_model('other', lambda: unsupported)


def test_optional_watermark_state_is_serialized_separately_from_decode():
    base = Model(Session(4))
    base.watermarker = object()
    active = [0, 0]
    def watermark(value):
        active[0] += 1
        active[1] = max(active)
        time.sleep(.005)
        active[0] -= 1
        return value + 7
    base._apply_watermark = watermark
    def task(index):
        model = shared.acquire_model(('nano', 1), lambda: base)
        value = model.engine.infer(index)
        return model._apply_watermark(value)
    with ThreadPoolExecutor(4) as pool:
        assert list(pool.map(task, range(4))) == [7, 10, 13, 16]
    assert active == [0, 1]


def test_clear_collects_bound_adapter_cycles_before_loading_another_engine():
    base = Model(Session(), OnnxV3LiteEngine)
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        def task():
            model = shared.acquire_model(('turbo', 'fp32', 1), lambda: base)
            return weakref.ref(model)
        with ThreadPoolExecutor(1) as pool:
            reference = pool.submit(task).result()
        # A bound per-clone enrollment method holds its own model in a cycle.
        assert reference() is not None
        shared.clear_shared_models()
        assert reference() is None
        assert base.closed
    finally:
        if was_enabled:gc.enable()
