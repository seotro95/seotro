"""Control parsing and real PCM DSP checks, not neural-emotion quality claims."""
import importlib
import json
import wave

import numpy as np
import pytest
import soundfile as sf

from hmong_expression import EMOTIONS, automatic_pause, parameters, shape_phrase_energy
from narration import Segment, plan_segments


def expression_job(text='Nyob zoo.', **changes):
    return {'id': 'expression', 'text': text, 'engine': 'f5_hmong', 'speed': 1,
            'delivery': 'natural', 'format': 'wav', 'paragraph_pause': 0,
            'segment_plan': 'hmong-expression-v1', 'emotion': 'neutral',
            'emotion_strength': .65, 'auto_rhythm': True, **changes}


def test_inline_controls_inside_bold_keep_words_and_persistent_txt_emotion():
    segments = plan_segments(expression_job(
        'Nyob zoo. [emotion=warm]Kuv tuaj.\n**[emotion=sad]Ua tsaug.** [pause=0.7] Peb nyob nov.',
        auto_rhythm=False))
    assert [(s.text, s.emotion, s.emphasis, s.pause) for s in segments] == [
        ('Nyob zoo.', 'neutral', False, 0), ('Kuv tuaj.', 'warm', False, 0),
        ('Ua tsaug.', 'sad', True, 0), ('', None, False, .7),
        ('Peb nyob nov.', 'sad', False, 0)]
    assert not any('emotion=' in s.text or '**' in s.text or 'pause=' in s.text for s in segments)


@pytest.mark.parametrize('text', ['[emotion=angry]Nyob zoo.', '[emotion=]Nyob zoo.',
                                 '[emotion=warm Nyob zoo.', '**Nyob zoo.', '[pause=-1]Nyob zoo.'])
def test_unknown_or_malformed_controls_fail_before_synthesis(text):
    with pytest.raises(ValueError):
        plan_segments(expression_job(text))


def test_srt_emotion_resets_per_cue_and_never_adds_automatic_pauses():
    srt = ('1\n00:00:00,000 --> 00:00:03,000\n[emotion=warm]Nyob zoo. Ua tsaug.\n\n'
           '2\n00:00:03,000 --> 00:00:06,000\nKuv tuaj.\n')
    segments = plan_segments(expression_job(srt, input_format='srt', emotion='serious'))
    assert [(s.cue, s.emotion, s.text) for s in segments] == [
        (0, 'warm', 'Nyob zoo. Ua tsaug.'), (1, 'serious', 'Kuv tuaj.')]
    assert all(s.rhythm_pause == 0 for s in segments)


def test_rhythm_keeps_sentence_and_paragraph_gaps_and_explicit_pause_overrides():
    segments = plan_segments(expression_job('Nyob zoo. [pause=0] Ua tsaug.\n\nKuv tuaj!'))
    assert [s.text for s in segments] == ['Nyob zoo.', '', 'Ua tsaug.', 'Kuv tuaj!']
    assert segments[0].rhythm_pause == 0 and segments[1].pause == 0
    assert segments[2].rhythm_pause > automatic_pause('Ua tsaug.')
    assert segments[3].rhythm_pause == automatic_pause('Kuv tuaj!')
    assert len(plan_segments(expression_job('Nyob zoo. Ua tsaug.', auto_rhythm=False))) == 1


def test_dialogue_quotes_keep_sentence_pauses_without_splitting_each_comma():
    segments = plan_segments(expression_job('“Nyob zoo.” Kuv tuaj, kuv nyob nov.'))
    assert [segment.text for segment in segments] == ['"Nyob zoo."', 'Kuv tuaj, kuv nyob nov.']
    assert all(segment.rhythm_pause > 0 for segment in segments)


def test_packing_is_bounded_and_cannot_cross_emotion_or_explicit_pause():
    text = ' '.join(['Pab paj pav pas pag pam pad pa.'] * 30)
    segments = plan_segments(expression_job(text, auto_rhythm=False))
    assert ' '.join(s.text for s in segments) == text
    assert all(len(s.text) <= 160 for s in segments)
    changes = plan_segments(expression_job('Nyob zoo. [emotion=warm]Ua tsaug. [pause=0] Kuv tuaj.',
                                            auto_rhythm=False))
    assert [(s.text, s.emotion) for s in changes] == [
        ('Nyob zoo.', 'neutral'), ('Ua tsaug.', 'warm'), ('', None), ('Kuv tuaj.', 'warm')]


def test_new_fields_do_not_change_legacy_or_standard_segmentation():
    text = 'Nyob zoo. Ua tsaug.'
    for engine, marker in [('f5_hmong', 'classic-v1'), ('f5_hmong', 'hmong-packed-v1'),
                           ('vieneu', 'hmong-expression-v1')]:
        legacy = {'text': text, 'engine': engine, 'segment_plan': marker, 'paragraph_pause': 0}
        assert plan_segments({**legacy, 'emotion': 'sad', 'emotion_strength': 1,
                              'auto_rhythm': True}) == plan_segments(legacy)


def test_emotion_presets_are_distinct_but_zero_strength_is_neutral():
    assert len({parameters(emotion) for emotion in EMOTIONS}) == len(EMOTIONS)
    assert parameters('sad')[0] < parameters('neutral')[0] < parameters('joyful')[0]
    assert automatic_pause('Nyob zoo.', 'suspense') > automatic_pause('Nyob zoo.', 'joyful')
    for emotion in EMOTIONS:
        assert parameters(emotion, 0) == (1, 1, 1, 0)
        assert automatic_pause('Nyob zoo.', emotion, 0) == automatic_pause('Nyob zoo.', 'neutral', 0)


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    module = importlib.import_module('worker')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, '_hmong_model_instance', None)
    (tmp_path / 'audio').mkdir()
    return module


