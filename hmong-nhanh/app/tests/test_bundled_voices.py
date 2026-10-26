"""Bundled uploads are editable references, never fabricated ready-made clones."""
import hashlib
import wave
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app
import builtin_references


ADDED = {
    'builtin-hmong-female-3': ('Hmong nữ 3', 'aec83955c0c81abe7355167c779c7ca4c6c4b51422b4ba1018b7ff8f6b30fb1b'),
    'builtin-hmong-female-1': ('Hmong nữ', '2c3467e7b5f0e49a3277397c00762810f657fd1bbd36f738a7e17d0f067f6222'),
    'builtin-ngoc-huyen': ('Ngọc Huyền', '0f0902ae57716c6933d2cc9385714a68d318080bed4addcf7f4ac1804545070f'),
    'builtin-hmong-male-2': ('Hmong nam 2', 'bc9104c2ebe00471abc46283c52627b2cadc615d96f15f1dc9d576b1316d78c8'),
    'builtin-hmong-male-1': ('Hmong nam 1', '29285370b91db8465222b2056b204110c6dded1a60c9004c7fb8747fe4978c9c'),
    'builtin-hmong-female-2': ('Hmong nữ 2 (1)', '874f510e723f48fcd093d55a5ba4613fc80107a863261658ec9d3961ef493d84'),
}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA_DIR', str(tmp_path))
    monkeypatch.setattr(app.cloning_engine, 'availability', lambda: {
        'ready': True, 'configured': True, 'dependencies': True, 'reason': ''})
    return tmp_path


def test_six_original_uploads_available_without_fabricated_transcripts(isolated):
    with TestClient(app.app) as client:
        voices = {voice['id']: voice for voice in client.get('/api/voices').json()['voices']}
        assert len(voices) == 8
        assert voices['hmong-white-female']['name'] == 'Nữ'
        assert voices['hmong-white-male']['name'] == 'Nam'
        for ident, (name, digest) in ADDED.items():
            voice = voices[ident]
            assert voice['name'] == name
            assert voice['source_type'] == 'bundled'
            assert voice['source_filename'].endswith('.MP3')
            assert not voice['reference_ready'] and not voice['generation_configured']
            assert voice['reference_settings']['text'] == ''
            audio = client.get(voice['reference'])
            assert audio.status_code == 200
            assert hashlib.sha256(audio.content).hexdigest() == digest
            assert 3 <= voice['reference_settings']['duration'] < 30
            with patch('app.voice_jobs.create') as create:
                response = client.post('/api/speech/jobs', json={'voice': ident, 'text': 'Nyob zoo.'})
                assert response.status_code == 422
                create.assert_not_called()


@pytest.mark.parametrize('ident', ADDED)
def test_saved_bundled_reference_survives_restart_and_routes_exact_pair(isolated, ident):
    # This is a synthetic fixture transcript for routing assertions, not ASR or
    # a claimed transcription of any user's audio.
    transcript = 'Fixture words for ' + ident
    with TestClient(app.app) as client:
        response = client.put('/api/voices/' + ident + '/reference',
                              json={'start': 0, 'end': 4, 'text': transcript})
        assert response.status_code == 200, response.text
        voice = response.json()['voice']
        assert voice['reference_ready'] and voice['generation_configured']
        selected, saved = builtin_references.selected(ident)
        assert saved == transcript
        with wave.open(str(selected)) as audio:
            assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()) == (1, 2, 24000, 96000)

    with TestClient(app.app) as restarted:
        catalog = {voice['id']: voice for voice in restarted.get('/api/voices').json()['voices']}
        assert catalog[ident]['reference_settings']['text'] == transcript
        assert catalog[ident]['reference_ready']
        assert not catalog['hmong-white-female']['reference_ready']
        assert not catalog['hmong-white-male']['reference_ready']
        with patch('app.voice_jobs.create', return_value={'id': 'test', 'status': 'running'}) as create:
            response = restarted.post('/api/speech/jobs', json={'voice': ident, 'text': 'Nyob zoo.'})
            assert response.status_code == 202, response.text
            job = create.call_args.args[0]
        assert job['voice'] == ident and job['voice_name'] == ADDED[ident][0]
        assert job['_reference'] == {'path': str(selected.resolve()), 'text': transcript}


def test_added_samples_do_not_overwrite_existing_reference_settings(isolated):
    with TestClient(app.app) as client:
        for ident in ('hmong-white-female', 'hmong-white-male'):
            response = client.put('/api/voices/' + ident + '/reference',
                                  json={'start': 1, 'end': 5, 'text': 'Saved legacy ' + ident})
            assert response.status_code == 200
        old_metadata = {path.name: path.read_bytes() for path in (isolated / 'references').glob('hmong-white-*.json')}
        for ident in ADDED:
            assert client.get('/api/voices/' + ident + '/source').status_code == 200
        assert {path.name: path.read_bytes() for path in (isolated / 'references').glob('hmong-white-*.json')} == old_metadata
        for ident in ('builtin-made-up', 'builtin-hmong-female-1/../../bad'):
            result = client.post('/api/speech/jobs', json={'voice': ident, 'text': 'Nyob zoo.'})
            assert result.status_code == 422
