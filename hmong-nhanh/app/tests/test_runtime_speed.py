import io
import shutil
from types import SimpleNamespace
from unittest.mock import Mock
import wave

import pytest

import cloning_engine as engine
import cpu_runtime
from render_cache import RenderCache


def reference(path, amplitude=257):
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        out.writeframes(amplitude.to_bytes(2, 'little') * 32000)
    return path


@pytest.fixture
def synthesizer(tmp_path, monkeypatch):
    model = SimpleNamespace(device='cpu')
    sample = reference(tmp_path / 'voice.wav')
    data = engine._wav([.2] * 8000, 8000)
    infer = Mock(return_value=data)
    monkeypatch.setattr(engine, '_render_cache', RenderCache())
    monkeypatch.setattr(engine, '_model_key', ('model-v1',))
    monkeypatch.setattr(engine, 'availability', lambda: {'ready': True})
    monkeypatch.setattr(engine, '_load_model', lambda settings: model)
    monkeypatch.setattr(engine, '_prepare_reference', lambda *args: {
        'text': args[2] + ' ', 'seconds': 4})
    monkeypatch.setattr(engine, '_infer_one', infer)
    return model, sample, infer


def test_identical_cue_and_job_snapshot_reuses_exact_wav(synthesizer, tmp_path):
    _, sample, infer = synthesizer
    snapshot = tmp_path / 'job-reference.wav'
    shutil.copyfile(sample, snapshot)
    first = engine.synthesize('Tae-yong cov ntaub ntawv tus kheej', 1, sample,
                              'Kuv hais lus Hmoob rau koj.', 'balanced')
    repeated = engine.synthesize('Tae-yong cov ntaub ntawv tus kheej', 1, snapshot,
                                 'Kuv hais lus Hmoob rau koj.', 'balanced')
    assert first == repeated
    assert infer.call_count == 1
    with wave.open(io.BytesIO(repeated)) as wav:
        assert wav.getnframes() == 8000


@pytest.mark.parametrize('change', ['voice', 'transcript', 'text', 'speed', 'quality', 'weights', 'engine'])
def test_changed_condition_never_reuses_old_voice(synthesizer, monkeypatch, change):
    _, sample, infer = synthesizer
    arguments = dict(text='Nyob zoo.', speed=1, reference_path=sample,
                     reference_text='Kuv hais lus Hmoob rau koj.', quality='balanced')
    engine.synthesize(**arguments)
    if change == 'voice':
        reference(sample, amplitude=514)
    elif change == 'transcript':
        arguments['reference_text'] = 'Some call me mother nature.'
    elif change == 'text':
        arguments['text'] = 'Koj nyob li cas?'
    elif change == 'speed':
        arguments['speed'] = 1.2
    elif change == 'quality':
        arguments['quality'] = 'quality'
    elif change == 'weights':
        monkeypatch.setattr(engine, '_model_key', ('model-v2',))
    else:
        replacement = SimpleNamespace(device='cpu')
        monkeypatch.setattr(engine, '_load_model', lambda settings: replacement)
    engine.synthesize(**arguments)
    assert infer.call_count == 2


def test_failed_synthesis_is_never_cached(synthesizer):
    _, sample, infer = synthesizer
    infer.side_effect = engine.CloningError('Temporary inference failure')
    for _ in range(2):
        with pytest.raises(engine.CloningError):
            engine.synthesize('Nyob zoo.', 1, sample, 'Kuv hais lus Hmoob rau koj.')
    assert infer.call_count == 2


def test_benchmark_bypasses_existing_result_without_overwriting_it(synthesizer):
    _, sample, infer = synthesizer
    args = ('Nyob zoo.', 1, sample, 'Kuv hais lus Hmoob rau koj.', 'balanced')
    original = engine.synthesize(*args)
    infer.return_value = engine._wav([.4] * 8000, 8000)
    measured = engine.synthesize(*args, use_cache=False)
    measured_again = engine.synthesize(*args, use_cache=False)
    assert measured == measured_again and measured != original
    assert engine.synthesize(*args) == original
    assert infer.call_count == 3


