"""Real PCM/FFmpeg regression checks; synthesis is deterministic, without models."""
import importlib
import json
import wave
from unittest.mock import patch

import numpy as np
import pytest

from duration_sync import pcm_frames, target_frames, verify_export
from language_catalog import LANGUAGES
from narration import PCMWriter
from subtitles import parse_srt
from test_app import studio  # noqa: F401


def tone(path, seconds, frequency=440):
    count = round(seconds * 24000)
    samples = (np.sin(np.arange(count) * (2*np.pi*frequency/24000))*9000).astype('<i2')
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(samples.tobytes())


def local_worker(root, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(root))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', root)
    (root/'audio').mkdir(exist_ok=True)
    return worker


def job(ident, text='First sentence.\nLast sentence.', **changes):
    return {'id': ident, 'text': text, 'engine': 'system', 'speaker': 'test',
            'speed': 1, 'format': 'wav', 'paragraph_pause': 0, **changes}


@pytest.mark.parametrize('language', list(LANGUAGES))
def test_txt_and_strict_srt_have_identical_measured_duration(tmp_path, monkeypatch, language):
    worker = local_worker(tmp_path, monkeypatch)
    # Native scripts, including scripts without whitespace, take the same PCM path.
    word = LANGUAGES[language].split('·')[-1].strip() + ' 123'
    calls = []
    def synth(text, path):
        calls.append(text)
        tone(path, .6)
    txt = word + '\n' + word
    srt = f'1\n00:00:00,250 --> 00:00:00,950\n{word}\n\n2\n00:00:01,500 --> 00:00:02,345\n{word}\n'
    worker.render(job('txt', txt, language=language, target_seconds=2.345), synth)
    worker.render(job('srt', srt, language=language, input_format='srt'), synth)
    expected = round(2.345*24000)
    assert pcm_frames(tmp_path/'audio/txt.wav') == expected
    assert pcm_frames(tmp_path/'audio/srt.wav') == expected
    assert calls == [word]*4
    assert parse_srt((tmp_path/'audio/srt.srt').read_text(encoding='utf-8')) == parse_srt(srt)
    for ident in ('txt', 'srt'):
        result = json.loads((tmp_path/f'parts/{ident}/result.json').read_text())
        assert result['duration_verified'] and not result['duration_limited']
        assert result['duration_report']['error_frames'] == 0
    with wave.open(str(tmp_path/'audio/srt.wav')) as audio:
        samples = np.frombuffer(audio.readframes(audio.getnframes()), '<i2')
    assert not samples[:6000].any()  # leading silence
    assert samples[6000:20400].any()
    assert not samples[22800:36000].any()  # original gap between cues
    report = json.loads((tmp_path/'parts/srt/alignment.json').read_text())
    assert report['sync_ok'] and report['duration']['error_frames'] == 0


@pytest.mark.parametrize('extension', ['wav', 'mp3'])
@pytest.mark.parametrize('kind', ['txt', 'srt'])
@pytest.mark.parametrize('seconds', [2.345, 1.001])
def test_actual_export_decodes_to_exact_target(tmp_path, monkeypatch, extension, kind, seconds):
    worker = local_worker(tmp_path, monkeypatch)
    from subtitles import timestamp
    text = 'Hello.' if kind == 'txt' else f'1\n00:00:00,000 --> {timestamp(seconds)}\nHello.'
    payload = job('export', text, format=extension, input_format=kind)
    if kind == 'txt':
        payload['target_seconds'] = seconds
    worker.render(payload, lambda text, path: tone(path, .75))
    report = verify_export(tmp_path/f'audio/export.{extension}', tmp_path, seconds)
    assert report['sample_frames'] == round(seconds*24000) and report['verified']
    assert report['measurement'] == 'decoded_pcm'
    assert not list(tmp_path.glob('verify-*.wav'))