def sine(path, *, seconds=2, amplitude=.3):
    samples = amplitude * np.sin(2 * np.pi * 220 * np.arange(round(seconds * 24000)) / 24000)
    sf.write(str(path), samples, 24000, subtype='PCM_16')


def fundamental(samples, rate):
    # Ignore the atempo window edges; compare stable voiced periodicity.
    middle = samples[round(.2 * rate):-round(.2 * rate)]
    spectrum = np.abs(np.fft.rfft(middle * np.hanning(len(middle))))
    return np.fft.rfftfreq(len(middle), 1 / rate)[int(np.argmax(spectrum))]


@pytest.mark.parametrize('emotion', ['warm', 'joyful', 'sad', 'serious', 'suspense'])
def test_real_audio_tempo_and_energy_preserve_pitch_periodicity(worker, tmp_path, emotion):
    job = expression_job(emotion=emotion, emotion_strength=1, auto_rhythm=False)
    worker.prepare_chunk(job, Segment(text='Nyob zoo.', emotion=emotion), 0, tmp_path,
                         lambda text, path: sine(path))
    samples, rate = sf.read(str(tmp_path / '000000.wav'))
    assert rate == 24000 and np.isfinite(samples).all()
    assert fundamental(samples, rate) == pytest.approx(220, abs=1.5)
    assert len(samples) / rate == pytest.approx(2 / parameters(emotion, 1)[0], abs=.06)
    assert np.max(np.abs(samples)) <= .951
    assert worker.valid_checkpoint(tmp_path / '000000.wav')


def test_energy_envelope_is_bounded_without_changing_samples_or_pitch(worker, tmp_path):
    path = tmp_path / 'envelope.wav'
    sine(path, amplitude=.94)
    before, rate = sf.read(str(path))
    shape_phrase_energy(path, 'joyful', 1)
    after, after_rate = sf.read(str(path))
    assert rate == after_rate == 24000 and len(before) == len(after)
    assert np.max(np.abs(after)) <= .951
    assert fundamental(after, rate) == pytest.approx(fundamental(before, rate), abs=.1)
    assert not np.array_equal(before, after)


def test_zero_strength_matches_neutral_pcm_and_legacy_ignores_new_controls(worker, tmp_path):
    neutral = tmp_path / 'neutral'
    zero = tmp_path / 'zero'
    legacy = tmp_path / 'legacy'
    for folder in (neutral, zero, legacy):
        folder.mkdir()
    synth = lambda text, path: sine(path, seconds=.5)
    worker.prepare_chunk(expression_job(emotion_strength=0), Segment(text='Nyob zoo.', emotion='neutral'),
                         0, neutral, synth)
    worker.prepare_chunk(expression_job(emotion='sad', emotion_strength=0),
                         Segment(text='Nyob zoo.', emotion='sad'), 0, zero, synth)
    worker.prepare_chunk(expression_job(segment_plan='classic-v1', emotion='sad', emotion_strength=1),
                         Segment(text='Nyob zoo.'), 0, legacy, synth)
    assert (neutral / '000000.wav').read_bytes() == (zero / '000000.wav').read_bytes()
    assert (neutral / '000000.wav').read_bytes() == (legacy / '000000.wav').read_bytes()


def test_real_render_strips_controls_adds_exact_gaps_and_reuses_checkpoints(worker, tmp_path):
    job = expression_job('Nyob zoo. [emotion=warm]Kuv tuaj.[pause=0.25] **Ua tsaug.**',
                         paragraph_pause=.04)
    calls = []
    def synth(text, path):
        calls.append(text)
        sine(path, seconds=.2)
    worker.render(job, synthesize=synth)
    assert calls == ['Nyob zoo.', 'Kuv tuaj.', 'Ua tsaug.']
    segments = plan_segments(job)
    work = tmp_path / 'parts' / job['id']
    audio_frames = sum(sf.info(str(path)).frames for path in work.glob('[0-9]*.wav'))
    expected_gaps = .04 + segments[0].rhythm_pause + .25 + .04 + segments[-1].rhythm_pause
    output = sf.info(str(tmp_path / 'audio' / (job['id'] + '.wav')))
    assert output.frames == audio_frames + round(expected_gaps * 24000)
    result = json.loads((work / 'result.json').read_text())
    assert result['expression']['emotion_counts'] == {'neutral': 1, 'warm': 2}
    assert result['expression']['emotions_used'] == ['neutral', 'warm']
    assert not result['expression']['pitch_shift'] and not result['expression']['neural_emotion']
    worker.render(job, synthesize=lambda *args: pytest.fail('Completed PCM should be reused'))


def test_real_srt_render_keeps_cue_times_and_skips_auto_gaps(worker, tmp_path):
    srt = ('1\n00:00:00,000 --> 00:00:03,000\n[emotion=warm]Nyob zoo.\n\n'
           '2\n00:00:03,000 --> 00:00:06,000\nUa tsaug.\n')
    worker.render(expression_job(srt, input_format='srt', paragraph_pause=3),
                  synthesize=lambda text, path: sine(path, seconds=.2))
    with wave.open(str(tmp_path / 'audio' / 'expression.wav')) as audio:
        assert audio.getnframes() == 6 * 24000
    alignment = json.loads((tmp_path / 'parts' / 'expression' / 'alignment.json').read_text())
    assert [(cue['start'], cue['end']) for cue in alignment['cues']] == [(0, 3), (3, 6)]
    assert alignment['sync_ok']
