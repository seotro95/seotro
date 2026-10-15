import importlib
import json
import wave
from unittest.mock import patch

import pytest

from subtitles import parse_srt, export_srt
from test_app import studio  # noqa: F401

SRT = '1\n00:00:01,000 --> 00:00:02,000\nXin chào.\n\n2\n00:00:03,000 --> 00:00:04,000\n<b>Cảm ơn.</b>\n'


def test_srt_validation_and_roundtrip():
    cues = parse_srt('\ufeff'+SRT.replace('\n', '\r\n'))
    assert cues[1]['text'] == 'Cảm ơn.'
    assert parse_srt(export_srt(cues)) == cues
    for text in ('bad', SRT.replace('00:00:03,000', '00:00:01,500'), SRT.replace('00:00:02,000', '00:00:00,000'), SRT.replace('00:00:04,000', '04:00:00,000')):
        with pytest.raises(ValueError):
            parse_srt(text)


def test_srt_audio_timing_txt_exports_and_overflow(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    def synth(text, output):
        with wave.open(str(output), 'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
            f.writeframes(b'\x00\x20'*12000)  # half second per phrase
    job = {'id': 'srt', 'text': SRT, 'engine': 'vieneu', 'input_format': 'srt', 'format': 'wav', 'speed': 1, 'paragraph_pause': 3}
    worker.render(job, synth)
    with wave.open(str(tmp_path/'audio/srt.wav')) as f:
        data = f.readframes(f.getnframes())
        assert f.getnframes() == 4*24000
    assert not any(data[:24000*2])  # silence before first cue
    assert any(data[24000*2:36000*2])
    assert not any(data[36000*2:72000*2])
    assert any(data[72000*2:84000*2])
    assert parse_srt((tmp_path/'audio/srt.srt').read_text()) == parse_srt(SRT)
    worker.render({**job, 'id': 'txt', 'input_format': 'txt', 'text': 'Xin chào. Cảm ơn.', 'paragraph_pause': .2}, synth)
    actual = parse_srt((tmp_path/'audio/txt.srt').read_text())
    assert actual[0]['end'] == .5 and actual[1]['start'] == .7
    with pytest.raises(ValueError, match='Câu SRT 1 đọc quá dài'):
        worker.render({**job, 'id': 'overflow', 'text': SRT.replace('00:00:02,000', '00:00:01,100')}, synth)


def test_subtitle_api_and_system_voice_needs_no_model(studio):
    import app
    client, root = studio
    assert client.post('/api/scripts/convert', json={'text': SRT, 'input_format': 'srt', 'output_format': 'txt'}).json()['text'] == 'Xin chào.\nCảm ơn.'
    assert client.post('/api/scripts/convert', json={'text': 'Xin chào', 'input_format': 'txt', 'output_format': 'srt'}).status_code == 422
    voice = {'id': 'sys-test', 'name': 'Test Windows', 'engine': 'system', 'speaker': 'Test', 'languages': ['vi']}
    with patch('app.installed_voices', return_value=[voice]), patch('app.executor.submit'):
        assert any(v['engine']=='system' for v in client.get('/api/voices').json()['voices'])
        job = client.post('/api/speech', json={'text': SRT, 'input_format': 'srt', 'voice_id': 'sys-test'}).json()
        assert job['engine']=='system' and job['total']==2
    ident = job['id']
    assert client.get(f'/api/jobs/{ident}/script.txt').text == 'Xin chào.\nCảm ơn.'
    assert parse_srt(client.get(f'/api/jobs/{ident}/script.srt').text) == parse_srt(SRT)
    with patch('app.installed_voices', return_value=[voice]), patch('app.executor.submit'):
        bad = client.post('/api/speech', json={'text': 'bad', 'input_format': 'srt', 'voice_id': 'sys-test'})
        assert bad.status_code == 422
    # Windows SAPI invocation never places the user's text into executable command text.
    import system_voices
    command = system_voices.command('speak')
    assert '-ExecutionPolicy' not in command
    assert 'SelectVoice' in command[-1] and '$env:VOICE_STUDIO_SPEECH_REQUEST' in command[-1]


def test_srt_fits_short_cue_without_shifting_next_cue(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path/'audio').mkdir()
    def synth(text, output):
        import numpy as np
        import soundfile as sf
        sf.write(output, .3*np.sin(np.arange(12000)*2*np.pi*440/24000), 24000)
    worker.render({'id': 'fit', 'text': SRT.replace('00:00:02,000', '00:00:01,400'), 'engine': 'vieneu', 'input_format': 'srt', 'format': 'wav', 'speed': 1}, synth)
    with wave.open(str(tmp_path/'audio/fit.wav')) as f:
        assert f.getnframes() == 96000


def test_sapi_json_request_keeps_user_text_out_of_command(tmp_path, monkeypatch):
    import system_voices
    # Preserve pathlib's native platform and mock only the provider's platform check.
    from types import SimpleNamespace
    monkeypatch.setattr(system_voices, 'os', SimpleNamespace(name='nt', environ={}))
    text = 'Tiếng Việt; $(không thực thi) " lời mẫu'
    output = tmp_path / 'voice.wav'
    def run(command, **kwargs):
        payload = json.loads(open(kwargs['env']['VOICE_STUDIO_SPEECH_REQUEST'], encoding='utf-8').read())
        assert payload['text'] == text and payload['voice'] == 'Test voice'
        assert text not in command[-1]
    with patch('system_voices.subprocess.run', side_effect=run):
        system_voices.speak(text, 'Test voice', output)
    assert not list(tmp_path.glob('*.json'))