def test_compression_keeps_all_text_pitch_and_subtitle_order(tmp_path, monkeypatch):
    worker = local_worker(tmp_path, monkeypatch)
    calls = []
    def synth(text, path):
        calls.append(text)
        tone(path, 2)
    worker.render(job('fit', target_seconds=3), synth)
    assert calls == ['First sentence.', 'Last sentence.']
    output = tmp_path/'audio/fit.wav'
    assert pcm_frames(output) == 72000
    with wave.open(str(output)) as audio:
        samples = np.frombuffer(audio.readframes(audio.getnframes()), '<i2')
    middle = samples[12000:36000].astype(float)
    pitch = np.argmax(abs(np.fft.rfft(middle)))*24000/len(middle)
    assert abs(pitch-440) < 3
    cues = parse_srt((tmp_path/'audio/fit.srt').read_text())
    assert [c['text'] for c in cues] == calls
    assert cues[0]['end'] <= cues[1]['start'] and cues[-1]['end'] <= 3


def test_target_fits_raw_audio_longer_than_final_safety_limit(tmp_path, monkeypatch):
    worker = local_worker(tmp_path, monkeypatch)
    worker.render(job('long', target_seconds=60, max_minutes=1),
                  lambda text, path: tone(path, 35))
    result = json.loads((tmp_path/'parts/long/result.json').read_text())
    assert result['completed'] == 2 and not result['duration_limited']
    assert result['duration_fit']['raw_seconds'] == 70
    assert pcm_frames(tmp_path/'audio/long.wav') == 60*24000


@pytest.mark.parametrize('kind', ['txt', 'srt'])
def test_unfit_voice_reports_error_and_does_not_publish_partial_audio(tmp_path, monkeypatch, kind):
    worker = local_worker(tmp_path, monkeypatch)
    text = 'All words must remain.' if kind == 'txt' else '1\n00:00:00,000 --> 00:00:01,000\nAll words must remain.'
    payload = job('unfit', text, input_format=kind, target_seconds=1)
    with pytest.raises(ValueError, match='không cắt|đọc quá dài'):
        worker.render(payload, lambda text, path: tone(path, 2.5))
    assert not (tmp_path/'audio/unfit.wav').exists()
    assert not (tmp_path/'parts/unfit/result.json').exists()
    assert pcm_frames(tmp_path/'parts/unfit/000000.wav') == 60000


def test_export_verification_failure_never_marks_srt_synced(tmp_path, monkeypatch):
    worker = local_worker(tmp_path, monkeypatch)
    def fail(*args):
        raise ValueError('Thời lượng file không khớp.')
    monkeypatch.setattr(worker, 'verify_export', fail)
    with pytest.raises(ValueError, match='không khớp'):
        worker.render(job('bad', '1\n00:00:00,000 --> 00:00:02,000\nHello.', input_format='srt'),
                      lambda text, path: tone(path, .75))
    assert not (tmp_path/'audio/bad.wav').exists()
    assert not json.loads((tmp_path/'parts/bad/alignment.json').read_text())['sync_ok']


def test_strict_pcm_never_silently_cuts_a_word_or_pause(tmp_path):
    tone(tmp_path/'source.wav', 1.001)
    writer = PCMWriter(tmp_path/'out.wav', max_seconds=1, strict=True)
    try:
        with pytest.raises(ValueError, match='không cắt'):
            writer.append(tmp_path/'source.wav')
        assert writer.frames == 0
        with pytest.raises(ValueError, match='Khoảng nghỉ'):
            writer.silence(1.001)
    finally:
        writer.close()


@pytest.mark.parametrize('seconds', [0, -1, 10801, float('nan'), float('inf'), .0000001])
def test_invalid_targets_are_rejected(seconds):
    with pytest.raises(ValueError):
        target_frames(seconds)


