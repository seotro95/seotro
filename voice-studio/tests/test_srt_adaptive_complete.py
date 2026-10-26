"""Tight SRT cues keep every planned phrase and exact caption boundaries."""
import importlib
import json
import shutil

import numpy as np
import pytest
import soundfile as sf

from narration import Segment
from subtitles import parse_srt


WORDS = [
    'Tus txiv neej taub hau do nqa ib tog ntoo hnyav tsib caug kilo ntaus rau daim iav kawg zog',
    'Tab sis daim iav muaj zog ntawd tseem tsis tawg li',
    'Thaum Win pom lo lus Made in China sau rau saum daim iav',
    'Nws thiaj xav tsis thoob kiag',
]
RANGES = [(.133, 3.066), (3.5, 5.166), (5.533, 8), (8.266, 9)]
CLOCKS = [('00:00:00,133', '00:00:03,066'), ('00:00:03,500', '00:00:05,166'),
          ('00:00:05,533', '00:00:08,000'), ('00:00:08,266', '00:00:09,000')]
SRT = '\n\n'.join(f'{i+1}\n{start} --> {end}\n{text}'
                   for i, ((start, end), text) in enumerate(zip(CLOCKS, WORDS)))


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    return module


def job(**changes):
    return {'id': 'adaptive-probe', 'engine': 'f5_hmong', 'voice_id': 'probe',
            'speaker': None, 'language': 'mww', 'format': 'wav', 'speed': 1,
            'text': SRT, 'input_format': 'srt', 'subtitle_timing': True,
            'delivery': 'natural', 'paragraph_pause': 0,
            'cue_fit': 'adaptive', 'max_cue_tempo': 4,
            'require_complete_audio': True, **changes}


def tone(path, seconds, hz=220):
    t = np.arange(round(seconds * 24000)) / 24000
    sf.write(path, .2 * np.sin(2 * np.pi * hz * t), 24000, subtype='PCM_16')


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='Requires actual pitch-preserving cue fitting')
def test_user_four_cues_keep_all_input_text_and_exact_nine_second_timeline(worker):
    calls = []
    durations = [6.124, 3.139, 3.709, 2.107]
    def synth(text, path):
        index = WORDS.index(text)
        calls.append(text)
        tone(path, durations[index], 220 + 100 * index)
    worker.render(job(), synth)
    folder = worker.DATA / 'parts' / 'adaptive-probe'
    alignment = json.loads((folder / 'alignment.json').read_text())
    result = json.loads((folder / 'result.json').read_text())
    assert calls == WORDS
    assert alignment['mode'] == 'adaptive' and alignment['sync_ok']
    assert len(alignment['cues']) == 4
    assert [cue['spoken_text'] for cue in alignment['cues']] == WORDS
    assert result['speech_complete'] and not result['duration_limited']
    assert result['require_complete_audio'] and result['audio_seconds'] == 9
    assert result['completed'] == result['total'] == 4
    assert len(result['timing_warnings']) == 2
    output = worker.DATA / 'audio' / 'adaptive-probe.wav'
    samples, rate = sf.read(output)
    assert rate == 24000 and len(samples) == 9 * rate
    for index, (cue, (start, end)) in enumerate(zip(alignment['cues'], RANGES)):
        assert cue['status'] == 'matched' and cue['spoken_start'] == start
        assert start < cue['spoken_end'] <= end + .001
        assert 1 < cue['tempo'] <= 4
        audio = samples[round(start*rate):round(cue['spoken_end']*rate)]
        peak_hz = np.argmax(abs(np.fft.rfft(audio))) * rate / len(audio)
        assert abs(peak_hz - (220 + 100 * index)) < 5
        next_start = RANGES[index + 1][0] if index < 3 else 9
        assert not np.any(samples[round(end*rate):round(next_start*rate)])
    assert not np.any(samples[:round(.133*rate)])
    assert parse_srt((worker.DATA / 'audio' / 'adaptive-probe.srt').read_text()) == parse_srt(SRT)


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='Requires actual fitting')
def test_adaptive_over_cap_fails_before_publishing_and_keeps_full_chunk(worker):
    settings = job(id='over-cap', text='1\n00:00:00,000 --> 00:00:00,100\nNyob zoo.')
    with pytest.raises(ValueError, match='Câu SRT 1.*không cắt mất lời'):
        worker.render(settings, lambda text, path: tone(path, 1))
    folder = worker.DATA / 'parts' / 'over-cap'
    assert worker.valid_checkpoint(folder / '000000.wav')
    assert sf.info(folder / '000000.wav').duration == 1
    assert not (worker.DATA / 'audio' / 'over-cap.wav').exists()
    alignment = json.loads((folder / 'alignment.json').read_text())
    assert alignment['failed_cue'] == 1 and not alignment['sync_ok']


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='Requires actual fitting')
@pytest.mark.parametrize('mode', ['strict', 'gap'])
def test_advanced_new_job_also_chains_high_tempo_and_warns(worker, monkeypatch, mode):
    seen = []
    original = worker.normalize_audio
    def spy(raw, out, tempo, gain, **kwargs):
        seen.append((tempo, kwargs))
        return original(raw, out, tempo, gain, **kwargs)
    monkeypatch.setattr(worker, 'normalize_audio', spy)
    settings = job(id=mode, text='1\n00:00:00,000 --> 00:00:01,000\nNyob zoo.',
                   cue_fit=mode, timeline_seconds=1)
    worker.render(settings, lambda text, path: tone(path, 3))
    fitted = [(tempo, kwargs) for tempo, kwargs in seen if tempo > 2]
    assert fitted and all(kwargs['chain_tempo'] is True for tempo, kwargs in fitted)
    result = json.loads((worker.DATA / 'parts' / mode / 'result.json').read_text())
    assert result['speech_complete'] and len(result['timing_warnings']) == 1


