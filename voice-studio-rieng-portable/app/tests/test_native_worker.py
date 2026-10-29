"""Native multilingual routing, model lifetime and timeline integration."""
import json
import sys
from types import SimpleNamespace
import wave

import pytest

from narration import Segment
from test_worker_optimization import worker, tones, write_pcm  # noqa: F401


@pytest.fixture
def native_worker(worker, monkeypatch):
    monkeypatch.setattr(worker, '_cached_key', None)
    monkeypatch.setattr(worker, '_cached_synth', None)
    return worker


def test_native_constructor_preserves_reference_language_and_transcript(native_worker, tmp_path, monkeypatch):
    events = []
    reference = tmp_path/'original-reference.wav'
    def create(path, data, **options):
        events.append(('create', path, data, options))
        return object()
    monkeypatch.setitem(sys.modules, 'voice_library', SimpleNamespace(
        resolve_reference=lambda ident, data: (reference, {'transcript': 'Bonjour, voici le texte original.', 'native_language': 'en'})))
    monkeypatch.setitem(sys.modules, 'voxcpm_backend', SimpleNamespace(close_backends=lambda: events.append('close-voxcpm')))
    monkeypatch.setitem(sys.modules, 'fast_multilingual', SimpleNamespace(create_synthesizer=create))
    native_worker.load_synthesizer({'engine': 'voxcpm', 'international_backend': 'omnivoice',
                                   'voice_id': 'chosen', 'language': 'fr', 'nano_threads': 3,
                                   'international_device': 'cuda', 'omnivoice_steps': 24})
    assert events == ['close-voxcpm', ('create', reference, tmp_path, {
        'threads': 3, 'steps': 24, 'device': 'cuda', 'language': 'fr',
        'reference_text': 'Bonjour, voici le texte original.', 'reference_language': 'en'})]


def test_legacy_constructor_releases_native_before_loading_voxcpm(native_worker, tmp_path, monkeypatch):
    events = []
    reference = tmp_path/'reference.wav'
    def create(path, data, **options):
        events.append(('create', path, data, options))
        return object()
    monkeypatch.setitem(sys.modules, 'voice_library', SimpleNamespace(
        resolve_reference=lambda ident, data: (reference, {})))
    monkeypatch.setitem(sys.modules, 'fast_multilingual', SimpleNamespace(close_backends=lambda: events.append('close-native')))
    monkeypatch.setitem(sys.modules, 'voxcpm_backend', SimpleNamespace(create_synthesizer=create))
    native_worker.load_synthesizer({'engine': 'voxcpm', 'voice_id': 'old', 'nano_threads': 2,
                                   'voxcpm_steps': 8, 'international_precision': 'int8'})
    assert events == ['close-native', ('create', reference, tmp_path,
                                      {'threads': 2, 'steps': 8, 'precision': 'int8'})]


@pytest.mark.parametrize('changed', [
    {'international_backend': 'voxcpm'}, {'international_device': 'cuda'}, {'omnivoice_steps': 32}])
def test_native_model_selection_is_part_of_cached_synthesizer_key(native_worker, monkeypatch, changed):
    loaded = []
    def load(job):
        result = object()
        loaded.append(result)
        return result
    monkeypatch.setattr(native_worker, 'load_synthesizer', load)
    job = {'engine': 'voxcpm', 'international_backend': 'omnivoice',
           'voice_id': 'same', 'language': 'fr', 'international_device': 'cpu', 'omnivoice_steps': 16}
    first = native_worker.get_synthesizer(job)
    assert native_worker.get_synthesizer(job) is first
    assert native_worker.get_synthesizer({**job, **changed}) is not first
    assert len(loaded) == 2


def test_reset_closes_both_international_model_families(native_worker, monkeypatch):
    closed = []
    monkeypatch.setitem(sys.modules, 'voxcpm_backend', SimpleNamespace(close_backends=lambda: closed.append('voxcpm')))
    monkeypatch.setitem(sys.modules, 'fast_multilingual', SimpleNamespace(close_backends=lambda: closed.append('native')))
    native_worker.reset_nano_models()
    assert closed == ['voxcpm', 'native']
    assert native_worker._cached_synth is None and native_worker._cached_key is None


