"""Uploads, timestamp preservation and exact-timeline queue contracts."""
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app
from subtitles import parse_srt


@pytest.fixture
def studio(tmp_path, monkeypatch):
    for name in ('voices', 'audio', 'jobs', 'models', 'parts'):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(app, 'DATA', tmp_path)
    monkeypatch.setattr(app, 'installed_voices', lambda: [])
    (tmp_path / 'models/vieneu_nano.ready').touch()
    with TestClient(app.app) as client:
        with patch.object(app.executor, 'submit') as submit:
            yield client, tmp_path, submit


SRT = '1\n00:00:01,125 --> 00:00:04,875\nXin chào.\n\n2\n00:00:06,000 --> 00:00:08,250\nCảm ơn bạn.\n'


@pytest.mark.parametrize('filename,encoding,text', [
    ('KICH_BAN.SRT', 'utf-16', SRT),
    ('loi-thoai.txt', 'utf-8-sig', '[00:01.125 - 00:04.875] Xin chào.\n[00:06 - 00:08.250] Cảm ơn bạn.'),
    ('notepad.txt', 'utf-16-be', 'Văn bản tiếng Việt không có timeline.'),
])
def test_real_upload_decodes_notepad_files_and_keeps_cues(studio, filename, encoding, text):
    client, _, submit = studio
    response = client.post('/api/scripts/import', files={'file': (filename, text.encode(encoding), 'text/plain')})
    assert response.status_code == 200, response.text
    result = response.json()
    assert '\ufffd' not in result['text'] and 'encoding' in result
    if 'Xin chào' in text:
        assert result['has_timeline'] and result['input_format'] == 'srt'
        cues = parse_srt(result['text'])
        assert [(c['start'], c['end']) for c in cues] == [(1.125, 4.875), (6, 8.25)]
    else:
        assert result['text'] == text and not result['has_timeline']
    submit.assert_not_called()


def test_start_only_txt_waits_for_video_end_then_queues_exact(studio):
    client, _, _ = studio
    text = '[00:01] Xin chào.\n[00:05] Cảm ơn bạn.'
    pending = client.post('/api/scripts/import', files={'file': ('script.txt', text.encode(), 'text/plain')}).json()
    assert pending['requires_total_duration'] and pending['cues'][-1]['end'] is None
    denied = client.post('/api/speech', json={'text': text, 'voice_id': 'nano-minhquan'})
    assert denied.status_code == 422 and 'câu cuối' in denied.json()['detail']
    response = client.post('/api/speech', json={'text': text, 'voice_id': 'nano-minhquan', 'timeline_seconds': 9})
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['timing_mode'] == 'exact' and job['input_format'] == 'srt'
    assert job['timeline_seconds'] == 9
    assert [(c['start'], c['end']) for c in parse_srt(job['text'])] == [(1, 5), (5, 9)]


def test_srt_defaults_to_its_last_end_not_three_hours_and_keeps_video_tail(studio):
    client, _, _ = studio
    payload = {'text': SRT, 'voice_id': 'nano-minhquan', 'input_format': 'srt'}
    response = client.post('/api/speech', json=payload)
    assert response.status_code == 202, response.text
    assert response.json()['timeline_seconds'] == 8.25
    assert response.json()['timing_mode'] == 'exact'
    extended = client.post('/api/speech', json={**payload, 'timeline_seconds': 12})
    assert extended.status_code == 202 and extended.json()['timeline_seconds'] == 12
    assert parse_srt(extended.json()['text']) == parse_srt(SRT)


def test_too_short_video_or_output_limit_never_queues_truncated_speech(studio):
    client, _, submit = studio
    payload = {'text': SRT, 'voice_id': 'nano-minhquan', 'input_format': 'srt'}
    assert client.post('/api/speech', json={**payload, 'timeline_seconds': 7}).status_code == 422
    assert client.post('/api/speech', json={**payload, 'timeline_seconds': 61, 'max_minutes': 1}).status_code == 422
    submit.assert_not_called()


