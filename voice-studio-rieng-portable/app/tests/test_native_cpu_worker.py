"""CPU native jobs can overlap independent cues; CUDA stays single-context."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading

from test_native_worker import native_worker  # noqa: F401
from test_worker_optimization import worker, tones, write_pcm  # noqa: F401


def test_independent_native_cpu_cues_run_concurrently_without_reordering(native_worker, tmp_path, monkeypatch):
    barrier = threading.Barrier(2)
    threads = set()
    def synthesize(text, path):
        threads.add(threading.get_ident())
        barrier.wait(timeout=10)
        write_pcm(path, tones([220 if text == 'Bonjour.' else 440], .1))
    monkeypatch.setattr(native_worker, 'get_synthesizer', lambda job: synthesize)
    monkeypatch.setattr(native_worker, 'create_render_pool', lambda workers, job: ThreadPoolExecutor(max_workers=workers))
    text = '1\n00:00:00,000 --> 00:00:00,500\nBonjour.\n\n2\n00:00:01,000 --> 00:00:01,500\nBienvenue.'
    try:
        native_worker.render({'id': 'cpu-native-parallel', 'text': text, 'input_format': 'srt',
            'engine': 'voxcpm', 'language': 'fr', 'international_backend': 'voxcpm_native',
            'international_device': 'cpu', 'voxcpm_steps': 8, 'nano_threads': 2, 'nano_parallel': 2,
            'format': 'wav', 'speed': 1, 'cue_fit': 'strict'})
        result = json.loads((tmp_path / 'parts/cpu-native-parallel/result.json').read_text())
        assert len(threads) == 2
        assert result['execution_settings']['workers'] == 2
        assert result['execution_settings']['device'] == 'cpu'
        assert result['execution_settings']['backend'] == 'voxcpm_native'
        assert result['audio_seconds'] == 1.5
        alignment = json.loads((tmp_path / 'parts/cpu-native-parallel/alignment.json').read_text())
        assert alignment['sync_ok'] and [cue['start'] for cue in alignment['cues']] == [0, 1]
    finally:
        native_worker.close_nano_pool()
