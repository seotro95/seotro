"""Scheduling and cache correctness, using fixture PCM rather than AI benchmarks."""
import importlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import soundfile as sf

from nano_resources import NANO_WORKER_BYTES, RESERVED_BYTES, nano_resources, resource_policy, resolve_nano_settings


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    module.close_nano_pool()
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, '_cached_synth', None)
    monkeypatch.setattr(module, '_cached_key', None)
    (tmp_path / 'audio').mkdir()
    (tmp_path / 'voices').mkdir()
    yield module
    module.close_nano_pool()


def job(**changes):
    return {'id': 'fixture', 'text': 'Câu đầu. Câu sau.', 'engine': 'vieneu_nano',
            'speaker': 'Fixture', 'nano_parallel': 3, 'nano_threads': 1, 'nano_steps': 4,
            'format': 'wav', 'speed': 1, 'paragraph_pause': 0, **changes}


def install_thread_pool(worker, monkeypatch, synthesize):
    # Real spawned-process initialization is checked separately. Fixture worker
    # threads make completion ordering/cancellation deterministic and lightweight.
    monkeypatch.setattr(worker, 'get_synthesizer', lambda _: synthesize)
    created = []
    def create(settings, workers):
        pool = ThreadPoolExecutor(max_workers=workers)
        created.append((dict(settings), workers, pool))
        return pool
    monkeypatch.setattr(worker, 'create_nano_pool', create)
    monkeypatch.setattr(worker, 'resolve_nano_settings', lambda value: dict(value))
    return created


def pcm(path, value=.2, seconds=.1):
    sf.write(path, np.full(round(seconds * 24000), value, dtype=np.float32), 24000, subtype='PCM_16')


def test_resource_policy_caps_cpu_and_memory_without_thread_oversubscription():
    memory = RESERVED_BYTES + 4 * NANO_WORKER_BYTES
    policy = resource_policy(cpus=4, memory=memory)
    assert policy['recommended_workers'] == policy['max_workers'] == 4
    assert policy['recommended_threads'] == 1
    assert nano_resources(0, 0, cpus=4, memory=memory)['workers'] == 4
    settings = nano_resources(8, 3, cpus=4, memory=memory)
    assert settings['workers'] == 1 and settings['threads'] == 3
    assert nano_resources(8, 8, cpus=1, memory=0)['workers'] == 1
    assert nano_resources(8, 8, cpus=1, memory=0)['threads'] == 1
    assert nano_resources(8, 1, cpus=32, memory=RESERVED_BYTES + NANO_WORKER_BYTES)['workers'] == 1


def test_auto_requests_survive_api_resolution_and_worker_resolution(monkeypatch):
    import nano_resources as resources
    monkeypatch.setattr(resources, 'cpu_budget', lambda: 4)
    memory = [RESERVED_BYTES + 4 * NANO_WORKER_BYTES]
    monkeypatch.setattr(resources, 'available_memory', lambda: memory[0])
    queued = resolve_nano_settings(job(nano_parallel=0, nano_threads=0))
    assert queued['nano_parallel'] == 4 and queued['nano_threads'] == 1
    assert queued['nano_requested_parallel'] == queued['nano_requested_threads'] == 0
    memory[0] = RESERVED_BYTES + NANO_WORKER_BYTES
    resolved = resolve_nano_settings(queued)
    assert resolved['nano_parallel'] == 1
    assert resolved['nano_requested_parallel'] == resolved['nano_requested_threads'] == 0
    legacy = resolve_nano_settings(job(nano_parallel=2, nano_threads=2))
    assert legacy['nano_requested_parallel'] == legacy['nano_requested_threads'] == 2


