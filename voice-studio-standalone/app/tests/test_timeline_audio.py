"""Real FFmpeg regression checks for cue/video timing, using fixture speech PCM."""
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np
import pytest
import soundfile as sf

from timeline_audio import RATE, fit_cue, pcm_frames, timeline_frames
from subtitles import export_srt, parse_srt

pytestmark = pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='requires FFmpeg')


def tone(path, seconds, frequency=233):
    count = round(seconds * RATE)
    samples = .2 * np.sin(2 * np.pi * frequency * np.arange(count) / RATE)
    # A short amplitude ramp avoids test-only clicks without hiding any tail.
    edge = min(120, count // 2)
    samples[:edge] *= np.linspace(0, 1, edge)
    samples[-edge:] *= np.linspace(1, 0, edge)
    sf.write(str(path), samples, RATE, subtype='PCM_16')


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    module.close_nano_pool()
    monkeypatch.setattr(module, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    (tmp_path / 'voices').mkdir()
    yield module
    module.close_nano_pool()


def timed_job(**overrides):
    cues = [{'start': .123, 'end': 1.234, 'text': 'Câu đầu.'},
            {'start': 1.567, 'end': 2.789, 'text': 'Câu sau.'}]
    return {'id': 'timeline', 'text': export_srt(cues), 'input_format': 'srt',
            'timing_mode': 'exact', 'timeline_seconds': 3.141,
            'engine': 'vieneu_nano', 'speaker': 'Fixture', 'nano_parallel': 1,
            'nano_threads': 1, 'nano_steps': 4, 'format': 'wav', 'speed': 1,
            'paragraph_pause': 3, 'max_minutes': 180,
            'min_cue_tempo': .65, 'max_cue_tempo': 2, **overrides}


@pytest.mark.parametrize('source_seconds,window_seconds,expected_slow', [(1.6, 1.0, False), (.8, 1.2, True)])
def test_real_atempo_fits_speedup_and_slowdown_without_changing_pitch(tmp_path, source_seconds, window_seconds, expected_slow):
    source, output = tmp_path / 'source.wav', tmp_path / 'fitted.wav'
    tone(source, source_seconds)
    result = fit_cue(source, output, round(window_seconds * RATE))
    assert result['speech_frames'] == pcm_frames(output) <= round(window_seconds * RATE)
    assert result['speech_frames'] + result['padding_frames'] == round(window_seconds * RATE)
    assert (result['tempo'] < 1) is expected_slow
    audio, rate = sf.read(output)
    central = audio[len(audio) // 4: len(audio) * 3 // 4]
    frequency = np.count_nonzero(np.diff(np.signbit(central))) * rate / (2 * len(central))
    assert frequency == pytest.approx(233, abs=3)
    # Original PCM remains unmodified and available for resume/refitting.
    assert pcm_frames(source) == round(source_seconds * RATE)


def test_short_speech_obeys_natural_slowdown_floor_and_reports_padding(tmp_path):
    source, output = tmp_path / 'short.wav', tmp_path / 'fitted.wav'
    tone(source, .2)
    result = fit_cue(source, output, RATE * 2)
    assert result['tempo'] == .65
    assert result['padding_frames'] > RATE


def test_overlong_cue_fails_with_number_without_cutting_original(tmp_path):
    source, output = tmp_path / 'long.wav', tmp_path / 'fitted.wav'
    tone(source, 2.5)
    original = source.read_bytes()
    with pytest.raises(ValueError, match=r'Câu 7.*2.50×.*không cắt'):
        fit_cue(source, output, RATE, cue_number=7)
    assert source.read_bytes() == original and not output.exists()


@pytest.mark.parametrize('container', ['wav', 'mp3'])
def test_full_render_matches_every_cue_and_explicit_video_duration(worker, container):
    job = timed_job(format=container)
    spoken = []
    def synthesize(text, path):
        spoken.append(text)
        tone(path, .8 if text == 'Câu đầu.' else 1.6)
    worker.render(job, synthesize)
    assert spoken == ['Câu đầu.', 'Câu sau.']
    source = worker.DATA / 'audio' / ('timeline.' + container)
    if container == 'wav':
        with wave.open(str(source)) as audio:
            assert audio.getnframes() == round(3.141 * RATE)
        samples, rate = sf.read(source)
    else:
        # MP3 packet durations include encoder priming. Its seekable LAME/Xing
        # metadata must restore the exact timeline when an editor decodes it.
        decoded = worker.DATA / 'decoded.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source),
                        '-codec:a', 'pcm_s16le', '-y', str(decoded)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
        assert pcm_frames(decoded) == round(3.141 * RATE)
        samples, rate = sf.read(decoded, dtype='int16')
    # Lossy MP3 has low-level pre-echo around a transition. Its decoded sample
    # count is exact; only WAV can guarantee bit-zero silence up to a boundary.
    margin = .05 if container == 'mp3' else 0
    assert not samples[:round((.123 - margin) * RATE)].any()
    assert not samples[round((1.234 + margin) * RATE):round((1.567 - margin) * RATE)].any()
    assert not samples[round((2.789 + margin) * RATE):].any()
    assert samples[round(.2 * RATE):round(1.0 * RATE)].any()
    assert samples[round(1.7 * RATE):round(2.6 * RATE)].any()
    assert parse_srt((worker.DATA / 'audio/timeline.srt').read_text()) == parse_srt(job['text'])
    result = json.loads((worker.DATA / 'parts/timeline/result.json').read_text())
    assert result['sync_ok'] and not result['duration_limited']
    assert result['audio_seconds'] == 3.141
    assert result['synthesized_audio_seconds'] == pytest.approx(2.4)
    report = result['sync_report']
    assert report['complete'] and report['max_error_ms'] == 0
    assert report['matched_cues'] == report['total_cues'] == 2
    assert report['target_seconds'] == report['actual_seconds'] == 3.141
    alignment = json.loads((worker.DATA / 'parts/timeline/alignment.json').read_text())
    assert alignment['sync_ok'] and alignment['sync_report'] == report
    assert [c['tempo'] < 1 for c in alignment['cues']] == [True, False]
    assert [c['start_frame'] for c in alignment['cues']] == [round(.123 * RATE), round(1.567 * RATE)]
    assert [c['end_frame'] for c in alignment['cues']] == [round(1.234 * RATE), round(2.789 * RATE)]


def test_absent_video_duration_ends_exactly_at_last_caption(worker):
    job = timed_job(timeline_seconds=None)
    worker.render(job, lambda text, path: tone(path, .8))
    assert pcm_frames(worker.DATA / 'audio/timeline.wav') == round(2.789 * RATE)


@pytest.mark.parametrize('changes,message', [({'max_minutes': .02}, 'giới hạn xuất'),
                                              ({'timeline_seconds': 2.5}, 'ngắn hơn mốc cuối')])
def test_invalid_timeline_fails_before_synthesis_instead_of_truncating(worker, changes, message):
    def unexpected(*args):
        pytest.fail('Invalid timeline must be rejected before synthesis')
    with pytest.raises(ValueError, match=message):
        worker.render(timed_job(**changes), unexpected)
    assert not (worker.DATA / 'audio/timeline.wav').exists()


def test_refitting_timeline_reuses_speech_checkpoints_but_updates_output_length(worker):
    calls = []
    def synthesize(text, path):
        calls.append(text)
        tone(path, .8)
    worker.render(timed_job(), synthesize)
    worker.render(timed_job(timeline_seconds=4.25), synthesize)
    assert len(calls) == 2
    assert pcm_frames(worker.DATA / 'audio/timeline.wav') == round(4.25 * RATE)
    result = json.loads((worker.DATA / 'parts/timeline/result.json').read_text())
    assert result['reused_chunks'] == 2 and result['sync_report']['complete']


def test_failed_exact_cue_does_not_publish_partial_audio_or_subtitles(worker):
    with pytest.raises(ValueError, match='Câu 1:'):
        worker.render(timed_job(), lambda text, path: tone(path, 4))
    assert not (worker.DATA / 'audio/timeline.wav').exists()
    assert not (worker.DATA / 'audio/timeline.srt').exists()
    report = json.loads((worker.DATA / 'parts/timeline/alignment.json').read_text())
    assert not report['sync_ok'] and report['failed_cue'] == 1


def test_timeline_target_rounds_only_once_to_pcm_sample():
    cues = [{'start': 0, 'end': 1.001}]
    assert timeline_frames(cues, 1.234567) == round(1.234567 * RATE)


def test_many_millisecond_cues_do_not_accumulate_timeline_drift(worker):
    cues = [{'start': .123 + index * .05, 'end': .160 + index * .05, 'text': 'Lời.'}
            for index in range(200)]
    job = timed_job(text=export_srt(cues), timeline_seconds=10.321)
    worker.render(job, lambda text, path: tone(path, .037))
    assert pcm_frames(worker.DATA / 'audio/timeline.wav') == round(10.321 * RATE)
    report = json.loads((worker.DATA / 'parts/timeline/result.json').read_text())['sync_report']
    assert report['complete'] and report['matched_cues'] == 200 and report['max_error_ms'] == 0


def test_cue_fitting_honors_cancellation_before_ffmpeg(tmp_path):
    source, output, flag = tmp_path / 'source.wav', tmp_path / 'output.wav', tmp_path / 'cancel.flag'
    tone(source, .8)
    flag.touch()
    with pytest.raises(InterruptedError):
        fit_cue(source, output, RATE, cancel_flag=flag)
    assert not output.exists()

