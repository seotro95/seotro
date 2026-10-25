"""Rejected speech requests explain the next edit without leaking request data."""
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

import app
import hmong_assets


@pytest.fixture
def studio(tmp_path, monkeypatch):
    for folder in ('voices', 'audio', 'jobs', 'models', 'parts', 'videos'):
        (tmp_path / folder).mkdir()
    monkeypatch.setenv('HMOOB_BACKEND', 'native')
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'IS_HMONG', True)
    monkeypatch.setattr(app, 'LANGUAGES', {**app.LANGUAGES, 'mww': 'Hmong Trắng'})
    monkeypatch.setattr(app, 'PRESETS', hmong_assets.presets())
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    monkeypatch.setattr(app, 'model_ready', lambda engine: True)
    with TestClient(app.app) as client:
        submit = Mock()
        monkeypatch.setattr(app.executor, 'submit', submit)
        yield client, tmp_path, submit


def speech(**changes):
    return {'text': 'Nyob zoo.', 'voice_id': 'hmong-male', 'language': 'mww', **changes}


def assert_rejected(studio, payload):
    client, data, submit = studio
    response = client.post('/api/speech', json=payload)
    assert response.status_code == 422, response.text
    submit.assert_not_called()
    assert list((data / 'jobs').glob('*.json')) == []
    return response


def test_required_speech_fields_have_actionable_safe_feedback(studio):
    response = assert_rejected(studio, {})
    result = response.json()
    assert result['code'] == 'invalid_speech_fields'
    assert result['field'] == 'text'
    assert {item['field']: item['code'] for item in result['errors']} == {
        'text': 'missing', 'voice_id': 'missing'}
    assert 'Nhập nội dung' in result['detail'] and 'Chọn giọng' in result['detail']


@pytest.mark.parametrize('field,value,hint', [
    ('speed', .5, '0,7 đến 1,4'),
    ('max_minutes', 181, '1 đến 180'),
    ('paragraph_pause', -1, '0 đến 3'),
    ('emotion_strength', 2, '0 đến 1'),
    ('input_format', 'csv', 'TXT hoặc SRT'),
    ('text', '', 'Nhập nội dung'),
    ('voice_id', '', 'Chọn giọng'),
])
def test_speech_control_errors_identify_the_control_and_limits(studio, field, value, hint):
    result = assert_rejected(studio, speech(**{field: value})).json()
    assert result['field'] == field
    assert hint in result['detail']
    assert result['errors'][0]['field'] == field


def test_speech_validation_never_returns_values_or_nested_user_keys(studio):
    secret = 'private-request-token-do-not-return'
    payload = speech(text={'api_key': secret}, speed=secret,
                     character_voices={secret: [secret]})
    response = assert_rejected(studio, payload)
    assert secret not in response.text and 'api_key' not in response.text
    assert 'input' not in response.json()['errors'][0]
    assert {item['field'] for item in response.json()['errors']} == {
        'text', 'speed', 'character_voices'}
    assert all(set(item) == {'field', 'code', 'message'} for item in response.json()['errors'])


def test_non_speech_key_validation_retains_generic_private_response(studio):
    client, _, _ = studio
    secret = 'private-key-value-do-not-return'
    response = client.post('/api/writing/connect', json={
        'provider': 'openai', 'api_key': {'private-field': secret}})
    assert response.status_code == 422
    assert set(response.json()) == {'detail'}
    assert secret not in response.text and 'private-field' not in response.text


@pytest.mark.parametrize('text,characters,hint', [
    ('Kuv muaj 2 tug me nyuam.', ['2'], 'Viết các số bằng chữ Hmong'),
    ('Mus saib https://example.com.', ['/'], 'đường dẫn hoặc địa chỉ'),
    ('Nyob zoo 😀.', ['😀'], 'RPA'),
])
def test_unsupported_spoken_text_reports_characters_without_creating_job(studio, text, characters, hint):
    result = assert_rejected(studio, speech(text=text)).json()
    assert result['code'] == 'unsupported_speech_characters'
    assert result['field'] == 'text'
    assert result['unsupported_characters'] == characters
    assert hint in result['detail']


def test_srt_error_keeps_cue_location_and_excludes_timestamps_from_characters(studio):
    text = '1\n00:00:00,000 --> 00:00:10,000\nKuv muaj 2 tug me nyuam.\n'
    result = assert_rejected(studio, speech(text=text, input_format='srt')).json()
    assert 'Câu SRT 1' in result['detail']
    assert result['unsupported_characters'] == ['2']


def test_unsupported_character_metadata_is_deduplicated_and_bounded(studio):
    text = 'Nyob zoo ' + ''.join(chr(0x4e00 + index) for index in range(30)) * 5
    result = assert_rejected(studio, speech(text=text)).json()
    assert len(result['unsupported_characters']) == 16
    assert len(set(result['unsupported_characters'])) == 16
    assert text not in result['detail']


def test_reference_validation_points_to_voice_selection(studio, monkeypatch):
    path, _ = hmong_assets.reference('hmong-male')
    monkeypatch.setattr(hmong_assets, 'reference', lambda speaker: (path, 'Kuv muaj 2.'))
    result = assert_rejected(studio, speech()).json()
    assert result['field'] == 'voice_id'
    assert 'Lời mẫu tham chiếu' in result['detail']
    assert result['unsupported_characters'] == ['2']


@pytest.mark.parametrize('text', [
    'Nyob-zoo, kuv yog ib tug Hmoob.',
    "Kuv hais tias 'Nyob zoo'.",
    'Kuv hais tias ’Nyob zoo’.',
    'Kuv muaj ob tug me nyuam.',
    '[pause=0.5] [emotion=warm]Nyob zoo. **Ua tsaug.**',
])
def test_supported_words_apostrophes_and_controls_still_queue_exact_source(studio, text):
    client, data, submit = studio
    response = client.post('/api/speech', json=speech(text=text))
    assert response.status_code == 202, response.text
    result = response.json()
    assert result['text'] == text
    assert app.read_json(data / 'jobs' / (result['id'] + '.json'))['text'] == text
    submit.assert_called_once_with(app.run_job, result['id'])
