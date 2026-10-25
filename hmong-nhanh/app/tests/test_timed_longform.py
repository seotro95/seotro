"""Subtitle timing is exact, bounded, resumable and never spoken as metadata."""
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import wave

import numpy as np
import pytest

import audio_timing
import longform


def audio(seconds, value=513):
    output = io.BytesIO()
    with wave.open(output, 'wb') as sound:
        sound.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        sound.writeframes(value.to_bytes(2, 'little', signed=True) * round(seconds * 24000))
    return output.getvalue()


def pcm(path):
    with wave.open(str(path), 'rb') as sound:
        return sound.readframes(sound.getnframes())


def setup_job(folder, text, **changes):
    sample = folder / 'reference.wav'
    sample.write_bytes(audio(4))
    payload = {'text': text, 'voice': 'custom-0123456789abcdef', 'quality': 'balanced',
               'style': 'natural', 'speed': 1, 'timing': 'auto',
               '_reference': {'path': str(sample), 'text': 'A different language, exact reference words.'},
               **changes}
    longform.atomic_json(folder / 'input.json', payload)
    return payload


@pytest.fixture(autouse=True)
def device_and_disk(monkeypatch):
    monkeypatch.setattr(longform.cloning_engine, 'runtime_device', lambda: 'cpu')
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=2 * 1024 ** 3))


def test_actual_user_timestamp_is_silence_until_start_and_exact_ending(tmp_path, monkeypatch):
    setup_job(tmp_path, '1\n00:04:28,533 --> 00:04:29,333\nKuv muaj 25 xyoo.\n')
    calls = []
    def synth(text, speed, sample, transcript, quality):
        calls.append((text, speed, sample, transcript, quality))
        return audio(.8)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', synth)
    result = longform.process_job(tmp_path)
    assert calls == [('Kuv muaj 25 xyoo.', 1, tmp_path / 'reference.wav',
                      'A different language, exact reference words.', 'balanced')]
    assert result['alignment'] == 'subtitle' and result['source_format'] == 'srt'
    assert result['target_seconds'] == result['audio_seconds'] == 269.333
    data = pcm(tmp_path / 'parts' / result['parts'][0]['filename'])
    start, end = round(268.533 * 24000), round(269.333 * 24000)
    assert len(data) == end * 2
    assert data[:start * 2] == bytes(start * 2)
    assert data[start * 2:] == bytes([1, 2]) * (end - start)
    checkpoint = json.loads((tmp_path / 'checkpoint.json').read_text())
    assert checkpoint['spoken_seconds'] == .8  # The 268s lead-in never boosts throughput.
    assert abs(.8 / result['throughput'] - result['elapsed_seconds']) <= .00051


def test_exact_gap_frames_and_chapter_boundaries(tmp_path, monkeypatch):
    setup_job(tmp_path, '7\n00:00:00,250 --> 00:00:01,000\nNyob 12.\n\n8\n00:00:01,333 --> 00:00:02,333\n2026\n')
    monkeypatch.setattr(longform, 'CHAPTER_SECONDS', 1)
    calls = []
    def synth(text, *args, **kwargs):
        calls.append(text)
        return audio(.75 if len(calls) == 1 else 1, value=len(calls))
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', synth)
    result = longform.process_job(tmp_path)
    assert calls == ['Nyob 12.', '2026']
    assert [part['seconds'] for part in result['parts']] == [1, 1, .333]
    data = b''.join(pcm(tmp_path / 'parts' / part['filename']) for part in result['parts'])
    expected = bytes(round(.25 * 24000) * 2) + b'\x01\0' * round(.75 * 24000)
    expected += bytes(round(.333 * 24000) * 2) + b'\x02\0' * 24000
    assert data == expected


@pytest.mark.parametrize('target', [12000, 48000])
def test_pitch_preserving_stretch_exact_length(target):
    samples = np.sin(2 * np.pi * 440 * np.arange(24000) / 24000) * .25
    original = io.BytesIO()
    with wave.open(original, 'wb') as sound:
        sound.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        sound.writeframes((samples * 32767).astype('<i2').tobytes())
    fitted, generated_seconds, ratio = audio_timing.fit_wav(original.getvalue(), target, 1)
    with wave.open(io.BytesIO(fitted), 'rb') as sound:
        assert sound.getframerate() == 24000 and sound.getnframes() == target
        values = np.frombuffer(sound.readframes(target), dtype='<i2')
    spectrum = np.abs(np.fft.rfft(values * np.hanning(len(values))))
    peak = np.fft.rfftfreq(len(values), 1 / 24000)[np.argmax(spectrum)]
    assert abs(peak - 440) < 3  # Resampling would incorrectly move this to 220/880Hz.
    assert generated_seconds == 1 and ratio == 24000 / target


