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


def test_auto_clone_falls_back_to_standard_when_nano_clone_is_not_prepared(studio):
    client, data, ident = studio
    (data / 'models' / 'vieneu.ready').touch()
    # A ready preset is not proof that reference cloning works on this machine.
    (data / 'models' / 'vieneu_nano.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={'text': 'Lời đọc.', 'voice_id': ident})
    assert response.status_code == 202
    assert response.json()['engine'] == 'vieneu'


def test_auto_clone_defaults_to_prepared_nano_without_changing_reference_or_playback(studio):
    client, data, ident = studio
    (data / 'models' / 'vieneu_nano_clone.ready').touch()
    text = 'Tạo giọng từ đúng bản thu của tôi, ở tốc độ đọc tự nhiên.'
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={'text': text, 'voice_id': ident})
    assert response.status_code == 202, response.text
    job = response.json()
    assert (job['engine'], job['voice_id'], job['speaker']) == ('vieneu_nano', ident, None)
    assert job['nano_steps'] == 4
    assert job['nano_requested_parallel'] == job['nano_requested_threads'] == 0
    assert job['speed'] == 1 and job['text'] == text
    assert job['paragraph_pause'] == 0 and job['segment_plan'] == 'nano-packed-v1'
    config = client.get('/api/config').json()
    assert config['default_clone_engine'] == 'auto' and config['default_nano_steps'] == 4
    entry = next(v for v in client.get('/api/voices').json()['voices'] if v['id'] == ident)
    assert entry['default_engine'] == job['engine']


def test_explicit_clone_quality_and_pause_choices_are_retained(studio):
    client, data, ident = studio
    for model in ('vieneu', 'vieneu_nano_clone'):
        (data / 'models' / f'{model}.ready').touch()
    payload = {'text': 'Lời kể tự nhiên.', 'voice_id': ident, 'clone_engine': 'standard',
               'nano_steps': 16, 'paragraph_pause': .6}
    with patch.object(app.executor, 'submit'):
        standard = client.post('/api/speech', json=payload)
        nano = client.post('/api/speech', json={**payload, 'clone_engine': 'nano'})
    assert standard.status_code == nano.status_code == 202
    assert standard.json()['engine'] == 'vieneu'
    assert nano.json()['engine'] == 'vieneu_nano' and nano.json()['nano_steps'] == 16
    assert nano.json()['paragraph_pause'] == .6 and nano.json()['segment_plan'] == 'classic-v1'


def test_auto_fast_clone_is_limited_to_vietnamese_and_does_not_replace_presets(studio):
    client, data, ident = studio
    for model in ('vieneu', 'vieneu_nano_clone', 'qwen_clone'):
        (data / 'models' / f'{model}.ready').touch()
    other = 'b' * 32
    app.write_json(data / 'voices' / f'{other}.json', {
        'id': other, 'name': 'English reference', 'languages': ['en-US'], 'category': 'cloned',
    })
    with patch.object(app.executor, 'submit'):
        english = client.post('/api/speech', json={'text': 'Hello.', 'voice_id': other, 'language': 'en-US'})
        preset = client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': 'vi-maianh'})
    assert english.status_code == preset.status_code == 202
    assert (english.json()['engine'], english.json()['voice_id']) == ('qwen_clone', other)
    assert (preset.json()['engine'], preset.json()['voice_id']) == ('vieneu', 'vi-maianh')


def test_short_samples_and_partial_output_cannot_verify_an_hour():
    short = speed_report(60, 1)
    assert short['target_30x_met_on_sample'] is True
    assert short['hour_target_verified'] is False and short['estimate_only'] is True
    assert speed_report(3601, 119)['hour_target_verified'] is True
    assert speed_report(3601, 121)['hour_target_verified'] is False
    partial = speed_report(3601, 119, complete=False)
    assert partial['hour_target_verified'] is False and partial['complete_text'] is False
    assert speed_report(0, 1) is None