def test_auto_reuses_fully_started_pool_after_ram_drop_without_allocating_more_models(worker, monkeypatch):
    import nano_resources as resources
    memory = [RESERVED_BYTES + 4 * NANO_WORKER_BYTES]
    monkeypatch.setattr(resources, 'available_memory', lambda: memory[0])
    monkeypatch.setattr(resources, 'cpu_budget', lambda: 4)
    monkeypatch.setattr(worker, 'get_synthesizer', lambda settings: lambda text, path: pcm(path))
    created = []
    def create(settings, count):
        pool = ThreadPoolExecutor(max_workers=count)
        # Mirror an already-spawned ProcessPool. A partial pool must not be
        # considered warm because adding tasks could still start more models.
        pool._processes = {i: SimpleNamespace(is_alive=lambda: True) for i in range(count)}
        created.append(pool)
        return pool
    monkeypatch.setattr(worker, 'create_nano_pool', create)
    settings = job(nano_parallel=0, nano_threads=0)
    worker.render(settings)
    original = worker._nano_pool
    assert len(created) == 1 and worker._nano_pool_key[0] == 4
    memory[0] = RESERVED_BYTES + NANO_WORKER_BYTES // 2
    queued = resolve_nano_settings({**settings, 'id': 'repeat'})
    assert queued['nano_parallel'] == 1  # free RAM excludes existing warm models
    worker.render(queued)
    assert worker._nano_pool is original and len(created) == 1
    result = json.loads((worker.DATA / 'parts/repeat/result.json').read_text())
    progress = json.loads((worker.DATA / 'parts/repeat/progress.json').read_text())
    assert result['nano_parallel'] == 4 and result['nano_threads'] == 1
    assert result['nano_resources']['reused_warm_pool']
    assert progress['nano_parallel'] == 4 and progress['nano_resources']['reused_warm_pool']
    memory[0] = RESERVED_BYTES + 2 * NANO_WORKER_BYTES
    worker.render(job(id='manual', nano_parallel=2, nano_threads=1))
    assert worker._nano_pool is not original and original._shutdown
    assert len(created) == 2 and worker._nano_pool_key[0] == 2