def _start_synthetic_backend_process(marker):
    """An isolated stand-in for a resident international Python runtime."""
    import subprocess
    child = subprocess.Popen([sys.executable, '-c', 'import threading; threading.Event().wait()'])
    def close():
        from pathlib import Path
        child.terminate()
        child.wait(timeout=5)
        Path(marker).write_text(json.dumps({'pid': child.pid, 'returncode': child.returncode}))
    sys.modules['fast_multilingual'] = SimpleNamespace(close_backends=close)
    return child.pid


def test_replacing_process_pool_releases_its_resident_backend(native_worker, tmp_path):
    import os
    import signal
    pool = native_worker.create_render_pool(1, {'engine': 'voxcpm', 'model_memory': 'process'})
    pid = None
    marker = tmp_path/'backend-closed.json'
    try:
        pid = pool.submit(_start_synthetic_backend_process, str(marker)).result(timeout=20)
        assert not marker.exists()
        pool.shutdown(wait=True)
        closed = json.loads(marker.read_text())
        assert closed['pid'] == pid and closed['returncode'] is not None
    finally:
        pool.shutdown(wait=True)
        if pid is not None and not marker.exists():
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def test_native_render_caps_raw_job_to_one_model_and_keeps_srt_timeline(native_worker, tmp_path, monkeypatch):
    calls = []
    def native(text, path):
        calls.append(text)
        write_pcm(path, tones([220], .1))
    monkeypatch.setattr(native_worker, 'get_synthesizer', lambda job: native)
    monkeypatch.setattr(native_worker, 'create_render_pool', lambda *args: pytest.fail('native model must remain single-session'))
    monkeypatch.setitem(sys.modules, 'fast_multilingual', SimpleNamespace(
        execution_info=lambda: {'backend': 'omnivoice', 'device': 'cuda', 'precision': 'q8_0', 'threads': 3}))
    text = '1\n00:00:00,000 --> 00:00:00,500\nBonjour.\n\n2\n00:00:01,000 --> 00:00:01,500\nBonsoir.'
    native_worker.render({'id': 'native', 'text': text, 'input_format': 'srt', 'engine': 'voxcpm',
                          'international_backend': 'omnivoice', 'international_device': 'auto',
                          'omnivoice_steps': 16, 'nano_threads': 3, 'nano_parallel': 8,
                          'language': 'fr', 'format': 'wav', 'speed': 1, 'cue_fit': 'strict'})
    result = json.loads((tmp_path/'parts/native/result.json').read_text())
    actual = result['execution_settings']
    assert calls == ['Bonjour.', 'Bonsoir.']
    assert actual['workers'] == actual['worker_budget'] == 1
    assert actual['backend'] == 'omnivoice' and actual['device'] == 'cuda'
    assert actual['precision'] == 'q8_0' and actual['omnivoice_steps'] == 16
    assert result['audio_seconds'] == 1.5 and result['spoken_audio_seconds'] == pytest.approx(.2)
    with wave.open(str(tmp_path/'audio/native.wav')) as audio:
        assert audio.getnframes() == 36000 and audio.getframerate() == 24000
    alignment = json.loads((tmp_path/'parts/native/alignment.json').read_text())
    assert alignment['sync_ok'] and [cue['start'] for cue in alignment['cues']] == [0, 1]


@pytest.mark.parametrize('changed', [
    {'international_backend': 'voxcpm'}, {'international_device': 'cuda'}, {'omnivoice_steps': 32}])
def test_fitted_cue_cache_tracks_native_backend_device_and_steps(native_worker, tmp_path, monkeypatch, changed):
    writes = []
    original_writer = native_worker.PCMWriter
    def writer(*args, **kwargs):
        writes.append(args[0])
        return original_writer(*args, **kwargs)
    def prepare(job, segment, index, work):
        path = work/f'{index:06d}.wav'
        if not path.exists():
            write_pcm(path, tones([220], .1))
    monkeypatch.setattr(native_worker, 'PCMWriter', writer)
    monkeypatch.setattr(native_worker, 'prepare_chunk', prepare)
    job = {'engine': 'voxcpm', 'international_backend': 'omnivoice',
           'international_device': 'cpu', 'omnivoice_steps': 16, 'cue_fit': 'strict'}
    args = (0, {'start': 0, 'end': .5}, [(0, Segment(text='Bonjour.'))], tmp_path, .5)
    native_worker.prepare_cue(job, *args)
    native_worker.prepare_cue(job, *args)
    assert len(writes) == 1
    native_worker.prepare_cue({**job, **changed}, *args)
    assert len(writes) == 2
