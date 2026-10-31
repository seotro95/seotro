"""The quantized VoxCPM path keeps voices/languages and requires its own runtime."""
import pytest

import app
import fast_multilingual
from test_reference_voices_api import reference_catalog, KOREAN, THAI, ENGLISH
from test_standalone_api import studio  # noqa: F401


def installed(monkeypatch, devices=('cpu', 'cuda'), cpu_workers=1):
    monkeypatch.setattr(fast_multilingual, 'is_ready', lambda data, device=None, family='omnivoice':
                        family == 'voxcpm2' and (bool(devices) if device is None else device in devices))
    monkeypatch.setattr(fast_multilingual, 'cuda_available', lambda data, family='omnivoice':
                        family == 'voxcpm2' and 'cuda' in devices)
    monkeypatch.setattr(app, 'native_voxcpm_cpu_limits', lambda profile='smooth': {
        'max_workers': cpu_workers, 'max_threads': 8, 'cpu_budget': max(4, cpu_workers * 4), 'memory_sufficient': True})
    monkeypatch.setattr(app, 'native_voxcpm_cpu_presets', lambda profile='smooth': {
        mode: {'nano_parallel': cpu_workers, 'nano_threads': 4, 'voxcpm_steps': steps,
               'audio_fit_backend': 'wsola' if mode == 'fast' else 'ffmpeg'}
        for mode, steps in [('fast', 4), ('balanced', 8), ('quality', 10)]})


def test_native_voxcpm_only_install_keeps_defaults_ready_without_pytorch(reference_catalog, monkeypatch):
    client, data, _, _ = reference_catalog
    installed(monkeypatch)
    voices = {v['id']: v for v in client.get('/api/voices').json()['voices']}
    for ident in (KOREAN, THAI):
        assert voices[ident]['ready_voxcpm_native'] and voices[ident]['ready']
        assert not voices[ident]['ready_native'] and not voices[ident]['ready_voxcpm']
    cfg = client.get('/api/config').json()
    assert cfg['native_voxcpm_cpu_available'] and cfg['native_voxcpm_cuda_available']
    assert not cfg['models']['voxcpm'] and not cfg['native_multilingual_ready']


@pytest.mark.parametrize('device', ['cpu', 'cuda'])
@pytest.mark.parametrize('mode,steps', [('fast', 4), ('balanced', 8), ('quality', 10)])
def test_native_voxcpm_keeps_voice_steps_and_single_model(reference_catalog, monkeypatch, device, mode, steps):
    client, data, root, submit = reference_catalog
    installed(monkeypatch)
    monkeypatch.setattr(app, 'rendering_limits', lambda *a, **k: pytest.fail('legacy model RAM budget used'))
    result = client.post('/api/speech', json={
        'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.',
        'international_backend': 'voxcpm_native', 'international_device': device,
        'render_mode': mode, 'nano_parallel': 32,
    })
    assert result.status_code == 202, result.text
    job = result.json()
    assert job['voice_id'] == KOREAN and job['language'] == 'ko' and job['speaker'] is None
    assert job['international_backend'] == 'voxcpm_native' and job['international_device'] == device
    assert job['nano_parallel'] == 1 and job['model_memory'] == 'native'
    assert job['voxcpm_steps'] == steps
    assert (root / 'voices' / (KOREAN + '.wav')).is_file()
    submit.assert_called_once_with(app.run_job, job['id'])


def test_missing_cuda_does_not_use_a_different_backend(reference_catalog, monkeypatch):
    client, data, _, submit = reference_catalog
    installed(monkeypatch, ('cpu',))
    r = client.post('/api/speech', json={'voice_id': THAI, 'language': 'th', 'text': 'สวัสดี',
        'international_backend': 'voxcpm_native', 'international_device': 'cuda'})
    assert r.status_code == 503 and 'CUDA' in r.json()['detail']
    submit.assert_not_called()


