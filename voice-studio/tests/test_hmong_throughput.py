"""Speech throughput excludes manufactured gaps and needs sustained evidence."""
import importlib
import json
import shutil
import wave

import numpy as np
import pytest
import soundfile as sf

from performance import speed_report


def test_short_fast_sample_is_not_a_sustained_or_one_hour_achievement():
    report = speed_report(1, .01, spoken_audio_seconds=1)
    assert report['realtime_multiplier'] == 100
    assert report['estimated_hour_seconds'] == 36
    assert report['measurement_basis'] == 'speech_chunks_excluding_inserted_silence'
    assert not report['sustained_measurement']
    assert not report['target_30x_met_on_sample']
    assert not report['target_30x_verified_one_hour']
    assert report['estimate_only']


def test_sustained_sample_and_actual_one_hour_run_are_distinguished():
    sustained = speed_report(65, 2, spoken_audio_seconds=60)
    assert sustained['realtime_multiplier'] == 30
    assert sustained['measurement_audio_seconds'] == 60
    assert sustained['measurement_output_audio_seconds'] == 65
    assert sustained['measurement_inserted_silence_seconds'] == 5
    assert sustained['sustained_measurement'] and sustained['target_30x_met_on_sample']
    assert not sustained['target_30x_verified_one_hour'] and sustained['estimate_only']
    actual_hour = speed_report(3605, 120, spoken_audio_seconds=3600)
    assert actual_hour['target_30x_verified_one_hour']
    assert not actual_hour['estimate_only']
    slow_hour = speed_report(3600, 121, spoken_audio_seconds=3600)
    assert not slow_hour['target_30x_met_on_sample']
    assert not slow_hour['target_30x_verified_one_hour']


def test_legacy_output_measurement_is_labelled_and_cannot_verify_spoken_hour():
    legacy = speed_report(3600, 120)
    assert legacy['target_30x_met_on_sample']
    assert legacy['measurement_basis'] == 'output_duration_legacy'
    assert legacy['measurement_inserted_silence_seconds'] is None
    assert not legacy['target_30x_verified_one_hour'] and legacy['estimate_only']


@pytest.mark.parametrize('audio,elapsed,spoken', [
    (True, 1, 1), (1, True, 1), (1, 1, True),
    (float('nan'), 1, 1), (1, float('inf'), 1), (1, 1, float('nan')),
    (1, 1, float('inf')), (0, 1, 1), (1, 0, 1), (1, 1, 0),
    (1, 1, -1), (1, 1, 1.1), (1, -1, 1),
    (10 ** 1000, 1, 1), (1, 10 ** 1000, 1),
])
def test_invalid_or_inconsistent_measurements_have_no_speed_report(audio, elapsed, spoken):
    assert speed_report(audio, elapsed, spoken_audio_seconds=spoken) is None


def test_single_sample_rounding_does_not_create_negative_inserted_silence():
    report = speed_report(1, 1, spoken_audio_seconds=1 + 1 / 24000)
    assert report['measurement_audio_seconds'] == 1
    assert report['measurement_inserted_silence_seconds'] == 0


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, '_hmong_model_instance', None)
    (tmp_path / 'audio').mkdir()
    return module


def job(**changes):
    return {'id': 'throughput', 'engine': 'f5_hmong', 'speaker': None,
            'voice_id': 'personal-test-voice', 'language': 'mww', 'format': 'wav',
            'text': 'Nyob zoo.', 'input_format': 'txt', 'speed': 1,
            'delivery': 'natural', 'paragraph_pause': 0, 'max_minutes': 180,
            'segment_plan': 'hmong-expression-v1', 'emotion': 'neutral',
            'emotion_strength': 0, 'auto_rhythm': False, **changes}


def sine(path, seconds, *, trailing_silence=0):
    samples = .2 * np.sin(2 * np.pi * 220 * np.arange(round(24000 * seconds)) / 24000)
    if trailing_silence:
        samples = np.concatenate((samples, np.zeros(round(24000 * trailing_silence))))
    sf.write(str(path), samples, 24000, subtype='PCM_16')


def result(worker, settings, synthesize):
    worker.render(settings, synthesize=synthesize)
    data = json.loads((worker.DATA / 'parts' / settings['id'] / 'result.json').read_text())
    with wave.open(str(worker.DATA / 'audio' / (settings['id'] + '.wav'))) as output:
        assert data['audio_seconds'] == output.getnframes() / output.getframerate()
    assert 0 <= data['spoken_audio_seconds'] <= data['audio_seconds']
    assert data['spoken_audio_seconds'] + data['inserted_silence_seconds'] == pytest.approx(data['audio_seconds'])
    return data


def test_real_hour_of_srt_padding_cannot_masquerade_as_one_hour_of_voice(worker):
    settings = job(text='1\n00:00:00,000 --> 01:00:00,000\nNyob zoo.\n',
                   input_format='srt')
    data = result(worker, settings, lambda text, path: sine(path, .6))
    assert data['audio_seconds'] == 3600
    assert data['spoken_audio_seconds'] == .6
    assert data['inserted_silence_seconds'] == 3599.4
    # The former total-duration calculation called this 360x realtime.
    report = speed_report(data['audio_seconds'], 10,
                          spoken_audio_seconds=data['spoken_audio_seconds'])
    assert report['realtime_multiplier'] == .06
    assert not report['target_30x_met_on_sample']
    assert not report['target_30x_verified_one_hour']


def test_explicit_and_paragraph_pauses_are_excluded_but_model_silence_is_retained(worker):
    settings = job(text='Nyob zoo.[pause=2]Peb tuaj.', paragraph_pause=.3)
    data = result(worker, settings,
                  lambda text, path: sine(path, .5, trailing_silence=.5))
    # Two full one-second chunks count, including their own quiet endings.
    assert data['spoken_audio_seconds'] == 2
    assert data['inserted_silence_seconds'] == pytest.approx(2.3)


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='Real cue fitting requires FFmpeg')
def test_real_ffmpeg_cue_fit_scales_speech_spans_and_excludes_compressed_pause(worker):
    settings = job(text='1\n00:00:00,000 --> 00:00:01,250\n'
                        'Nyob zoo.[pause=0.6]Peb tuaj.\n', input_format='srt',
                   max_cue_tempo=2)
    data = result(worker, settings, lambda text, path: sine(path, .6))
    alignment = json.loads((worker.DATA / 'parts' / settings['id'] / 'alignment.json').read_text())
    cue = alignment['cues'][0]
    assert cue['status'] == 'matched' and cue['tempo'] > 1
    fitted_seconds = cue['spoken_end'] - cue['spoken_start']
    assert data['spoken_audio_seconds'] == pytest.approx(fitted_seconds * 2 / 3, abs=2 / 24000)
    assert data['spoken_audio_seconds'] < 1.2  # actual post-fit duration, not source chunks
    assert .38 < data['inserted_silence_seconds'] < .5


def test_output_limit_counts_only_the_speech_that_was_actually_written(worker):
    settings = job(text='1\n00:00:00,000 --> 00:02:00,000\n'
                        'Nyob zoo.[pause=10]Peb tuaj.\n', input_format='srt',
                   max_minutes=1)
    data = result(worker, settings, lambda text, path: sine(path, 30))
    assert data['duration_limited']
    assert data['audio_seconds'] == 60
    assert data['spoken_audio_seconds'] == 50
    assert data['inserted_silence_seconds'] == 10
