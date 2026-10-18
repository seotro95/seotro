import importlib
import json
import wave
from unittest.mock import patch

import pytest
from subtitles import normalize_script, parse_srt
from test_app import studio  # noqa: F401


@pytest.mark.parametrize('text', [
    '00:01 --> 00:03 Xin chào.\n00:04 --> 00:06 Cảm ơn.',
    '1\r00:00:01,000 --> 00:00:03,000\rXin chào.\r2\r00:00:04,000 --> 00:00:06,000\rCảm ơn.',
    '[00:01] Xin chào.\n[00:03]\n\n',
])
def test_minute_ranges_and_cr_only_srt(text):
    normalized, kind = normalize_script(text)
    assert kind == 'srt'
    cues = parse_srt(normalized)
    assert cues[0] == {'start': 1, 'end': 3, 'text': 'Xin chào.'}


def test_start_only_txt_requires_explicit_final_end():
    with pytest.raises(ValueError, match='kết thúc cuối'):
        normalize_script('[00:01] Xin chào.\n[00:04] Cảm ơn.')
    assert normalize_script('Giá 200.000 đồng, hẹn lúc 12:30.')[1] == 'txt'
    with pytest.raises(ValueError):
        normalize_script('00:01 --> 00:03 Xin chào.\n00:02 --> 00:04 Lệch.')


@pytest.mark.parametrize('encoding', ['utf-8-sig', 'utf-16'])
def test_file_import_and_queued_speech_preserve_timeline(studio, encoding):
    import app
    client, root = studio
    original = '[00:01] Xin chào.\n[00:04] Cảm ơn.\n[00:06]'
    response = client.post('/api/scripts/import', files={'file': ('lời.TXT', original.encode(encoding), 'text/plain')})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['input_format'] == 'srt'
    assert [(c['start'], c['end']) for c in result['cues']] == [(1, 4), (4, 6)]
    (root/'models/vieneu_nano.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={'text': original, 'input_format': 'txt', 'voice_id': 'nano-minhquan'})
    assert response.status_code == 202, response.text
    assert response.json()['input_format'] == 'srt'
    assert parse_srt(response.json()['text']) == result['cues']


@pytest.mark.parametrize('extension', ['srt', 'txt'])
@pytest.mark.parametrize('encoding', ['utf-8-sig', 'utf-16'])
def test_exact_millisecond_range_import_and_queue(studio, extension, encoding):
    import app
    client, root = studio
    original = '1\r\n00:00:00,200 --> 00:00:02,700\r\nXin chào.\r\n'
    response = client.post('/api/scripts/import', files={
        'file': (f'lời.{extension.upper()}', original.encode(encoding), 'text/plain'),
    })
    assert response.status_code == 200, response.text
    result = response.json()
    expected = [{'start': .2, 'end': 2.7, 'text': 'Xin chào.'}]
    assert result['input_format'] == 'srt'
    assert result['cues'] == expected
    (root/'models/vieneu_nano.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={
            'text': result['text'], 'input_format': result['input_format'],
            'voice_id': 'nano-minhquan', 'format': 'wav',
        })
    assert response.status_code == 202, response.text
    job = response.json()
    assert job['input_format'] == 'srt'
    assert parse_srt(job['text']) == expected
    assert [(part.cue, part.text) for part in app.plan_segments(job)] == [(0, 'Xin chào.')]


def test_exact_millisecond_range_wav_and_export(studio, monkeypatch):
    import app
    import numpy as np
    client, root = studio
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(root))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', root)
    original = '1\n00:00:00,200 --> 00:00:02,700\nXin chào.\n'
    (root/'models/vieneu_nano.ready').touch()
    with patch.object(app.executor, 'submit'):
        response = client.post('/api/speech', json={
            'text': original, 'input_format': 'srt',
            'voice_id': 'nano-minhquan', 'format': 'wav',
        })
    assert response.status_code == 202, response.text
    job = response.json()
    spoken = []
    def synth(text, path):
        spoken.append(text)
        with wave.open(str(path), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b'\x00\x20' * 24000)
    worker.render(job, synth)
    assert spoken == ['Xin chào.']
    with wave.open(str(root/'audio'/f'{job["id"]}.wav')) as output:
        assert output.getnframes() == 64800  # Exactly 2.700 seconds at 24 kHz.
        samples = np.frombuffer(output.readframes(output.getnframes()), dtype=np.int16)
    assert not np.any(samples[:4800])  # The cue starts at exactly 0.200 seconds.
    assert np.all(samples[4800:28800])
    assert not np.any(samples[28800:])
    assert parse_srt((root/'audio'/f'{job["id"]}.srt').read_text()) == parse_srt(original)
    report = json.loads((root/'parts'/job['id']/'alignment.json').read_text())
    assert report['sync_ok']
    assert report['cues'][0]['spoken_start'] == .2
    assert report['cues'][0]['spoken_end'] == 1.2
    response = client.get(f'/api/jobs/{job["id"]}/script.srt')
    assert response.status_code == 200
    assert '00:00:00,200 --> 00:00:02,700' in response.text


def test_invalid_import_keeps_errors_actionable(studio):
    client, _ = studio
    for name, data in [('bad.srt', b'not srt'), ('file.pdf', b'no'), ('bad.txt', b'\xff\x80'), ('empty.txt', b'')]:
        response = client.post('/api/scripts/import', files={'file': (name, data)})
        assert response.status_code == 422
        assert response.json()['detail']
    response = client.post('/api/scripts/import', files={'file': ('large.txt', b'x' * (2 * 1024 * 1024 + 1))})
    assert response.status_code == 422


def test_imported_txt_produces_exact_wav_length_and_silence(tmp_path, monkeypatch):
    import numpy as np
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path/'audio').mkdir()
    text, kind = normalize_script('[00:01] Xin chào.\n[00:04] Cảm ơn.\n[00:06]')
    def synth(text, path):
        with wave.open(str(path), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b'\x00\x20' * 12000)
    worker.render({'id': 'imported', 'text': text, 'input_format': kind, 'engine': 'vieneu_nano', 'format': 'wav', 'speed': 1, 'cue_fit': 'strict'}, synth)
    with wave.open(str(tmp_path/'audio/imported.wav')) as output:
        assert output.getnframes() == 6 * output.getframerate()
        samples = np.frombuffer(output.readframes(output.getnframes()), dtype=np.int16)
    assert not np.any(samples[:24000])
    assert np.any(samples[24000:36000])
    assert not np.any(samples[36000:96000])
    assert np.any(samples[96000:108000])
    assert not np.any(samples[108000:])
    assert parse_srt((tmp_path/'audio/imported.srt').read_text()) == parse_srt(text)
