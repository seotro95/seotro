"""Regression coverage for padded cues and resumable timing failures."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import wave

import numpy as np
import pytest

import audio_timing
import longform

RATE = audio_timing.RATE
USER_TEXT = 'nws tsis txhawj txog nws tus kheej ntau'
USER_SRT = '196\n00:05:33,366 --> 00:05:34,533\n' + USER_TEXT


def audio(seconds, frequency=220):
    stream = io.BytesIO()
    frames = round(seconds * RATE)
    values = np.sin(np.arange(frames) * frequency * 2 * np.pi / RATE) * .25
    with wave.open(stream, 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes((values * 32767).astype('<i2').tobytes())
    return stream.getvalue()


def setup(folder, text, **options):
    reference = folder / 'reference.wav'
    reference.write_bytes(audio(4))
    data = {'text': text, 'voice': 'custom-' + '1' * 32, 'quality': 'balanced',
            'style': 'natural', 'speed': 1.0, 'timing': 'auto',
            '_reference': {'path': str(reference), 'text': 'Exact words of this external voice.'}, **options}
    longform.atomic_json(folder / 'input.json', data)
    return data


def merged(folder, result):
    blocks = []
    for part in result['parts']:
        with wave.open(str(folder / 'parts' / part['filename']), 'rb') as wav:
            blocks.append(wav.readframes(wav.getnframes()))
    return np.frombuffer(b''.join(blocks), dtype='<i2')


@pytest.fixture(autouse=True)
def runtime(monkeypatch):
    monkeypatch.setattr(longform.cloning_engine, 'runtime_device', lambda: 'cpu')
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=2 * 1024**3))


def test_latest_user_example_only_speaks_words_and_keeps_exact_absolute_times(tmp_path, monkeypatch):
    setup(tmp_path, USER_SRT)
    calls = []
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda text, *a, **kw: calls.append(text) or audio(1.167))
    result = longform.process_job(tmp_path)
    assert calls == [USER_TEXT]
    samples = merged(tmp_path, result)
    assert len(samples) == round(334.533 * RATE)
    assert not samples[:round(333.366 * RATE)].any()
    assert samples[round(333.366 * RATE):].any()
    assert result['target_seconds'] == result['audio_seconds'] == 334.533


def test_long_slot_pads_on_disk_and_keeps_tiny_chunk_without_extreme_slowdown(tmp_path, monkeypatch):
    setup(tmp_path, '1\n00:00:00,500 --> 00:00:12,500\nNyob zoo.')
    monkeypatch.setattr(longform, 'CHAPTER_SECONDS', 3)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(1))
    result = longform.process_job(tmp_path)
    samples = merged(tmp_path, result)
    assert len(samples) == round(12.5 * RATE)
    assert not samples[:RATE // 2].any()
    assert samples[RATE // 2:round(2.5 * RATE)].any()
    assert not samples[round(2.5 * RATE):].any()
    assert audio_timing.frame_count(tmp_path / 'chunks/chunk-000000.wav') == RATE * 2
    assert [part['seconds'] for part in result['parts']] == [3, 3, 3, 3, .5]
    checkpoint = json.loads((tmp_path / 'checkpoint.json').read_text())
    assert checkpoint['padding_frames'] == {'0': RATE * 10}
    assert checkpoint['spoken_seconds'] == 1
    assert any('Khung phụ đề dài hơn' in warning for warning in result['warnings'])
    assert not list((tmp_path / 'raw').glob('*.wav'))


def test_resume_padded_cue_keeps_finished_audio_and_does_not_synthesize_again(tmp_path, monkeypatch):
    setup(tmp_path, '1\n00:00:00,000 --> 00:00:10,000\nNyob zoo.')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(1))
    original = longform.process_job(tmp_path)
    chunk = tmp_path / 'chunks/chunk-000000.wav'
    part = tmp_path / 'parts/part-0001.wav'
    identities = (chunk.stat().st_mtime_ns, part.stat().st_mtime_ns, part.read_bytes())
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: pytest.fail('already completed'))
    resumed = longform.process_job(tmp_path)
    assert resumed['resumed'] and resumed['audio_seconds'] == original['audio_seconds']
    assert (chunk.stat().st_mtime_ns, part.stat().st_mtime_ns, part.read_bytes()) == identities


def test_unfittable_cue_keeps_raw_audio_and_resume_never_regenerates_it(tmp_path, monkeypatch):
    setup(tmp_path, '1\n00:00:00,000 --> 00:00:01,000\nNyob zoo.')
    calls = []
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: calls.append(1) or audio(3))
    for attempt in range(2):
        with pytest.raises(ValueError, match='Không cắt bỏ lời đọc'):
            longform.process_job(tmp_path)
        checkpoint = json.loads((tmp_path / 'checkpoint.json').read_text())
        assert checkpoint['completed'] == 0
        assert audio_timing.frame_count(tmp_path / 'raw/chunk-000000.wav') == RATE * 3
    assert len(calls) == 1
    assert not (tmp_path / 'result.json').exists()


def test_changed_reference_cannot_reuse_cached_unfittable_audio(tmp_path, monkeypatch):
    data = setup(tmp_path, '1\n00:00:00,000 --> 00:00:01,000\nNyob zoo.')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(3))
    with pytest.raises(ValueError):
        longform.process_job(tmp_path)
    data['_reference']['text'] = 'Different reference words.'
    longform.atomic_json(tmp_path / 'input.json', data)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: pytest.fail('must reject'))
    with pytest.raises(ValueError, match='Thiết lập khác'):
        longform.process_job(tmp_path)


def test_resume_06_checkpoint_without_padding_key_still_works(tmp_path, monkeypatch):
    setup(tmp_path, '1\n00:00:00,000 --> 00:00:01,000\nNyob zoo.')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(1))
    longform.process_job(tmp_path)
    checkpoint = json.loads((tmp_path / 'checkpoint.json').read_text())
    checkpoint.pop('padding_frames')
    longform.atomic_json(tmp_path / 'checkpoint.json', checkpoint)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: pytest.fail('legacy chunk complete'))
    assert longform.process_job(tmp_path)['resumed']


def test_bad_padding_checkpoint_is_rejected_before_any_generation(tmp_path, monkeypatch):
    setup(tmp_path, '1\n00:00:00,000 --> 00:00:10,000\nNyob zoo.')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(1))
    longform.process_job(tmp_path)
    checkpoint = json.loads((tmp_path / 'checkpoint.json').read_text())
    checkpoint['padding_frames'] = {'0': RATE * 10}
    longform.atomic_json(tmp_path / 'checkpoint.json', checkpoint)
    with pytest.raises(ValueError, match='Checkpoint'):
        longform.process_job(tmp_path)


def test_fit_mode_matches_latest_user_window_and_warns_about_fast_speech(tmp_path, monkeypatch):
    setup(tmp_path, USER_SRT, timing='fit')
    calls = []
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda text, *a, **kw: calls.append(text) or audio(3.5))
    result = longform.process_job(tmp_path)
    assert calls == [USER_TEXT]
    assert result['target_seconds'] == result['audio_seconds'] == 334.533
    values = merged(tmp_path, result)
    assert len(values) == round(334.533 * RATE)
    assert not values[:round(333.366 * RATE)].any()
    spoken = values[round(333.366 * RATE):]
    assert len(spoken) == round(1.167 * RATE) and spoken.any()
    spectrum = np.abs(np.fft.rfft(spoken * np.hanning(len(spoken))))
    peak = np.fft.rfftfreq(len(spoken), 1 / RATE)[np.argmax(spectrum)]
    assert abs(peak - 220) < 3
    assert any('trên 2 lần' in warning for warning in result['warnings'])
    checkpoint = json.loads((tmp_path / 'checkpoint.json').read_text())
    assert checkpoint['fast_cues']['0'] == pytest.approx(3.5 / 1.167)
    assert checkpoint['spoken_seconds'] == 3.5
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: pytest.fail('already fitted'))
    resumed = longform.process_job(tmp_path)
    assert resumed['warnings'] == result['warnings']
    assert resumed['resumed'] and resumed['audio_seconds'] == 334.533


def test_auto_mode_keeps_quality_guard_on_same_short_window(tmp_path, monkeypatch):
    setup(tmp_path, USER_SRT)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(3.5))
    with pytest.raises(ValueError, match='0,5 đến 2 lần'):
        longform.process_job(tmp_path)
    assert not (tmp_path / 'result.json').exists()


def test_fit_still_refuses_more_than_four_times_without_cutting_content(tmp_path, monkeypatch):
    setup(tmp_path, USER_SRT, timing='fit')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(5))
    with pytest.raises(ValueError, match='0,5 đến 4 lần'):
        longform.process_job(tmp_path)
    assert audio_timing.frame_count(tmp_path / 'raw/chunk-000000.wav') == 5 * RATE
    assert not (tmp_path / 'result.json').exists()


def test_fit_processes_late_audio_instead_of_clipping_it():
    # A late second tone remains late in the compressed output. Cropping the
    # first second would remove it completely; changing sample rate moves pitch.
    values = np.concatenate([
        np.sin(np.arange(RATE * 2) * 2 * np.pi * frequency / RATE) * .25
        for frequency in (220, 880)])
    source = io.BytesIO()
    with wave.open(source, 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes((values * 32767).astype('<i2').tobytes())
    fitted, original, ratio = audio_timing.fit_wav(source.getvalue(), RATE, 196, max_speed=4)
    with wave.open(io.BytesIO(fitted), 'rb') as wav:
        values = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2')
    assert len(values) == RATE and original == 4 and ratio == 4
    for part, frequency in ((values[RATE // 8:RATE * 3 // 8], 220),
                            (values[RATE * 5 // 8:RATE * 7 // 8], 880)):
        spectrum = np.abs(np.fft.rfft(part * np.hanning(len(part))))
        peak = np.fft.rfftfreq(len(part), 1 / RATE)[np.argmax(spectrum)]
        assert abs(peak - frequency) < 5


def test_fit_checkpoint_does_not_become_auto_checkpoint(tmp_path, monkeypatch):
    payload = setup(tmp_path, '1\n00:00:00,000 --> 00:00:01,000\nNyob zoo.', timing='fit')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *a, **kw: audio(1))
    longform.process_job(tmp_path)
    payload['timing'] = 'auto'
    longform.atomic_json(tmp_path / 'input.json', payload)
    with pytest.raises(ValueError, match='Thiết lập khác'):
        longform.process_job(tmp_path)
