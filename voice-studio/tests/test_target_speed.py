from unittest.mock import patch

from narration import plan_segments
from performance import speed_report
from test_app import studio  # noqa: F401


def test_target_math_and_invalid_measurements():
    assert speed_report(3600, 120)['target_30x_met_on_sample']
    assert speed_report(60, 2)['estimated_hour_seconds'] == 120
    assert not speed_report(60, 3)['target_30x_met_on_sample']
    assert speed_report(60, 3)['estimated_hour_seconds'] == 180
    assert speed_report(0, 1) is None
    assert speed_report(1, 0) is None


def test_packing_is_explicit_bounded_and_keeps_controls():
    text = 'Câu thứ nhất. Câu thứ hai. **Quan trọng** [pause=1] Câu cuối.'
    classic = plan_segments({'text': text})
    packed = plan_segments({'text': text, 'segment_plan': 'nano-packed-v1'})
    assert len(packed) < len(classic)
    assert packed[0].text == 'Câu thứ nhất. Câu thứ hai.'
    assert any(s.text == 'Quan trọng' and s.emphasis for s in packed)
    assert any(s.pause == 1 for s in packed)
    assert all(len(s.text) <= 130 for s in packed)
    assert plan_segments({'text': text}) == classic


def test_new_jobs_record_plan_and_steps_for_safe_resume(studio):
    client, root = studio
    (root / 'models' / 'vieneu_nano.ready').touch()
    with patch('app.executor.submit'):
        r = client.post('/api/speech', json={'text': 'Xin chào. Chào mọi người.', 'voice_id': 'nano-minhquan', 'paragraph_pause': 0, 'nano_steps': 4})
        assert r.status_code == 202
        assert r.json()['segment_plan'] == 'nano-packed-v1' and r.json()['total'] == 1
        assert r.json()['nano_steps'] == 4
        r = client.post('/api/speech', json={'text': 'Xin chào. Chào mọi người.', 'voice_id': 'nano-minhquan', 'paragraph_pause': 0.3})
        assert r.json()['segment_plan'] == 'classic-v1' and r.json()['total'] == 2
    assert client.post('/api/speech', json={'text': 'Test', 'voice_id': 'nano-minhquan', 'nano_steps': 1}).status_code == 422


def test_system_info_route_can_report_without_credentials(studio):
    client, _ = studio
    with patch('app.system_info', return_value={'cpu': 'Test CPU', 'ram_gb': 16, 'nvidia_gpus': [], 'pytorch_cuda_available': False}):
        r = client.get('/api/system-info')
    assert r.status_code == 200 and r.json()['ram_gb'] == 16


def test_parallel_completion_keeps_script_order_and_reuses_parts(tmp_path, monkeypatch):
    import importlib
    import time
    from concurrent.futures import ThreadPoolExecutor
    import numpy as np
    import soundfile as sf
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    finished = []
    def synthesize(text, output):
        if text == 'Câu đầu.':
            time.sleep(.06)  # second segment finishes first
        value = .1 if text == 'Câu đầu.' else .2
        sf.write(output, np.full(2400, value), 24000)
        finished.append(text)
    monkeypatch.setattr(worker, 'get_synthesizer', lambda job: synthesize)
    pool = ThreadPoolExecutor(max_workers=2)
    monkeypatch.setattr(worker, '_nano_pool', pool)
    job = {'id': 'parallel', 'text': 'Câu đầu. Câu sau.', 'engine': 'vieneu_nano', 'nano_parallel': 2, 'format': 'wav', 'speed': 1, 'paragraph_pause': 0}
    try:
        worker.render(job)
        assert finished == ['Câu sau.', 'Câu đầu.']
        samples, _ = sf.read(tmp_path / 'audio' / 'parallel.wav')
        assert abs(samples[:2400].mean() - .1) < .001
        assert abs(samples[2400:].mean() - .2) < .001
        worker.render(job)
        assert len(finished) == 2  # completed chunks were not regenerated
    finally:
        pool.shutdown()
