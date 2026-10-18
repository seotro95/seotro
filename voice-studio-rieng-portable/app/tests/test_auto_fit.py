"""Exercise automatic SRT fitting with real FFmpeg and synthetic audio only."""
import importlib
import json
import wave

import numpy as np
import pytest

from subtitles import parse_srt


RATE = 24000


@pytest.fixture
def renderer(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    return worker, tmp_path


def write_tones(path, sections):
    """Keep both halves distinguishable so fitting cannot silently cut the tail."""
    chunks = []
    for duration, frequency in sections:
        clock = np.arange(round(duration * RATE)) / RATE
        chunks.append((6000 * np.sin(2 * np.pi * frequency * clock)).astype('<i2'))
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(np.concatenate(chunks).tobytes())


def read_pcm(path):
    with wave.open(str(path), 'rb') as source:
        assert (source.getnchannels(), source.getsampwidth(), source.getframerate()) == (1, 2, RATE)
        return np.frombuffer(source.readframes(source.getnframes()), dtype='<i2')


def peak_frequency(samples):
    window = samples.astype(float) * np.hanning(len(samples))
    return np.fft.rfftfreq(len(window), 1 / RATE)[np.argmax(abs(np.fft.rfft(window)))]


def job(identifier, text, mode='auto'):
    return {'id': identifier, 'text': text, 'input_format': 'srt', 'engine': 'system',
            'format': 'wav', 'speed': 1, 'cue_fit': mode, 'max_cue_tempo': 1.5}


def test_auto_fits_reported_1410ms_into_900ms_while_strict_rejects(renderer):
    worker, data = renderer
    text = '1\n00:00:14,166 --> 00:00:15,066\nMột câu cần căn thời gian.'

    def synthesize(text, output):
        write_tones(output, [(1.410, 220)])

    with pytest.raises(ValueError, match='Câu SRT 1'):
        worker.render(job('strict', text, 'strict'), synthesize)
    assert not (data / 'audio/strict.wav').exists()
    worker.render(job('auto', text), synthesize)
    samples = read_pcm(data / 'audio/auto.wav')
    assert len(samples) == round(15.066 * RATE)
    assert not np.any(samples[:round(14.166 * RATE)])
    assert np.any(samples[round(14.166 * RATE):])
    report = json.loads((data / 'parts/auto/alignment.json').read_text())
    assert report['sync_ok'] is True
    assert report['cues'][0]['status'] == 'matched'
    assert report['cues'][0]['tempo'] > 1.5
    assert parse_srt((data / 'audio/auto.srt').read_text()) == parse_srt(text)


def test_auto_above_two_times_keeps_pitch_tail_and_original_cue_timeline(renderer):
    worker, data = renderer
    text = ('1\n00:00:00,250 --> 00:00:01,050\nCâu dài.\n\n'
            '2\n00:00:01,400 --> 00:00:01,900\nCâu ngắn.')

    def synthesize(text, output):
        if text == 'Câu dài.':
            write_tones(output, [(1.5, 220), (1.5, 440)])
        else:
            write_tones(output, [(.2, 660)])

    worker.render(job('fast', text), synthesize)
    samples = read_pcm(data / 'audio/fast.wav')
    assert len(samples) == round(1.9 * RATE)
    assert not np.any(samples[:round(.25 * RATE)])
    assert not np.any(samples[round(1.05 * RATE):round(1.4 * RATE)])
    first_cue = samples[round(.25 * RATE):round(1.05 * RATE)]
    # Both tones survive in source order; rate changes must preserve their pitch.
    assert peak_frequency(first_cue[round(.06 * RATE):round(.2 * RATE)]) == pytest.approx(220, abs=15)
    assert peak_frequency(first_cue[round(.55 * RATE):round(.69 * RATE)]) == pytest.approx(440, abs=15)
    report = json.loads((data / 'parts/fast/alignment.json').read_text())
    assert report['sync_ok'] is True
    assert [cue['status'] for cue in report['cues']] == ['matched', 'matched']
    assert report['cues'][0]['tempo'] > 2
    assert report['cues'][0]['warning'] == 'fast_tempo'
    assert report['cues'][1]['spoken_start'] == 1.4
    assert parse_srt((data / 'audio/fast.srt').read_text()) == parse_srt(text)


def test_auto_cancellation_preserves_checkpoint_without_publishing_audio(renderer):
    worker, data = renderer
    text = '1\n00:00:00,000 --> 00:00:00,900\nMột câu đang tạo.'

    def synthesize(text, output):
        write_tones(output, [(1.410, 220)])
        (data / 'parts/cancel/cancel.flag').touch()

    with pytest.raises(InterruptedError):
        worker.render(job('cancel', text), synthesize)
    assert not (data / 'audio/cancel.wav').exists()
    assert not (data / 'audio/cancel.srt').exists()
    assert (data / 'parts/cancel/000000.wav').exists()
