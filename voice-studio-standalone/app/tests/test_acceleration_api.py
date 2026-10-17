"""Queue and reporting contracts. Readiness markers are isolated test fixtures."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app
from performance import speed_report


@pytest.fixture
def studio(tmp_path, monkeypatch):
    for folder in ('voices', 'audio', 'jobs', 'models', 'parts'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    ident = 'a' * 32
    app.write_json(tmp_path / 'voices' / f'{ident}.json', {
        'id': ident, 'name': 'Mẫu của người dùng', 'languages': ['vi'], 'category': 'cloned',
    })
    with TestClient(app.app) as client:
        yield client, tmp_path, ident


def test_nano_clone_requires_its_own_preparation_and_never_changes_voice(studio):
    client, data, ident = studio
    (data / 'models' / 'vieneu_nano.ready').touch()
    payload = {'text': 'Lời đọc giữ đúng mẫu đã chọn.', 'voice_id': ident, 'clone_engine': 'nano'}
    denied = client.post('/api/speech', json=payload)
    assert denied.status_code == 503
    assert 'TAI_GIONG_NHAN_BAN_NHANH.bat' in denied.json()['detail']
    (data / 'models' / 'vieneu_nano_clone.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json=payload)
    assert response.status_code == 202, response.text
    job = response.json()
    assert (job['engine'], job['voice_id'], job['speaker']) == ('vieneu_nano', ident, None)
    assert job['nano_parallel'] >= 1 and job['nano_threads'] >= 1
    entry = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == ident)
    assert entry['ready_engines']['vieneu_nano'] is True
    assert entry['ready_engines']['vieneu'] is False


def test_nano_clone_does_not_fallback_for_non_vietnamese_or_presets(studio):
    client, data, ident = studio
    (data / 'models' / 'vieneu_nano_clone.ready').touch()
    assert client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'nano-minhquan', 'clone_engine': 'nano'}).status_code == 422
    other = 'b' * 32
    app.write_json(data / 'voices' / f'{other}.json', {'id': other, 'name': 'English reference', 'languages': ['en-US'], 'category': 'cloned'})
    assert client.post('/api/speech', json={'text': 'Hello.', 'voice_id': other, 'language': 'en-US', 'clone_engine': 'nano'}).status_code == 422
    assert not list((data / 'jobs').iterdir())


def test_benchmark_uses_new_text_with_selected_reference_and_same_queue(studio):
    client, data, ident = studio
    (data / 'models' / 'vieneu_nano_clone.ready').touch()
    payload = {'voice_id': ident, 'language': 'vi', 'clone_engine': 'nano', 'nano_steps': 4,
               'nano_parallel': 0, 'nano_threads': 0, 'quality': 'auto'}
    with patch.object(app.executor, 'submit') as submit:
        response = client.post('/api/benchmark', json=payload)
    assert response.status_code == 202, response.text
    job = response.json()
    submit.assert_called_once_with(app.run_job, job['id'])
    assert job['benchmark'] is True and job['voice_id'] == ident and job['speaker'] is None
    assert job['engine'] == 'vieneu_nano' and len(job['text']) > 1000
    assert job['format'] == 'wav' and job['speed'] == 1 and job['paragraph_pause'] == 0
    assert job['segment_plan'] == 'nano-packed-v1'
    assert client.post('/api/benchmark', json={**payload, 'text': 'Do not replace editor'}).status_code == 422


def test_existing_clone_default_stays_standard(studio):
    client, data, ident = studio
    (data / 'models' / 'vieneu.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={'text': 'Lời đọc.', 'voice_id': ident})
    assert response.status_code == 202
    assert response.json()['engine'] == 'vieneu'


def test_short_samples_and_partial_output_cannot_verify_an_hour():
    short = speed_report(60, 1)
    assert short['target_30x_met_on_sample'] is True
    assert short['hour_target_verified'] is False and short['estimate_only'] is True
    assert speed_report(3601, 119)['hour_target_verified'] is True
    assert speed_report(3601, 121)['hour_target_verified'] is False
    partial = speed_report(3601, 119, complete=False)
    assert partial['hour_target_verified'] is False and partial['complete_text'] is False
    assert speed_report(0, 1) is None
