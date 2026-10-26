"""The supplied dense SRT keeps its source, full words and actual timeline."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app
import hmong_assets
import longform
from hmong_native import validate_text
from hmong_text import normalize_speech_text, normalize_text
from narration import plan_segments
from test_user_srt_166 import SOURCE, WORDS


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    for folder in ('voices', 'jobs', 'parts', 'audio', 'models', 'videos'):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'IS_HMONG', True)
    monkeypatch.setattr(app, 'PRESETS', hmong_assets.presets())
    monkeypatch.setattr(app, 'LANGUAGES', {**app.LANGUAGES, 'mww': 'Hmong'})
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    monkeypatch.setattr(app, 'model_ready', lambda engine: True)
    with TestClient(app.app) as client:
        monkeypatch.setattr(app.executor, 'submit', Mock())
        yield client, tmp_path


@pytest.mark.parametrize('input_format', ['srt', 'txt'])
@pytest.mark.parametrize('wrapper', ['', '"'])
def test_valid_user_captions_queue_with_full_text_and_adaptive_timeline(studio, input_format, wrapper):
    client, data = studio
    source = wrapper + SOURCE + wrapper
    response = client.post('/api/speech', json={'text': source, 'language': 'mww',
        'voice_id': 'hmong-female-3', 'input_format': input_format})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['text'] == source and job['input_format'] == 'srt'
    assert job['subtitle_timing'] is True and job['cue_fit'] == 'adaptive'
    assert job['max_cue_tempo'] == 4 and job['require_complete_audio'] is True
    if input_format == 'txt':
        assert job['source_input_format'] == 'txt'
    parts = plan_segments(job)
    assert [(part.cue, part.text) for part in parts] == list(enumerate(WORDS))
    assert app.read_json(data / 'jobs' / (job['id'] + '.json')) == job


@pytest.mark.parametrize('input_format', ['srt', 'txt'])
def test_deliberate_continuous_reading_stays_available(studio, input_format):
    client, _ = studio
    response = client.post('/api/speech', json={'text': SOURCE, 'language': 'mww',
        'voice_id': 'hmong-female-3', 'input_format': input_format,
        'subtitle_timing': False})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['input_format'] == input_format and job['subtitle_timing'] is False
    parts = plan_segments(job)
    assert all(part.cue is None for part in parts)
    assert ' '.join(part.text for part in parts) == ' '.join(WORDS)


def test_explicit_strict_tempo_limit_is_not_overridden(studio):
    client, _ = studio
    response = client.post('/api/speech', json={'text': SOURCE, 'language': 'mww',
        'voice_id': 'hmong-female-3', 'input_format': 'srt',
        'cue_fit': 'strict', 'max_cue_tempo': 1.5})
    assert response.status_code == 202
    assert response.json()['cue_fit'] == 'strict'
    assert response.json()['max_cue_tempo'] == 1.5


@pytest.mark.parametrize('source,expected', [
    ('"Nyob zoo" (Ua tsaug).', 'Nyob zoo Ua tsaug.'),
    ('“Tus txiv neej” (rov los tsev).', 'Tus txiv neej rov los tsev.'),
    ('«ua thaj» (qab faib) rov ris.', 'ua thaj qab faib rov ris.'),
    ('Tus(txiv)neej', 'Tus txiv neej'),
])
def test_quotes_and_parentheses_preserve_every_word_through_model_validation(source, expected):
    assert normalize_speech_text(source) == expected
    assert validate_text(source) == expected.lower()
    reference = normalize_text(source)
    assert reference.count('(') == source.count('(')
    assert reference.count(')') == source.count(')')
    if any(mark in source for mark in ('"', '“', '«')):
        assert '"' in reference  # Reference words retain their original delimiters.


def test_new_book_identity_and_child_bind_complete_audio_policy(tmp_path):
    from test_longform_chapters import Worker
    job = {'id': 'a' * 32, 'text': 'Nyob zoo.', 'engine': 'hmong_native',
           'language': 'mww', 'input_format': 'txt', 'format': 'wav'}
    chapters = longform.plan_chapters(job)
    old = longform.plan_identity(job, chapters)
    assert old == longform.plan_identity({**job, 'require_complete_audio': False}, chapters)
    complete = {**job, 'require_complete_audio': True}
    assert old != longform.plan_identity(complete, chapters)
    worker = Worker(tmp_path)
    longform.run_longform(complete, tmp_path, worker, {})
    assert worker.calls and all(child['require_complete_audio'] is True for child in worker.calls)