def test_warm_pool_reuse_requires_memory_cpu_voice_and_started_processes(worker, monkeypatch):
    import nano_resources as resources
    memory = [RESERVED_BYTES + NANO_WORKER_BYTES // 2]
    cpus = [4]
    monkeypatch.setattr(resources, 'available_memory', lambda: memory[0])
    monkeypatch.setattr(resources, 'cpu_budget', lambda: cpus[0])
    settings = resolve_nano_settings(job(nano_parallel=0, nano_threads=0))
    pool = ThreadPoolExecutor(max_workers=4)
    pool._processes = {i: SimpleNamespace(is_alive=lambda: True) for i in range(4)}
    monkeypatch.setattr(worker, '_nano_pool', pool)
    monkeypatch.setattr(worker, '_nano_pool_key', (4, worker.synthesis_key(settings)))
    assert worker.resolve_nano_runtime(settings)['nano_parallel'] == 4
    assert worker.resolve_nano_runtime({**settings, 'speaker': 'Other'})['nano_parallel'] == 1
    cpus[0] = 2
    assert worker.resolve_nano_runtime(settings)['nano_parallel'] == 1
    cpus[0] = 4
    memory[0] = RESERVED_BYTES - 1
    assert worker.resolve_nano_runtime(settings)['nano_parallel'] == 1
    memory[0] = RESERVED_BYTES + NANO_WORKER_BYTES // 2
    pool._processes.pop(3)
    assert worker.resolve_nano_runtime(settings)['nano_parallel'] == 1


def test_parallel_render_keeps_every_sentence_order_and_excludes_pause_from_speed(worker, monkeypatch):
    text = 'Câu đầu. [pause=0.2] Câu sau. Câu cuối.'
    values = {'Câu đầu.': .1, 'Câu sau.': .2, 'Câu cuối.': .3}
    finished = []
    def synthesize(text, path):
        if text == 'Câu đầu.':
            time.sleep(.05)
        pcm(path, values[text])
        finished.append(text)
    install_thread_pool(worker, monkeypatch, synthesize)
    worker.render(job(text=text, paragraph_pause=.1))
    assert finished[-1] == 'Câu đầu.'
    samples, rate = sf.read(worker.DATA / 'audio' / 'fixture.wav')
    assert rate == 24000
    assert samples[:2400].mean() == pytest.approx(.1, abs=.001)
    assert not samples[2400:9600].any()  # sentence pause + explicit pause
    assert samples[9600:12000].mean() == pytest.approx(.2, abs=.001)
    assert samples[14400:16800].mean() == pytest.approx(.3, abs=.001)
    result = json.loads((worker.DATA / 'parts/fixture/result.json').read_text())
    assert result['completed'] == result['total'] == 4
    assert result['synthesized_audio_seconds'] == pytest.approx(.3)
    assert result['audio_seconds'] == pytest.approx(.8)
    assert result['reused_chunks'] == 0
    worker.render(job(text=text, paragraph_pause=.1))
    assert len(finished) == 3
    result = json.loads((worker.DATA / 'parts/fixture/result.json').read_text())
    assert result['reused_chunks'] == 3 and result['reused_audio_seconds'] == pytest.approx(.3)


def test_lookahead_keeps_workers_fed_but_bounds_queue_before_ordered_assembly(worker, monkeypatch):
    workers = 3
    first_wave_submitted = threading.Event()
    submitted = []
    assembled_at = []
    class RecordingPool(ThreadPoolExecutor):
        def submit(self, function, *args, **kwargs):
            submitted.append(args[2])  # prepare_chunk index
            future = super().submit(function, *args, **kwargs)
            if len(submitted) == workers * 2:
                first_wave_submitted.set()
            return future
    def synthesize(text, path):
        if text == 'Câu số 0.':
            assert first_wave_submitted.wait(timeout=1), 'workers were starved behind the first chunk'
        pcm(path)
    install_thread_pool(worker, monkeypatch, synthesize)
    monkeypatch.setattr(worker, 'create_nano_pool', lambda settings, count: RecordingPool(max_workers=count))
    original_writer = worker.PCMWriter
    class RecordingWriter(original_writer):
        def append(self, path):
            if not assembled_at:
                assembled_at.append(len(submitted))
            return super().append(path)
    monkeypatch.setattr(worker, 'PCMWriter', RecordingWriter)
    text = ' '.join(f'Câu số {index}.' for index in range(20))
    worker.render(job(text=text, nano_parallel=workers))
    assert assembled_at == [workers * 2]
    assert submitted == list(range(20))
    result = json.loads((worker.DATA / 'parts/fixture/result.json').read_text())
    assert result['completed'] == result['total'] == 20


def test_pool_is_warm_reused_until_voice_or_thread_configuration_changes(worker, monkeypatch):
    created = install_thread_pool(worker, monkeypatch, lambda text, path: pcm(path))
    settings = job()
    first = worker.get_nano_pool(settings, 3)
    assert worker.get_nano_pool(settings, 3) is first
    second = worker.get_nano_pool({**settings, 'nano_threads': 2}, 2)
    assert second is not first and first._shutdown
    third = worker.get_nano_pool({**settings, 'speaker': 'Other'}, 3)
    assert third is not second and second._shutdown
    assert len(created) == 3


def test_warm_spawn_initializer_pins_threads_before_model_loading(worker, monkeypatch):
    calls = []
    monkeypatch.setattr(worker, 'get_synthesizer', lambda settings: calls.append(settings))
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(key, '12')
    settings = job(nano_threads=1)
    worker.initialize_nano_worker(settings)
    import os
    assert calls == [settings]
    assert all(os.environ[key] == '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
    factory = Mock()
    monkeypatch.setattr(worker, 'ProcessPoolExecutor', factory)
    worker.create_nano_pool(settings, 3)
    assert factory.call_args.kwargs['initializer'] is worker.initialize_nano_worker
    assert factory.call_args.kwargs['initargs'] == (settings,)
    assert factory.call_args.kwargs['mp_context'].get_start_method() == 'spawn'


def test_cancel_keeps_complete_checkpoints_and_resume_does_not_skip_words(worker, monkeypatch):
    spoken = []
    cancel = worker.DATA / 'parts/fixture/cancel.flag'
    lock = threading.Lock()
    def synthesize(text, path):
        with lock:
            spoken.append(text)
        pcm(path)
        if text == 'Câu đầu.':
            cancel.touch()
    install_thread_pool(worker, monkeypatch, synthesize)
    with pytest.raises(InterruptedError):
        worker.render(job(text='Câu đầu. Câu sau. Câu cuối.'))
    assert (worker.DATA / 'parts/fixture/000000.wav').is_file()
    assert not (worker.DATA / 'audio/fixture.wav').exists()
    cancel.unlink()
    worker.render(job(text='Câu đầu. Câu sau. Câu cuối.'))
    assert spoken.count('Câu đầu.') == 1
    assert set(spoken) == {'Câu đầu.', 'Câu sau.', 'Câu cuối.'}
    result = json.loads((worker.DATA / 'parts/fixture/result.json').read_text())
    assert result['completed'] == 3 and result['reused_chunks'] >= 1


def test_lookahead_failure_never_replaces_current_segment_error(worker, monkeypatch):
    def synthesize(text, path):
        if text == 'Câu sau.':
            raise RuntimeError('primary failure')
        if text == 'Câu cuối.':
            raise ValueError('lookahead failure')
        pcm(path)
    install_thread_pool(worker, monkeypatch, synthesize)
    with pytest.raises(RuntimeError, match='primary failure'):
        worker.render(job(text='Câu đầu. Câu sau. Câu cuối.'))


def test_changed_text_or_voice_invalidates_parts_but_hardware_changes_keep_resume(worker, monkeypatch):
    spoken = []
    def synthesize(text, path):
        spoken.append(text)
        pcm(path)
    install_thread_pool(worker, monkeypatch, synthesize)
    settings = job()
    worker.render(settings)
    assert len(spoken) == 2
    worker.render({**settings, 'nano_parallel': 2, 'nano_threads': 2})
    assert len(spoken) == 2
    worker.render({**settings, 'text': 'Lời khác.'})
    assert spoken[-1] == 'Lời khác.' and len(spoken) == 3
    worker.render({**settings, 'speaker': 'Other'})
    assert len(spoken) == 5


def test_parallel_srt_keeps_cue_timing_and_speech_only_metric(worker, monkeypatch):
    install_thread_pool(worker, monkeypatch, lambda text, path: pcm(path))
    srt = '1\n00:00:00,500 --> 00:00:01,000\nCâu đầu.\n\n2\n00:00:01,500 --> 00:00:02,000\nCâu sau.\n'
    worker.render(job(text=srt, input_format='srt', paragraph_pause=3, cue_fit='strict'))
    samples, _ = sf.read(worker.DATA / 'audio/fixture.wav')
    assert not samples[:12000].any() and samples[12000:14400].any()
    assert not samples[14400:36000].any() and samples[36000:38400].any()
    result = json.loads((worker.DATA / 'parts/fixture/result.json').read_text())
    assert result['audio_seconds'] == 2 and result['synthesized_audio_seconds'] == pytest.approx(.2)
    alignment = json.loads((worker.DATA / 'parts/fixture/alignment.json').read_text())
    assert alignment['sync_ok']


def test_duration_cap_discards_lookahead_failure_and_reports_unread_text(worker, monkeypatch):
    def synthesize(text, path):
        if text == 'Câu sau.':
            raise RuntimeError('unneeded chunk failed')
        pcm(path, seconds=.2)
    install_thread_pool(worker, monkeypatch, synthesize)
    worker.render(job(max_minutes=.1 / 60))
    samples, _ = sf.read(worker.DATA / 'audio/fixture.wav')
    assert len(samples) == 2400
    result = json.loads((worker.DATA / 'parts/fixture/result.json').read_text())
    assert result['duration_limited'] and result['completed'] == 1
    assert result['total'] == 2


def test_nano_clone_enrolls_selected_reference_once_and_never_uses_preset(worker, monkeypatch):
    reference = worker.DATA / 'voices/clone.wav'
    pcm(reference)
    model = Mock()
    model.infer.return_value = np.ones(10)
    factory = Mock(return_value=model)
    monkeypatch.setitem(sys.modules, 'vieneu.v3nano', SimpleNamespace(V3NanoVieNeuTTS=factory))
    import nano_voice
    encoded = {'speaker_emb': np.ones(192), 'style': np.ones((50, 256))}
    enroll = Mock(return_value=encoded)
    monkeypatch.setattr(nano_voice, 'load_nano_reference', enroll)
    settings = job(speaker=None, voice_id='clone')
    synthesize = worker.get_synthesizer(settings)
    synthesize('Câu đầu.', worker.DATA / 'one.wav')
    worker.get_synthesizer(settings)('Câu sau.', worker.DATA / 'two.wav')
    enroll.assert_called_once_with(model, reference)
    assert factory.call_count == 1
    assert all(call.kwargs['voice'] is encoded for call in model.infer.call_args_list)
    pcm(reference, seconds=.2)
    worker.get_synthesizer(settings)
    assert factory.call_count == 2 and enroll.call_count == 2


def test_nano_reference_cleaning_is_local_and_removed_on_encoding_failure(tmp_path, monkeypatch):
    from nano_voice import load_nano_reference
    original = tmp_path / 'original.wav'
    clean = tmp_path / 'temporary.wav'
    original.write_bytes(b'original')
    clean.write_bytes(b'clean')
    cleaner = Mock(return_value=clean)
    monkeypatch.setitem(sys.modules, 'local_vieneu', SimpleNamespace(LocalVieneu=SimpleNamespace(_preclean_reference_audio=cleaner)))
    model = SimpleNamespace(engine=SimpleNamespace(prepare_reference=Mock(side_effect=ValueError('bad reference'))))
    with pytest.raises(ValueError, match='bad reference'):
        load_nano_reference(model, original)
    cleaner.assert_called_once_with(original)
    model.engine.prepare_reference.assert_called_once_with(str(clean), denoise=False)
    assert not clean.exists() and original.read_bytes() == b'original'