def test_native_voxcpm_srt_keeps_timestamps_and_explicit_steps(reference_catalog, monkeypatch):
    client, data, _, _ = reference_catalog
    installed(monkeypatch)
    text = '1\n00:00:01,000 --> 00:00:03,000\n안녕하세요.\n\n2\n00:00:04,000 --> 00:00:06,000\n다음 문장입니다.'
    r = client.post('/api/speech', json={'voice_id': KOREAN, 'language': 'ko', 'text': text,
        'input_format': 'srt', 'international_backend': 'voxcpm_native', 'voxcpm_steps': 10})
    assert r.status_code == 202, r.text
    assert r.json()['text'] == text and r.json()['voxcpm_steps'] == 10
    assert r.json()['segment_plan'] == 'classic-v1'


def test_native_voxcpm_benchmark_uses_selected_language(reference_catalog, monkeypatch):
    client, data, _, _ = reference_catalog
    installed(monkeypatch)
    r = client.post('/api/benchmark', json={'voice_id': THAI, 'language': 'th',
        'international_backend': 'voxcpm_native', 'international_device': 'cuda'})
    assert r.status_code == 202, r.text
    assert r.json()['nano_parallel'] == 1 and r.json()['international_device'] == 'cuda'
    assert r.json()['voice_id'] == THAI and 'Đây là đoạn đo' not in r.json()['text']


@pytest.mark.parametrize('settings', [{'voxcpm_steps': 6}, {'international_precision': 'int8'}])
def test_invalid_native_voxcpm_settings_do_not_start_a_job(reference_catalog, monkeypatch, settings):
    client, data, _, submit = reference_catalog
    installed(monkeypatch)
    r = client.post('/api/speech', json={'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.',
        'international_backend': 'voxcpm_native', **settings})
    assert r.status_code == 422
    submit.assert_not_called()


def test_turbo_reference_is_never_replaced_by_native_voxcpm(reference_catalog, monkeypatch):
    client, data, _, submit = reference_catalog
    installed(monkeypatch)
    (data / 'models/vieneu.ready').touch()
    r = client.post('/api/speech', json={'voice_id': ENGLISH, 'language': 'en-US', 'text': 'Hello.',
        'international_backend': 'voxcpm_native'})
    assert r.status_code == 422
    submit.assert_not_called()


def test_many_core_native_cpu_keeps_model_family_and_bounded_parallelism(reference_catalog, monkeypatch):
    client, data, _, _ = reference_catalog
    installed(monkeypatch, cpu_workers=7)
    r = client.post('/api/speech', json={'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요. 다음 문장입니다.',
        'international_backend': 'voxcpm_native', 'international_device': 'cpu', 'resource_profile': 'maximum', 'render_mode': 'quality'})
    assert r.status_code == 202, r.text
    job = r.json()
    assert job['nano_parallel'] == 7 and job['nano_threads'] == 4 and job['voxcpm_steps'] == 10
    assert job['voice_id'] == KOREAN and job['language'] == 'ko'


def test_gpu_remains_single_context_on_a_many_core_machine(reference_catalog, monkeypatch):
    client, data, _, _ = reference_catalog
    installed(monkeypatch, cpu_workers=7)
    r = client.post('/api/speech', json={'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.',
        'international_backend': 'voxcpm_native', 'international_device': 'cuda', 'nano_parallel': 7})
    assert r.status_code == 202, r.text
    assert r.json()['nano_parallel'] == 1


def test_native_cpu_low_available_memory_does_not_queue(reference_catalog, monkeypatch):
    client, data, _, submit = reference_catalog
    installed(monkeypatch)
    monkeypatch.setattr(app, 'native_voxcpm_cpu_limits', lambda profile='smooth': {'memory_sufficient': False})
    r = client.post('/api/speech', json={'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.',
        'international_backend': 'voxcpm_native', 'international_device': 'cpu'})
    assert r.status_code == 503 and 'RAM' in r.json()['detail']
    submit.assert_not_called()
