import io
import math
from pathlib import Path
import shutil
import struct
import wave

import pytest

import review_script as review


def test_srt_accepts_multiple_blank_separators_and_removes_subtitle_formatting():
    script = review.parse_script(
        '1\n00:00:00,200 --> 00:00:02,700\n<font color="white">Nyob <i>zoo.</i></font>'
        '\n\n \n\n2\n00:00:03,000 --> 00:00:05,000\n<b>Kuv hais lus Hmoob.</b>\n')
    assert script.timed
    assert [cue.text for cue in script.cues] == ['Nyob zoo.', 'Kuv hais lus Hmoob.']
    assert script.duration == 5


def test_srt_formatting_without_speech_is_rejected():
    with pytest.raises(review.ScriptError, match='thiếu lời'):
        review.parse_script('00:00:00,200 --> 00:00:02,700\n<i></i>')


def write_voice(path, seconds=.05, value=1200, frequency=None):
    frames = round(seconds * review.SAMPLE_RATE)
    if frequency is None:
        pcm = struct.pack('<h', value) * frames
    else:
        pcm = b''.join(struct.pack('<h', round(value * math.sin(2 * math.pi * frequency * i / review.SAMPLE_RATE)))
                       for i in range(frames))
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(review.SAMPLE_RATE)
        writer.writeframes(pcm)
    return Path(path)


