"""Native selection must preserve references and require the chosen runtime."""
import pytest

import app
import fast_multilingual
from test_reference_voices_api import (reference_catalog, prepared_international_model,
                                       KOREAN, THAI, ENGLISH)
from test_standalone_api import studio  # noqa: F401


def installed(monkeypatch, devices=('cpu',)):
    monkeypatch.setattr(fast_multilingual, 'is_ready',
                        lambda data, device=None: bool(devices) if device is None else device in devices)
    monkeypatch.setattr(fast_multilingual, 'cuda_available', lambda data: 'cuda' in devices)


def test_native_only_install_lists_same_reference_ids(reference_catalog, monkeypatch):
    client, data, root, submit = reference_catalog
    installed(monkeypatch)
    voices = {v['id']: v for v in client.get('/api/voices').json()['voices']}
    for ident in (KOREAN, THAI):
        assert voices[ident]['ready'] and voices[ident]['ready_native']
        assert not voices[ident]['ready_voxcpm']
        assert voices[ident]['has_sample']
        assert 'transcript' not in voices[ident]
    config = client.get('/api/config').json()
    assert config['native_multilingual_ready']
    assert not config['native_multilingual_cuda_available']
    assert not config['models']['voxcpm']


@pytest.mark.parametrize('device', ('cpu', 'cuda'))
def test_native_srt_keeps_voice_language_timeline_and_one_model(reference_catalog, monkeypatch, device):
    client, data, root, submit = reference_catalog
    installed(monkeypatch, ('cpu', 'cuda'))
    # VoxCPM's FP32 budget must not reject a native Q8 model on a smaller PC.
    monkeypatch.setattr(app, 'rendering_limits', lambda *a, **k: pytest.fail('VoxCPM budget applied to native'))
    script = '1\n00:00:01,200 --> 00:00:03,500\n안녕하세요.\n'
    response = client.post('/api/speech', json={
        'voice_id': KOREAN, 'language': 'ko', 'text': script, 'input_format': 'srt',
        'international_backend': 'omnivoice', 'international_device': device,
        'omnivoice_steps': 16, 'nano_parallel': 32, 'nano_threads': 8})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['voice_id'] == KOREAN and job['speaker'] is None
    assert job['engine'] == 'voxcpm' and job['language'] == 'ko'
    assert job['international_backend'] == 'omnivoice' and job['international_device'] == device
    assert job['nano_parallel'] == 1 and job['nano_threads'] == 8
    assert job['model_memory'] == 'native' and job['omnivoice_steps'] == 16
    assert app.parse_srt(job['text']) == app.parse_srt(script)
    assert (root / 'voices' / f'{KOREAN}.wav').is_file()
    submit.assert_called_once_with(app.run_job, job['id'])


def test_native_benchmark_uses_selected_language_and_fast_steps(reference_catalog, monkeypatch):
    client, data, root, submit = reference_catalog
    installed(monkeypatch)
    response = client.post('/api/benchmark', json={
        'voice_id': THAI, 'language': 'th', 'render_mode': 'fast',
        'international_backend': 'omnivoice', 'nano_parallel': 8})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['voice_id'] == THAI and job['language'] == 'th'
    assert job['nano_parallel'] == 1 and job['omnivoice_steps'] == 8
    assert job['paragraph_pause'] == 0 and 'Đây là đoạn đo' not in job['text']


def test_missing_native_does_not_fall_back_to_installed_voxcpm(reference_catalog, monkeypatch):
    client, data, root, submit = reference_catalog
    prepared_international_model(data, monkeypatch)
    installed(monkeypatch, ())
    response = client.post('/api/speech', json={
        'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.',
        'international_backend': 'omnivoice'})
    assert response.status_code == 503
    assert 'TAI_GIONG_DA_NGON_NGU_NHANH.bat' in response.json()['detail']
    submit.assert_not_called()


def test_missing_cuda_does_not_fall_back_to_cpu(reference_catalog, monkeypatch):
    client, data, root, submit = reference_catalog
    installed(monkeypatch)
    response = client.post('/api/speech', json={
        'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.',
        'international_backend': 'omnivoice', 'international_device': 'cuda'})
    assert response.status_code == 503
    submit.assert_not_called()


@pytest.mark.parametrize('settings', (
    {'international_backend': 'omnivoice', 'omnivoice_steps': 12},
    {'international_backend': 'voxcpm', 'international_device': 'cuda'},
    {'international_backend': 'omnivoice', 'international_precision': 'int8'},
))
def test_invalid_native_settings_are_rejected(reference_catalog, monkeypatch, settings):
    client, data, root, submit = reference_catalog
    installed(monkeypatch)
    response = client.post('/api/speech', json={
        'voice_id': KOREAN, 'language': 'ko', 'text': '안녕하세요.', **settings})
    assert response.status_code == 422
    submit.assert_not_called()


def test_turbo_reference_cannot_be_silently_switched(reference_catalog, monkeypatch):
    client, data, root, submit = reference_catalog
    installed(monkeypatch)
    (data / 'models/vieneu.ready').touch()
    response = client.post('/api/speech', json={
        'voice_id': ENGLISH, 'language': 'en-US', 'text': 'Hello.',
        'international_backend': 'omnivoice'})
    assert response.status_code == 422
    submit.assert_not_called()