def test_benchmark_job_always_requests_uncached_inference(tmp_path, monkeypatch):
    import longform
    sample = reference(tmp_path / 'reference.wav')
    audio = engine._wav([.2] * 2400, 24000)
    infer = Mock(return_value=audio)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', infer)
    payload = {'text': 'Nyob zoo, hnub no koj nyob li cas?', 'voice': 'hmong-white-female',
               'quality': 'balanced', 'benchmark': True, 'timing': 'natural',
               '_reference': {'path': str(sample), 'text': 'Kuv hais lus Hmoob rau koj.'}}
    for number in range(2):
        folder = tmp_path / str(number)
        longform.atomic_json(folder / 'input.json', payload)
        result = longform.process_job(folder)
        assert result['completed'] == result['total'] == 1
    assert infer.call_count == 2
    assert all(call.kwargs.get('use_cache') is False for call in infer.call_args_list)


def test_cache_is_bounded_and_evicts_least_recently_used():
    cache = RenderCache(max_bytes=10, max_entries=2)
    cache.put('a', b'1111')
    cache.put('b', b'2222')
    assert cache.get('a') == b'1111'
    cache.put('c', b'3333')
    assert cache.get('b') is None
    assert cache.get('a') == b'1111'
    cache.put('too-large', b'0' * 11)
    assert cache.get('too-large') is None
    assert cache.bytes == 8
    cache.set_owner(object())
    assert cache.get('a') is None and cache.bytes == 0


def test_cache_replacement_counts_bytes_and_applies_byte_limit():
    cache = RenderCache(max_bytes=10, max_entries=128)
    owner = object()
    cache.set_owner(owner)
    cache.put('a', b'1111')
    cache.put('b', b'22')
    cache.put('a', b'3333333')
    assert cache.bytes == 9
    cache.set_owner(owner)
    assert cache.get('b') == b'22'
    cache.put('c', b'4444')
    assert cache.get('a') is None
    assert cache.get('b') == b'22' and cache.get('c') == b'4444'
    assert cache.bytes == 6


@pytest.mark.parametrize(('quota', 'expected'), [('200000 100000', 2), ('50000 100000', 1),
                                                   ('max 100000', None), ('bad', None),
                                                   ('-1 100000', None), ('100000 0', None),
                                                   ('2.5 1', None)])
def test_cgroup_v2_quotas(tmp_path, quota, expected):
    (tmp_path / 'cpu.max').write_text(quota)
    assert cpu_runtime._quota_limit(tmp_path) == expected


def test_cgroup_v1_quota(tmp_path):
    (tmp_path / 'cpu').mkdir()
    (tmp_path / 'cpu/cpu.cfs_quota_us').write_text('200000')
    (tmp_path / 'cpu/cpu.cfs_period_us').write_text('100000')
    assert cpu_runtime._quota_limit(tmp_path) == 2


@pytest.mark.parametrize(('requested', 'expected'), [('4', 2), ('1', 1), ('bad', 2), ('0', 1)])
def test_threads_respect_quota_and_user_lower_limit(monkeypatch, requested, expected):
    monkeypatch.setattr(cpu_runtime.os, 'cpu_count', lambda: 32)
    monkeypatch.setattr(cpu_runtime.os, 'sched_getaffinity', lambda pid: set(range(8)), raising=False)
    monkeypatch.setattr(cpu_runtime, '_quota_limit', lambda: 2)
    monkeypatch.setenv('HMONG_CPU_THREADS', requested)
    assert cpu_runtime.cpu_thread_count() == expected


def test_thread_fallback_without_linux_features(monkeypatch):
    monkeypatch.setattr(cpu_runtime.os, 'cpu_count', lambda: 6)
    monkeypatch.delattr(cpu_runtime.os, 'sched_getaffinity', raising=False)
    monkeypatch.setattr(cpu_runtime, '_quota_limit', lambda: None)
    monkeypatch.delenv('HMONG_CPU_THREADS', raising=False)
    assert cpu_runtime.cpu_thread_count() == 4


def test_thread_affinity_and_unknown_cpu_count_are_respected(monkeypatch):
    monkeypatch.setattr(cpu_runtime.os, 'cpu_count', lambda: 64)
    monkeypatch.setattr(cpu_runtime.os, 'sched_getaffinity', lambda pid: {7}, raising=False)
    monkeypatch.setattr(cpu_runtime, '_quota_limit', lambda: None)
    monkeypatch.setenv('HMONG_CPU_THREADS', '64')
    assert cpu_runtime.cpu_thread_count() == 1
    monkeypatch.setattr(cpu_runtime.os, 'cpu_count', lambda: None)
    monkeypatch.delattr(cpu_runtime.os, 'sched_getaffinity', raising=False)
    assert cpu_runtime.cpu_thread_count() == 1
