"""Country voices stay explicit and cannot borrow another model's readiness."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app
from benchmark_text import SAMPLE_TEXTS
from piper_catalog import PIPER_MODELS


@pytest.fixture
def country_studio(tmp_path, monkeypatch):
    for folder in ('voices', 'audio', 'jobs', 'models', 'parts'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    monkeypatch.setenv('VOICE_STUDIO_PORTABLE', '1')
    with TestClient(app.app) as client:
        with patch.object(app.executor, 'submit') as submit:
            yield client, tmp_path, submit


def test_portable_advertises_all_bundled_country_voices_but_only_vietnamese_cloning(country_studio, monkeypatch):
    client, _, _ = country_studio
    monkeypatch.setattr(app, 'piper_model_ready', lambda data, key: True)
    config = client.get('/api/config').json()
    voices = client.get('/api/voices').json()['voices']
    countries = [voice for voice in voices if voice['engine'] == 'piper']
    assert len(countries) == len(PIPER_MODELS) == 16
    assert len({voice['id'] for voice in countries}) == len(countries)
    assert {voice['speaker'] for voice in countries} == set(PIPER_MODELS)
    assert all(voice['ready'] for voice in countries)
    assert config['piper_voices_ready'] == len(countries)
    assert config['ai_clone_languages'] == ['vi']
    assert all(voice['languages'][0] in config['ai_voice_languages'] for voice in countries)
    assert all(voice['languages'][0] in config['languages'] for voice in countries)
    assert not any(voice['engine'] in {'qwen', 'qwen_clone'} for voice in voices)


@pytest.mark.parametrize('key', tuple(PIPER_MODELS))
def test_country_voice_and_its_benchmark_preserve_language_and_identity(country_studio, monkeypatch, key):
    client, _, submit = country_studio
    monkeypatch.setattr(app, 'piper_model_ready', lambda data, candidate: candidate == key)
    voice = next(voice for voice in app.PRESETS if voice.get('engine') == 'piper' and voice['speaker'] == key)
    language = voice['languages'][0]
    text = SAMPLE_TEXTS[language]
    response = client.post('/api/speech', json={'text': text, 'voice_id': voice['id'], 'language': language})
    assert response.status_code == 202, response.text
    job = response.json()
    assert (job['engine'], job['speaker'], job['voice_id'], job['language']) == ('piper', key, voice['id'], language)
    assert job['text'] == text and job['speed'] == 1
    measured = client.post('/api/benchmark', json={'voice_id': voice['id'], 'language': language})
    assert measured.status_code == 202, measured.text
    benchmark = measured.json()
    assert benchmark['benchmark'] is True
    assert (benchmark['engine'], benchmark['speaker'], benchmark['voice_id'], benchmark['language']) == ('piper', key, voice['id'], language)
    assert benchmark['text'] == text and benchmark['format'] == 'wav'
    assert submit.call_count == 2


@pytest.mark.parametrize('key', tuple(PIPER_MODELS))
def test_country_voice_rejects_wrong_language_before_readiness_or_queue(country_studio, monkeypatch, key):
    client, data, submit = country_studio
    voice = next(voice for voice in app.PRESETS if voice.get('engine') == 'piper' and voice['speaker'] == key)
    def unexpected_readiness(*args):
        raise AssertionError('Invalid language must be rejected before model access')
    monkeypatch.setattr(app, 'piper_model_ready', unexpected_readiness)
    response = client.post('/api/speech', json={'text': 'Xin chào.', 'voice_id': voice['id'], 'language': 'vi'})
    assert response.status_code == 422, response.text
    submit.assert_not_called()
    assert not list((data / 'jobs').iterdir())


def test_aggregate_marker_does_not_make_missing_country_model_ready(country_studio, monkeypatch):
    client, data, submit = country_studio
    # A partially copied bundle can retain this overall preparation marker.
    (data / 'models' / 'piper.ready').touch()
    countries = [voice for voice in app.PRESETS if voice.get('engine') == 'piper']
    available, missing = countries[:2]
    monkeypatch.setattr(app, 'piper_model_ready', lambda root, key: key == available['speaker'])
    config = client.get('/api/config').json()
    assert config['piper_voices_ready'] == 1
    listed = {voice['id']: voice for voice in client.get('/api/voices').json()['voices']}
    assert listed[available['id']]['ready'] is True
    assert listed[missing['id']]['ready'] is False
    response = client.post('/api/speech', json={'text': SAMPLE_TEXTS[missing['languages'][0]],
                           'voice_id': missing['id'], 'language': missing['languages'][0]})
    assert response.status_code == 503, response.text
    assert 'TAI_GIONG_QUOC_TE_NHANH.bat' in response.json()['detail']
    submit.assert_not_called()
    assert not list((data / 'jobs').iterdir())
