import hashlib
import wave
from unittest.mock import patch

from test_app import request


def test_uploaded_defaults_are_the_users_exact_recordings():
    hashes = {
        'male': '29285370b91db8465222b2056b204110c6dded1a60c9004c7fb8747fe4978c9c',
        'female': '2c3467e7b5f0e49a3277397c00762810f657fd1bbd36f738a7e17d0f067f6222',
    }
    for gender, digest in hashes.items():
        r = request('GET', f'/static/voices/hmong-white-{gender}.mp3')
        assert r.status_code == 200
        assert hashlib.sha256(r.content).hexdigest() == digest


def test_builtin_transcript_saved_without_changing_recording(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA', str(tmp_path))
    path = '/api/voices/hmong-white-female/reference'
    for data in ({'text': '', 'start': 0, 'end': 7}, {'text': 'x', 'start': 0, 'end': 10},
                 {'text': 'x', 'start': 20, 'end': 26}, {'text': 'x', 'start': 0, 'end': 1}):
        assert request('PUT', path, json=data).status_code == 422
    r = request('PUT', path, json={'text': 'Nyob zoo', 'start': 1, 'end': 7})
    assert r.status_code == 200
    catalog = request('GET', '/api/voices').json()['voices']
    assert catalog[1]['reference_settings']['text'] == 'Nyob zoo'
    assert catalog[1]['reference_settings']['start'] == 1


def test_builtin_clone_passes_selected_segment_and_exact_text(tmp_path, monkeypatch):
    monkeypatch.setenv('HMONG_STUDIO_DATA', str(tmp_path))
    request('PUT', '/api/voices/hmong-white-male/reference', json={'text': 'Exact reference', 'start': 2, 'end': 8})
    def synth(text, speed, sample, reference_text):
        assert text == 'New words'
        assert speed == 1.2
        assert reference_text == 'Exact reference'
        with wave.open(str(sample), 'rb') as audio:
            assert audio.getnchannels() == 1
            assert audio.getframerate() == 24000
            assert abs(audio.getnframes() / audio.getframerate() - 6) < .01
        return b'test-contract-not-inference'
    with patch('app.cloning_engine.synthesize', side_effect=synth):
        r = request('POST', '/api/speech', json={'text': 'New words', 'dialect': 'mww', 'voice': 'hmong-white-male', 'speed': 1.2})
    assert r.status_code == 200


def test_local_default_ignores_legacy_remote_configuration(monkeypatch):
    monkeypatch.delenv('HMONG_ENGINE', raising=False)
    monkeypatch.setenv('HMONG_TTS_URL', 'https://should-not-call.example/speech')
    monkeypatch.setenv('HMONG_ASR_URL', 'https://should-not-call.example/asr')
    with patch('app.local_engine.synthesize', return_value=b'local') as synth:
        r = request('POST', '/api/speech', json={'text': 'Hi', 'dialect': 'en'})
        assert r.content == b'local'
        synth.assert_called_once()
    status = request('GET', '/api/status').json()
    assert status['engine'] == 'local'
    assert not status['remote_tts'] and not status['remote_asr']