@pytest.mark.parametrize('target', [1000, 100000])
def test_extreme_fitting_refuses_to_cut_words(target):
    with pytest.raises(ValueError, match='Không cắt bỏ lời đọc'):
        audio_timing.fit_wav(audio(1), target, 23)


def test_stop_resume_preserves_reference_chunks_chapters_and_timing(tmp_path, monkeypatch):
    setup_job(tmp_path, '1\n00:00:00,500 --> 00:00:01,000\nFirst 12.\n\n2\n00:00:01,500 --> 00:00:02,000\nSecond 25.\n')
    monkeypatch.setattr(longform, 'CHAPTER_SECONDS', 1)
    calls = []
    def synth(text, *args, **kwargs):
        calls.append(text)
        if len(calls) == 2:
            raise RuntimeError('interrupted')
        return audio(.5, 111 if text.startswith('First') else 222)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', synth)
    with pytest.raises(RuntimeError, match='interrupted'):
        longform.process_job(tmp_path)
    first = tmp_path / 'chunks' / 'chunk-000000.wav'
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    part = tmp_path / 'parts' / 'part-0001.wav'
    modified = part.stat().st_mtime_ns
    result = longform.process_job(tmp_path)
    assert calls == ['First 12.', 'Second 25.', 'Second 25.']
    assert result['resumed'] and result['audio_seconds'] == 2
    assert hashlib.sha256(first.read_bytes()).hexdigest() == digest
    assert part.stat().st_mtime_ns == modified
    assert not list(tmp_path.rglob('*.pending'))
    assert result['completed'] == result['total'] == 2


def test_full_disk_after_speech_checkpoint_resumes_without_regeneration(tmp_path, monkeypatch):
    setup_job(tmp_path, '1\n00:00:01,000 --> 00:00:02,000\nNyob zoo.\n')
    calls = []
    def synth(text, *args, **kwargs):
        calls.append(text)
        return audio(1)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', synth)
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=100 * 1024 ** 2 + 10))
    with pytest.raises(ValueError, match='Không đủ đĩa'):
        longform.process_job(tmp_path)
    assert json.loads((tmp_path / 'checkpoint.json').read_text())['completed'] == 1
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=2 * 1024 ** 3))
    assert longform.process_job(tmp_path)['audio_seconds'] == 2
    assert calls == ['Nyob zoo.']


def test_natural_mode_cleans_subtitle_metadata_without_adding_timeline_silence(tmp_path, monkeypatch):
    setup_job(tmp_path, '1\n00:04:28,533 --> 00:04:29,333\nI have 25 books.\n', timing='natural')
    calls = []
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda text, *a, **kw: calls.append(text) or audio(1))
    result = longform.process_job(tmp_path)
    assert calls == ['I have 25 books.']
    assert result['audio_seconds'] == 1 and result['alignment'] == 'natural'
    assert result['target_seconds'] is None


def test_long_cue_is_bounded_and_keeps_all_words_and_outer_times():
    text = ' '.join('word' + str(i) for i in range(1000))
    plan = longform.timed_plan([{'start': .533, 'end': 150.333, 'text': text}])
    assert len(plan) > 1 and all(0 < len(piece['text']) <= 350 for piece in plan)
    assert ' '.join(piece['text'] for piece in plan).split() == text.split()
    assert plan[0]['start_frame'] == round(.533 * 24000)
    assert plan[-1]['end_frame'] == round(150.333 * 24000)
    assert all(a['end_frame'] == b['start_frame'] for a, b in zip(plan, plan[1:]))


@pytest.mark.parametrize('change', ['timing', 'timestamp', 'voice', 'reference'])
def test_resume_rejects_changed_timeline_or_reference(tmp_path, monkeypatch, change):
    payload = setup_job(tmp_path, '1\n00:00:01,000 --> 00:00:02,000\nNyob zoo.\n')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(1))
    longform.process_job(tmp_path)
    if change == 'timing':
        payload['timing'] = 'natural'
    elif change == 'timestamp':
        payload['text'] = payload['text'].replace('02,000', '02,100')
    elif change == 'voice':
        payload['voice'] = 'hmong-white-female'
    else:
        payload['_reference']['text'] += ' Changed.'
    longform.atomic_json(tmp_path / 'input.json', payload)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: pytest.fail('must reject before synthesis'))
    with pytest.raises(ValueError, match='Thiết lập khác'):
        longform.process_job(tmp_path)