def test_api_records_duration_and_rejects_conflicting_srt(studio):
    client, root = studio
    voice = {'id': 'sys-duration', 'name': 'Duration test', 'engine': 'system',
             'speaker': 'test', 'languages': list(LANGUAGES)}
    base = {'text': 'Hello.', 'voice_id': voice['id'], 'language': 'en-US'}
    srt = '1\n00:00:00,000 --> 00:00:02,345\nHello.'
    with patch('app.installed_voices', return_value=[voice]), patch('app.executor.submit'):
        response = client.post('/api/speech', json={**base, 'target_seconds': 2.345})
        assert response.status_code == 202, response.text
        assert response.json()['target_seconds'] == 2.345
        assert client.post('/api/speech', json={**base, 'target_seconds': 61, 'max_minutes': 1}).status_code == 422
        for target in [0, -1, 10801, 'nan', 'inf', .0000001]:
            assert client.post('/api/speech', json={**base, 'target_seconds': target}).status_code == 422
        for changes in [{'target_seconds': 3}, {'target_seconds': 2.345, 'cue_fit': 'gap'}]:
            assert client.post('/api/speech', json={**base, 'text': srt, 'input_format': 'srt', **changes}).status_code == 422
        response = client.post('/api/speech', json={**base, 'text': srt, 'input_format': 'srt', 'target_seconds': 2.345})
        assert response.status_code == 202
        (root/'videos').mkdir(exist_ok=True)
        import app
        video = 'e'*32
        app.write_json(root/'videos'/f'{video}.json', {'duration': 3})
        response = client.post('/api/speech', json={**base, 'video_id': video, 'video_offset': 1, 'target_seconds': 2.5})
        assert response.status_code == 422


def test_download_conversion_also_verifies_decoded_duration(studio):
    import app
    client, root = studio
    ident = 'd'*32
    tone(root/f'audio/{ident}.wav', 2.345)
    app.write_json(root/f'jobs/{ident}.json', {
        'id': ident, 'status': 'done', 'format': 'wav', 'duration_verified': True,
        'duration_report': {'expected_seconds': 2.345},
    })
    response = client.get(f'/api/jobs/{ident}/export.mp3')
    assert response.status_code == 200, response.text
    assert verify_export(root/f'audio/{ident}.mp3', root/'parts', 2.345)['error_frames'] == 0


def test_real_windows_speech_exports_match_duration(tmp_path, monkeypatch):
    """Exercise the production SAPI engine when the Windows runner has a voice."""
    import os
    from pathlib import Path
    if os.name != 'nt':
        pytest.skip('Real Windows SAPI speech requires Windows')
    from system_voices import installed_voices
    installed_voices.cache_clear()
    voice = next((v for v in installed_voices() if v['languages'][0].startswith('en')), None)
    if voice is None:
        pytest.skip('This Windows host has no installed English SAPI voice')
    root = Path(os.environ.get('VOICE_STUDIO_SPEECH_PROOF', str(tmp_path)))
    root.mkdir(parents=True, exist_ok=True)
    worker = local_worker(root, monkeypatch)
    text = 'Hello. Every spoken word stays in this recording.'
    payload = {'speaker': voice['speaker'], 'language': voice['languages'][0],
               'voice_id': voice['id'], 'max_minutes': 1}
    worker.render(job('real-txt', text, target_seconds=10, **payload))
    srt = f'1\n00:00:00,500 --> 00:00:10,000\n{text}'
    worker.render(job('real-srt', srt, input_format='srt', format='mp3', **payload))
    reports = {}
    for ident, extension in [('real-txt', 'wav'), ('real-srt', 'mp3')]:
        report = verify_export(root/f'audio/{ident}.{extension}', root, 10)
        assert report['sample_frames'] == 240000
        reports[ident] = report
    with wave.open(str(root/'audio/real-txt.wav')) as audio:
        samples = np.frombuffer(audio.readframes(audio.getnframes()), '<i2')
    assert samples.any() and samples.std() > 10
    (root/'proof.json').write_text(json.dumps({
        'engine': 'Windows SAPI', 'speaker': voice['speaker'],
        'language': voice['languages'][0], 'text': text, 'reports': reports,
    }, ensure_ascii=False, indent=2), encoding='utf-8')


def test_txt_exported_srt_round_trip_keeps_the_final_target(tmp_path, monkeypatch):
    worker = local_worker(tmp_path, monkeypatch)
    synth = lambda text, path: tone(path, .6)
    worker.render(job('original', target_seconds=10), synth)
    text = (tmp_path/'audio/original.srt').read_text(encoding='utf-8')
    cues = parse_srt(text)
    assert cues[-1]['end'] == 10
    assert [c['text'] for c in cues] == ['First sentence.', 'Last sentence.']
    worker.render(job('roundtrip', text, input_format='srt'), synth)
    assert pcm_frames(tmp_path/'audio/original.wav') == pcm_frames(tmp_path/'audio/roundtrip.wav') == 240000