def test_new_complete_policy_never_publishes_partial_speech_at_global_limit(worker):
    calls = []
    def synth(text, path):
        calls.append(text)
        tone(path, 40)
    settings = job(id='complete-limit', text='Nyob zoo. Peb tuaj.', input_format='txt', max_minutes=1)
    with pytest.raises(ValueError, match='chưa xuất bản thu bị cắt lời'):
        worker.render(settings, synth)
    assert calls == ['Nyob zoo.', 'Peb tuaj.']
    assert not (worker.DATA / 'audio' / 'complete-limit.wav').exists()
    assert not (worker.DATA / 'parts' / 'complete-limit' / 'result.json').exists()
    assert all(worker.valid_checkpoint(worker.DATA / 'parts' / 'complete-limit' / f'{index:06d}.wav')
               for index in range(2))
    # Raising only the output limit reuses complete synthesis checkpoints.
    worker.render({**settings, 'max_minutes': 2}, synth)
    assert calls == ['Nyob zoo.', 'Peb tuaj.']
    result = json.loads((worker.DATA / 'parts' / 'complete-limit' / 'result.json').read_text())
    assert result['speech_complete'] and result['audio_seconds'] == 80


def test_complete_flag_changes_chunk_identity_without_invalidating_legacy(worker):
    settings = job(require_complete_audio=False)
    segment = Segment(text='Nyob zoo.', cue=0)
    legacy = worker._chunk_identity(settings, segment)
    omitted = {key: value for key, value in settings.items() if key != 'require_complete_audio'}
    assert worker._chunk_identity(omitted, segment) == legacy
    assert worker._chunk_identity({**settings, 'require_complete_audio': True}, segment) != legacy


@pytest.mark.parametrize('tempo', [.25, .4, .5, 1, 1.5, 2, 2.4, 3, 4])
def test_safe_tempo_chain_never_uses_sample_skipping_stage(worker, tempo):
    factors = [float(part.split('=')[1]) for part in worker._tempo_filter(tempo).split(',')]
    assert all(.5 <= factor <= 2 for factor in factors)
    assert np.prod(factors) == pytest.approx(tempo)


def test_new_high_speed_prepare_normalization_uses_safe_chain(worker, monkeypatch):
    seen = []
    original = worker.normalize_audio
    def spy(raw, out, tempo, gain, **kwargs):
        seen.append((tempo, kwargs))
        return original(raw, out, 1, gain, **kwargs)
    monkeypatch.setattr(worker, 'normalize_audio', spy)
    settings = job(speed=2, delivery='energetic', input_format='txt', text='Nyob zoo.')
    folder = worker.DATA / 'probe'
    folder.mkdir()
    worker.prepare_chunk(settings, Segment(text='Nyob zoo.'), 0, folder,
                         lambda text, path: tone(path, .5))
    assert seen[0][0] > 2 and seen[0][1]['chain_tempo'] is True


@pytest.mark.parametrize('policy', ['yes', 1, [], {}])
def test_invalid_complete_policy_fails_before_output_mutation(worker, policy):
    with pytest.raises(ValueError, match='Chính sách'):
        worker.render(job(require_complete_audio=policy))
    assert not (worker.DATA / 'parts').exists()