def read_voice(source):
    if isinstance(source, bytes):
        source = io.BytesIO(source)
    else:
        source = str(source)
    with wave.open(source, 'rb') as reader:
        assert (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) == (1, 2, 24000)
        data = reader.readframes(reader.getnframes())
        return struct.unpack('<' + 'h' * (len(data) // 2), data)


def test_plain_long_script_has_one_immutable_cue_and_no_timestamps():
    source = 'Kuv hais lus Hmoob. ' * 50_000
    script = review.parse_script(source)
    assert not script.timed and script.duration == 0
    assert script.cues == (review.Cue(source.strip()),)
    with pytest.raises(AttributeError):
        script.cues[0].text = 'changed'
    assert len(review.parse_script('a' * 1_000_000).cues[0].text) == 1_000_000
    with pytest.raises(review.ScriptError, match='1.000.000'):
        review.parse_script('a' * 1_000_001)


def test_srt_indexes_optional_multiline_bom_and_crlf():
    source = '\ufeff1\r\n00:00:00,200 --> 00:00:02,700\r\nNyob zoo.\r\nKuv hais lus Hmoob.\r\n\r\n00:00:03.000 --> 00:00:04.250\r\nUa tsaug.'
    script = review.parse_script(source)
    assert script.timed and script.duration == 4.25
    assert script.cues == (review.Cue('Nyob zoo.\nKuv hais lus Hmoob.', .2, 2.7),
                           review.Cue('Ua tsaug.', 3.0, 4.25))


@pytest.mark.parametrize('source', [
    '00:00:00,200 --> 00:00:02,700',
    '00:00:00,2 --> 00:00:02,700\nNyob zoo.',
    '00:60:00,200 --> 01:00:02,700\nNyob zoo.',
    '-00:00:00,200 --> 00:00:02,700\nNyob zoo.',
    '00:00:02,700 --> 00:00:02,700\nNyob zoo.',
    '00:00:03,000 --> 00:00:02,700\nNyob zoo.',
    'Nyob zoo --> Ua tsaug.',
    '1\n00:00:00,000 --> 00:00:01,000\nA\n2\n00:00:01,000 --> 00:00:02,000\nB',
    '00:00:00,000 --> 00:00:02,000\nA\n\n00:00:01,999 --> 00:00:03,000\nB',
    '00:00:03,000 --> 00:00:04,000\nA\n\n00:00:01,000 --> 00:00:02,000\nB',
    '23:59:59,000 --> 24:00:00,001\nNyob zoo.',
    '00:00:00,000 --> 00:00:01,000 unexpected\nNyob zoo.',
])
def test_malformed_srt_rejected_instead_of_reading_timestamps(source):
    with pytest.raises(review.ScriptError):
        review.parse_script(source)


def test_explicit_formats_and_24_hour_boundary():
    assert review.parse_script('A --> B', 'text').cues[0].text == 'A --> B'
    with pytest.raises(review.ScriptError):
        review.parse_script('Nyob zoo.', 'srt')
    with pytest.raises(review.ScriptError):
        review.parse_script('Nyob zoo.', 'other')
    with pytest.raises(review.ScriptError):
        review.parse_script('\ufeff')
    script = review.parse_script('23:59:59,000 --> 24:00:00,000\nNyob zoo.')
    assert script.duration == 86400
    assert script.duration * 24000 * 2 < 2 ** 32 - 44


def test_cue_limit_prevents_unbounded_srt_work(monkeypatch):
    monkeypatch.setattr(review, 'MAX_CUES', 2)
    source = '\n\n'.join(f'00:00:0{i},000 --> 00:00:0{i + 1},000\nA' for i in range(3))
    with pytest.raises(review.ScriptError, match='20.000'):
        review.parse_script(source)


def test_timeline_places_cues_without_speaking_timestamps_and_reports_real_progress(tmp_path, monkeypatch):
    script = review.parse_script('1\n00:00:00,200 --> 00:00:00,400\nNyob zoo.\n\n'
                                 '2\n00:00:00,600 --> 00:00:00,800\nUa tsaug.')
    calls = []
    events = []

    def synthesize(text, reference, emotion, speed, *, progress, output_path):
        calls.append((text, reference, emotion, speed))
        progress({'progress': 5, 'phase': 'loading', 'generated_seconds': 0})
        progress({'progress': 99, 'phase': 'synthesis', 'generated_seconds': .05})
        return write_voice(output_path, value=1000 * len(calls))

    monkeypatch.setattr(review.cosy_engine, 'synthesize', synthesize)
    target = tmp_path / 'review.wav'
    assert review.render_timeline(script, 'female.mp3', 'review', 1.1,
                                  output_path=target, progress=events.append) == target
    samples = read_voice(target)
    assert len(samples) == 19200
    assert set(samples[:4800]) == {0}
    assert set(samples[4800:6000]) == {1000}
    assert set(samples[6000:14400]) == {0}
    assert set(samples[14400:15600]) == {2000}
    assert set(samples[15600:]) == {0}
    assert calls == [('Nyob zoo.', 'female.mp3', 'review', 1.1), ('Ua tsaug.', 'female.mp3', 'review', 1.1)]
    assert [event['progress'] for event in events] == sorted(event['progress'] for event in events)
    assert all(0 <= event['progress'] <= 99 for event in events)
    assert events[-1]['completed_units'] == events[-1]['total_units'] == 2
    assert events[-1]['generated_seconds'] == .8
    assert not list(tmp_path.glob('hmong-timeline-*'))


def test_small_direct_render_returns_wav_bytes(monkeypatch):
    script = review.parse_script('00:00:00,000 --> 00:00:00,100\nNyob zoo.')
    monkeypatch.setattr(review.cosy_engine, 'synthesize',
                        lambda *args, output_path, **kwargs: write_voice(output_path))
    result = review.render_timeline(script, 'reference.mp3')
    assert isinstance(result, bytes) and len(read_voice(result)) == 2400


def test_overlong_speech_is_not_truncated_and_preserves_old_output(tmp_path, monkeypatch):
    script = review.parse_script('00:00:00,000 --> 00:00:00,100\nNyob zoo.')
    monkeypatch.setattr(review.cosy_engine, 'synthesize',
                        lambda *args, output_path, **kwargs: write_voice(output_path, seconds=.3))
    target = tmp_path / 'review.wav'
    target.write_bytes(b'previous completed result')
    with pytest.raises(review.ScriptError, match='không cắt mất lời'):
        review.render_timeline(script, 'reference.mp3', output_path=target)
    assert target.read_bytes() == b'previous completed result'
    assert not list(tmp_path.glob('hmong-timeline-*'))


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='real FFmpeg unavailable')
def test_ffmpeg_fits_speech_and_preserves_pitch(tmp_path, monkeypatch):
    script = review.parse_script('00:00:00,100 --> 00:00:00,600\nNyob zoo.')
    monkeypatch.setattr(review.cosy_engine, 'synthesize',
                        lambda *args, output_path, **kwargs:
                        write_voice(output_path, seconds=.8, value=6000, frequency=440))
    result = review.render_timeline(script, 'reference.mp3', output_path=tmp_path / 'fit.wav')
    samples = read_voice(result)
    assert len(samples) == 14400 and not any(samples[:2400])
    # Frequency in the middle of the speech remains 440 Hz, rather than being
    # raised by the ~1.6x time compression.
    voiced = samples[4800:9600]
    upward_crossings = sum(a <= 0 < b for a, b in zip(voiced, voiced[1:]))
    assert abs(upward_crossings / (.2) - 440) < 10


def test_failed_engine_and_cancelled_progress_never_replace_output(tmp_path, monkeypatch):
    script = review.parse_script('00:00:00,000 --> 00:00:00,100\nNyob zoo.')
    target = tmp_path / 'review.wav'
    target.write_bytes(b'old')

    def fail(*args, output_path, **kwargs):
        write_voice(output_path)
        raise review.cosy_engine.EngineError('inference failed')

    monkeypatch.setattr(review.cosy_engine, 'synthesize', fail)
    with pytest.raises(review.cosy_engine.EngineError):
        review.render_timeline(script, 'reference.mp3', output_path=target)
    assert target.read_bytes() == b'old'
    monkeypatch.setattr(review.cosy_engine, 'synthesize',
                        lambda *args, output_path, **kwargs: write_voice(output_path))

    def cancel_at_finalization(event):
        if event['progress'] >= 98:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        review.render_timeline(script, 'reference.mp3', output_path=target, progress=cancel_at_finalization)
    assert target.read_bytes() == b'old'
    assert not list(tmp_path.glob('hmong-timeline-*'))


def test_invalid_or_truncated_generated_wav_is_rejected(tmp_path, monkeypatch):
    script = review.parse_script('00:00:00,000 --> 00:00:00,100\nNyob zoo.')

    def truncated(*args, output_path, **kwargs):
        write_voice(output_path)
        output_path.write_bytes(output_path.read_bytes()[:-4])

    monkeypatch.setattr(review.cosy_engine, 'synthesize', truncated)
    with pytest.raises(review.ScriptError, match='thiếu dữ liệu'):
        review.render_timeline(script, 'reference.mp3', output_path=tmp_path / 'never.wav')
    assert not (tmp_path / 'never.wav').exists()


@pytest.mark.parametrize('script', [
    review.Script((review.Cue('hello'),), False, 0),
    review.Script((review.Cue('hello', -1, 1),), True, 1),
    review.Script((review.Cue('hello', 0, float('nan')),), True, 1),
    review.Script((review.Cue('hello', 0, 1),), True, 2),
])
def test_programmatic_invalid_timeline_rejected_before_inference(script):
    with pytest.raises(review.ScriptError):
        review.render_timeline(script, 'reference.mp3')
