"""New audio processing never consumes legacy voice/chapter checkpoints."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app
import character_cast
import hmong_assets
import longform
from narration import Segment


def saved_job():
    voice = {'engine': 'hmong_native', 'voice_id': 'hmong-female-3',
             'speaker': 'hmong-female-3', 'hmong_reference_fingerprint': 'a' * 64}
    return {**voice, 'language': 'mww', 'text': 'Nyob zoo.', 'input_format': 'txt',
            'format': 'wav', 'character_cast': {'default_voice': voice,
            'voices': {'girl': voice}, 'cues': ['girl']}}


@pytest.mark.parametrize('profile', [None, 'legacy-v1', 'clear-v1'])
def test_cast_resume_keeps_legacy_identity_and_separates_clear_audio(profile):
    job = saved_job()
    if profile is not None:
        job['hmong_audio_profile'] = profile
    identity = character_cast.checkpoint_identity(job, Segment(text='Nyob zoo.', cue=0))
    legacy = '9ab372f9a1c1d820b8a6fd419d6f46ffb319ee111f9c981482fae2ffa1a7b5f8'
    assert (identity == legacy) is (profile != 'clear-v1')
    assert character_cast.settings_for_cue(job, 0).get('hmong_audio_profile') == profile


@pytest.mark.parametrize('profile', [None, 'legacy-v1', 'clear-v1'])
def test_book_resume_keeps_legacy_identity_and_separates_clear_audio(profile):
    job = saved_job()
    job.pop('character_cast')
    if profile is not None:
        job['hmong_audio_profile'] = profile
    identity = longform.plan_identity(job, longform.plan_chapters(job))
    legacy = 'cfa3d9ba38046663accaf0a26b90ca80ad33d189056ee87c0decd8423b1b5627'
    assert (identity == legacy) is (profile != 'clear-v1')


@pytest.mark.parametrize('profile', [None, 'legacy-v1', 'clear-v1'])
def test_actual_book_worker_receives_frozen_parent_audio_profile(tmp_path, profile):
    from test_longform_chapters import Worker
    job = saved_job()
    job.pop('character_cast')
    job['id'] = 'a' * 32
    if profile is not None:
        job['hmong_audio_profile'] = profile
    worker = Worker(tmp_path)
    longform.run_longform(job, tmp_path, worker, {})
    assert worker.calls and all(child.get('hmong_audio_profile') == profile for child in worker.calls)


@pytest.mark.parametrize('backend,profile', [('native', 'clear-v1'), ('f5', None)])
def test_api_assigns_profile_to_new_native_jobs_only(tmp_path, monkeypatch, backend, profile):
    monkeypatch.setenv('HMOOB_BACKEND', backend)
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
        response = client.post('/api/speech', json={'text': 'Nyob zoo.',
            'voice_id': 'hmong-male', 'language': 'mww',
            # Clients cannot downgrade newly generated speech to an old path.
            'hmong_audio_profile': 'legacy-v1'})
        assert response.status_code == 202, response.text
        job = response.json()
        assert job.get('hmong_audio_profile') == profile
        persisted = app.read_json(tmp_path / 'jobs' / (job['id'] + '.json'))
        assert persisted.get('hmong_audio_profile') == profile
        assert client.get('/api/config').json()['hmong_audio_profile'] == profile