def test_plain_text_can_use_an_explicit_video_duration_or_opt_out_of_timing(studio):
    client, _, _ = studio
    payload = {'text': 'Xin chào, đây là lời thoại.', 'voice_id': 'nano-minhquan', 'timing_mode': 'exact'}
    assert client.post('/api/speech', json=payload).status_code == 422
    result = client.post('/api/speech', json={**payload, 'timeline_seconds': 8}).json()
    assert parse_srt(result['text']) == [{'start': 0, 'end': 8, 'text': payload['text']}]
    natural = client.post('/api/speech', json={'text': SRT, 'input_format': 'srt', 'voice_id': 'nano-minhquan', 'timing_mode': 'natural'}).json()
    assert natural['input_format'] == 'txt' and '-->' not in natural['text']
    assert natural['text'] == 'Xin chào.\n\nCảm ơn bạn.'


def test_quality_presets_change_real_nano_steps_without_changing_identity(studio):
    client, _, _ = studio
    for quality, steps in [('balanced', 8), ('expressive', 16), ('fast', 4)]:
        response = client.post('/api/speech', json={'text': 'Lời kể [thở dài] vẫn giữ nguyên.', 'voice_id': 'nano-minhquan', 'narration_quality': quality})
        assert response.status_code == 202, response.text
        job = response.json()
        assert job['voice_id'] == 'nano-minhquan' and job['nano_steps'] == steps
        assert job['text'] == 'Lời kể [thở dài] vẫn giữ nguyên.'


def test_completed_timed_txt_and_srt_keep_the_same_timeline(studio):
    client, data, _ = studio
    ident = uuid.uuid4().hex
    app.write_json(data / 'jobs' / f'{ident}.json', {'id': ident, 'status': 'done', 'format': 'wav', 'timing_mode': 'exact', 'input_format': 'srt', 'text': SRT})
    (data / 'audio' / f'{ident}.srt').write_text(SRT, encoding='utf-8')
    txt = client.get(f'/api/jobs/{ident}/export.txt')
    srt = client.get(f'/api/jobs/{ident}/export.srt')
    assert txt.status_code == srt.status_code == 200
    imported = client.post('/api/scripts/import', files={'file': ('export.txt', txt.content, 'text/plain')})
    assert imported.status_code == 200, imported.text
    assert parse_srt(imported.json()['text']) == parse_srt(srt.text)
    converted = client.post('/api/scripts/convert', json={'text': SRT, 'input_format': 'srt', 'output_format': 'txt', 'preserve_timing': True})
    assert converted.status_code == 200 and '[00:00:01,125 --> 00:00:04,875]' in converted.json()['text']


def test_timed_txt_roundtrip_preserves_literal_formatting_symbols(studio):
    client, _, _ = studio
    original = '1\n00:00:01,000 --> 00:00:03,000\nĐọc &lt;b&gt;từ này&lt;/b&gt; &amp; tên &lt;An&gt;.\n'
    converted = client.post('/api/scripts/convert', json={'text': original, 'input_format': 'srt', 'output_format': 'txt', 'preserve_timing': True})
    assert converted.status_code == 200
    imported = client.post('/api/scripts/import', files={'file': ('symbols.txt', converted.json()['text'].encode(), 'text/plain')})
    assert imported.status_code == 200, imported.text
    assert parse_srt(imported.json()['text']) == parse_srt(original)


@pytest.mark.parametrize('filename,data,expected', [('bad.zip', b'hello', 422), ('empty.txt', b'', 422), ('big.txt', b'a' * (2*1024*1024+1), 413)])
def test_bad_upload_does_not_overwrite_or_queue(studio, filename, data, expected):
    client, root, submit = studio
    result = client.post('/api/scripts/import', files={'file': (filename, data, 'text/plain')})
    assert result.status_code == expected
    submit.assert_not_called()
    assert not list((root / 'jobs').iterdir())
