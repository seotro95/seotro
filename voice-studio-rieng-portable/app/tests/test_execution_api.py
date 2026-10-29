"""CPU execution selection preserves the chosen voice and quality through HTTP."""
from unittest.mock import Mock

import pytest
import app
from test_standalone_api import studio  # noqa: F401
from test_reference_voices_api import reference_catalog, ENGLISH


@pytest.mark.parametrize('execution', ['auto', 'shared', 'process'])
def test_turbo_cpu_execution_preserves_voice_quality_and_script(studio, monkeypatch, execution):
    client, data = studio
    monkeypatch.setattr(app.executor, 'submit', Mock())
    (data / 'models/vieneu.ready').touch()
    text = 'Giữ nguyên lời đọc và giọng Ngọc Huyền.'
    voice = next(v for v in app.available_voices() if v.get('speaker') == 'Ngọc Huyền')
    response = client.post('/api/speech', json={
        'voice_id': voice['id'], 'text': text, 'quality': 'standard',
        'render_mode': 'quality', 'nano_steps': 16, 'cpu_execution': execution,
    })
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['speaker'] == 'Ngọc Huyền' and job['engine'] == 'vieneu'
    assert job['text'] == text and job['quality'] == 'standard' and job['nano_steps'] == 16
    assert job['cpu_execution'] == execution
    assert job['model_memory'] == ('process' if execution == 'process' else 'shared')


def test_english_reference_cpu_calibration_keeps_native_text_and_precision(reference_catalog):
    client, data, _, _ = reference_catalog
    (data / 'models/vieneu.ready').touch()
    response = client.post('/api/calibrate', json={
        'voice_id': ENGLISH, 'language': 'en-US', 'quality': 'standard',
        'render_mode': 'quality', 'cpu_execution': 'auto',
    })
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['calibration'] and job['engine'] == 'vieneu' and job['voice_id'] == ENGLISH
    assert job['language'] == 'en-US' and job['quality'] == 'standard'
    assert 'The morning light' in job['text'] and 'Đây là đoạn' not in job['text']


def test_quick_machine_report_skips_torch_cuda_probe(studio, monkeypatch):
    client, _ = studio
    flags = []
    def info(include_cuda_probe=True):
        flags.append(include_cuda_probe)
        return {'nvidia_gpus': ['Synthetic GPU, 8192 MiB']}
    monkeypatch.setattr(app, 'system_info', info)
    assert client.get('/api/system-info?quick=true').json()['nvidia_gpus'] == ['Synthetic GPU, 8192 MiB']
    assert client.get('/api/system-info').status_code == 200
    assert flags == [False, True]


def test_saved_auto_winner_is_used_by_configuration_and_submission(studio, monkeypatch):
    import json
    import os
    import hardware
    client, data = studio
    monkeypatch.setattr(app.executor, 'submit', Mock())
    monkeypatch.setattr(hardware, '_machine_resources', lambda *args, **kwargs: (56, 28, 128))
    (data / 'models/vieneu.ready').touch()
    (data / 'calibration.json').write_text(json.dumps({
        'logical_cores': os.cpu_count(),
        'execution_choices': {'vieneu:smooth:fast:fp32': {
            'model_memory': 'process', 'nano_steps': 4,
            'settings': {'nano_parallel': 8, 'nano_threads': 2},
            'measurements': {'shared': {'realtime_multiplier': 4}, 'process': {'realtime_multiplier': 8}},
        }},
    }))
    config = client.get('/api/config').json()
    selected = config['rendering_presets_by_resource']['smooth']['vieneu']['fast']
    assert (selected['nano_parallel'], selected['nano_threads']) == (8, 2)
    response = client.post('/api/speech', json={
        'voice_id': 'vi-maianh', 'text': 'Giữ đúng giọng đã chọn.',
        'quality': 'standard', 'render_mode': 'fast', 'cpu_execution': 'auto',
    })
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['model_memory'] == 'process' and job['speaker'] == 'Mai Anh'
    assert (job['nano_parallel'], job['nano_threads']) == (8, 2)
    int8 = config['turbo_int8_rendering_presets_by_resource']['smooth']['fast']
    assert (int8['nano_parallel'], int8['nano_threads']) != (8, 2)
    for execution in ('shared', 'process'):
        assert set(config['turbo_int8_cpu_execution_rendering_presets'][execution]) == {'maximum', 'smooth', 'light'}
